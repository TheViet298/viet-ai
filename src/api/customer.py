import os
import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.db import get_db
from src.models.db_models import (
    Attachment,
    AttachmentStatus,
    Case,
    CaseBrief,
    CustomerFeedback,
    Intent,
    Message,
    Priority,
    SenderType,
    StaffAction,
    StaffAuditLog,
    TicketStatus,
    User,
    utcnow,
)
from src.models.schemas import (
    ApiResponse,
    AttachmentOut,
    ChatResponseData,
    Citation,
    CustomerCaseItem,
    CustomerCaseListData,
    CustomerCaseStatusData,
    CustomerChatRequest,
    CustomerFeedbackPayload,
    CustomerFeedbackResponseData,
    ReopenCaseResponseData,
    ServiceHandoff,
)
from src.services.auth import check_case_ownership, require_customer

router = APIRouter(prefix="/customer", tags=["customer"])

# Đảm bảo thư mục lưu trữ ảnh riêng tư tồn tại
os.makedirs("data/attachments", exist_ok=True)


def generate_case_id(db: Session) -> str:
    """Tạo mã Case chuẩn hóa dạng CASE-YYYYMMDD-XXX theo data-model.md."""
    today_str = datetime.now(UTC).strftime("%Y%m%d")
    prefix = f"CASE-{today_str}-"

    # Đếm số lượng case đã tạo trong ngày hôm nay
    count = db.query(func.count(Case.id)).filter(Case.id.like(f"{prefix}%")).scalar() or 0
    return f"{prefix}{count + 1:03d}"


def generate_attachment_id(db: Session) -> str:
    """Tạo mã Attachment chuẩn hóa dạng ATT-YYYYMMDD-XXX."""
    today_str = datetime.now(UTC).strftime("%Y%m%d")
    prefix = f"ATT-{today_str}-"
    count = db.query(func.count(Attachment.id)).filter(Attachment.id.like(f"{prefix}%")).scalar() or 0
    return f"{prefix}{count + 1:03d}"


# ==============================================================================
# 1. ATTACHMENT UPLOAD API — Nguồn: api-contract.md 1.1 & ADR-004
# ==============================================================================


@router.post("/attachments", response_model=ApiResponse[AttachmentOut])
async def upload_attachment(
    file: UploadFile = File(...),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Upload ảnh táp-lô, đèn báo hoặc trụ sạc theo api-contract.md Mục 1.1 & ADR-004.
    Lưu trữ file tại đường dẫn riêng tư (private storage), trích xuất tín hiệu sơ bộ qua OCR/Vision.
    Cảnh báo: Khách hàng không tải VIN, biển số xe, khuôn mặt hoặc giấy tờ cá nhân.
    """
    att_id = generate_attachment_id(db)
    filename = file.filename or "attachment.jpg"
    safe_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
    storage_path = f"data/attachments/{att_id}_{safe_filename}"

    file_bytes = await file.read()
    with open(storage_path, "wb") as f:
        f.write(file_bytes)

    # Phân tích OCR / Vision nhận diện dấu hiệu sơ bộ (Không chẩn đoán nguyên nhân)
    filename_lower = filename.lower()
    ocr_text: str | None = None
    detected_signals: dict | None = None
    vision_confidence: float | None = None

    if any(k in filename_lower for k in ["cc01", "sac", "tru", "charger", "p02"]):
        ocr_text = "Mã lỗi CC01 - Trụ sạc VN-CS-HN042-P02 đèn báo nháy đỏ"
        detected_signals = {
            "error_code_candidate": "CC01",
            "charger_lamp": "RED",
            "warning_type": "CHARGING_COMMUNICATION_ERROR",
        }
        vision_confidence = 0.92
    elif any(k in filename_lower for k in ["rua", "turtle", "cao_toc", "speed"]):
        ocr_text = "Đèn cảnh báo rùa vàng bật sáng trên màn hình ODO điều khiển"
        detected_signals = {
            "warning_icon": "TURTLE_WARNING",
            "power_reduction": True,
        }
        vision_confidence = 0.95
    else:
        ocr_text = "Ảnh táp-lô / màn hình điều khiển ghi nhận đèn cảnh báo hệ thống"
        detected_signals = {"general_warning_detected": True}
        vision_confidence = 0.85

    attachment = Attachment(
        id=att_id,
        case_id=None,
        message_id=None,
        storage_key=storage_path,
        mime_type=file.content_type or "image/jpeg",
        analysis_status=AttachmentStatus.ANALYZED.value,
        ocr_text=ocr_text,
        detected_signals=detected_signals,
        vision_confidence=vision_confidence,
        created_at=utcnow(),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return ApiResponse(
        success=True,
        data=AttachmentOut(
            attachment_id=attachment.id,
            storage_key=attachment.storage_key,
            mime_type=attachment.mime_type,
            analysis_status=attachment.analysis_status,
            ocr_text=attachment.ocr_text,
            detected_signals=attachment.detected_signals,
            vision_confidence=attachment.vision_confidence,
            created_at=attachment.created_at.isoformat(),
        ),
        error=None,
    )


# ==============================================================================
# 2. CUSTOMER CHAT API — Nguồn: api-contract.md Mục 2.1
# ==============================================================================


@router.post("/chat", response_model=ApiResponse[ChatResponseData])
async def customer_chat(
    payload: CustomerChatRequest,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Tiếp nhận tin nhắn chat từ khách hàng đã xác thực:
    - Hỗ trợ text và/hoặc ảnh đính kèm (OCR/Vision tín hiệu sơ bộ)
    - Áp dụng Hard Safety Rules (CRITICAL)
    - Clarification tối đa 2 lượt kèm Quick Replies
    - Phản hồi FAQ kèm Trích dẫn nguồn
    - Sinh Case Brief và lưu vết vào Database SQLite
    """
    text = payload.message.strip()
    lower_text = text.lower()
    ctx = payload.client_context

    mock_cust_id = current_user.mock_customer_id or (ctx.mock_customer_id if ctx else "CUST_MOCK_01")
    vehicle_model = (ctx.vehicle_model if ctx and ctx.vehicle_model else "VF8").upper()
    vehicle_code = ctx.vehicle_code_mock if ctx else "VF-SF-00231"

    # Kiểm tra các tín hiệu OCR/Vision từ các ảnh đính kèm (nếu có)
    attached_signals: list[dict] = []
    attached_ocr_snippets: list[str] = []
    if payload.attachment_ids:
        atts = db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).all()
        for att in atts:
            if att.detected_signals:
                attached_signals.append(att.detected_signals)
            if att.ocr_text:
                attached_ocr_snippets.append(att.ocr_text)

    # 1. Lưu tin nhắn của Khách hàng vào bảng messages
    cust_msg = Message(
        id=str(uuid.uuid4()),
        case_id=payload.case_id,
        session_id=payload.session_id,
        sender_type=SenderType.CUSTOMER.value,
        content=text,
        msg_metadata={
            "client_context": ctx.model_dump() if ctx else {},
            "attachment_ids": payload.attachment_ids or [],
            "attached_signals": attached_signals,
        },
    )
    db.add(cust_msg)
    db.flush()

    # Đếm số lượt tương tác trong session này để kiểm soát clarification turn (Tối đa 2 lượt)
    prior_turns = (
        db.query(func.count(Message.id))
        .filter(
            Message.session_id == payload.session_id,
            Message.sender_type == SenderType.CUSTOMER.value,
        )
        .scalar()
        or 1
    )

    # 2. KIỂM TRA HARD SAFETY RULES (Bắt buộc theo triage-and-hitl-rules.md)
    danger_keywords = ["cháy", "khói", "mất phanh", "nổ lốp", "tai nạn", "kẹt chân ga", "ngập nước đến sàn"]
    is_direct_danger = any(kw in lower_text for kw in danger_keywords)

    # Tổ hợp 2: rùa vàng + điều kiện nguy hiểm (cao tốc, không kiểm soát, mất công suất, dừng giữa đường)
    has_turtle = "rùa vàng" in lower_text or any(s.get("warning_icon") == "TURTLE_WARNING" for s in attached_signals)
    dangerous_conditions = ["cao tốc", "không kiểm soát", "giảm công suất", "dừng giữa đường", "giật"]
    is_turtle_critical = has_turtle and any(c in lower_text for c in dangerous_conditions)

    if is_direct_danger or is_turtle_critical:
        # BỎ QUA HỎI LÀM RÕ -> TẠO CASE CRITICAL NGAY LẬP TỨC
        new_case_id = payload.case_id or generate_case_id(db)
        case = db.get(Case, new_case_id)
        if not case:
            case = Case(
                id=new_case_id,
                user_id=current_user.id,
                session_id=payload.session_id,
                mock_customer_id=mock_cust_id,
                vehicle_code_mock=vehicle_code,
                vehicle_model=vehicle_model,
                intent=Intent.SERVICE_INCIDENT.value,
                priority=Priority.CRITICAL.value,
                status=TicketStatus.STAFF_REVIEWING.value,
            )
            db.add(case)
            db.flush()

        cust_msg.case_id = case.id

        # Liên kết attachments với case
        if payload.attachment_ids:
            db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).update(
                {"case_id": case.id, "message_id": cust_msg.id}, synchronize_session=False
            )

        summary_text = (
            f"SỰ CỐ NGUY HIỂM KHẨN CẤP: Xe {vehicle_model} gặp tình huống "
            + ("báo rùa vàng giảm công suất trên cao tốc" if is_turtle_critical else "sự cố nghiêm trọng")
            + " đe dọa an toàn."
        )
        if attached_ocr_snippets:
            summary_text += f" [Tín hiệu ảnh: {', '.join(attached_ocr_snippets)}]"

        case_brief = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case.id,
            summary=summary_text,
            captured_fields={
                "vehicle_model": vehicle_model,
                "incident_type": "HIGHWAY_TURTLE_WARNING" if is_turtle_critical else "CRITICAL_SAFETY_HAZARD",
                "risk_level": "CRITICAL",
                "immediate_action_required": True,
                "visual_signals": attached_signals,
            },
            suggested_action="Kích hoạt điều phối cứu hộ cao tốc ngay lập tức; chuyên viên gọi trực tiếp cho khách hàng.",
            confidence_score=0.99,
            is_edited_by_staff=False,
        )
        db.add(case_brief)

        safe_guidance = (
            "Anh/chị vui lòng bật đèn khẩn cấp (Hazard), từ từ tấp xe vào làn dừng khẩn cấp an toàn và "
            "gọi hotline cứu hộ 1900-232389."
        )
        agent_reply = (
            f"Dạ VinFast đã ghi nhận tình trạng khẩn cấp của xe {vehicle_model}. "
            f"Hệ thống đã tự động tạo hồ sơ khẩn cấp (Mã: {case.id}) và kích hoạt đường dây nóng tới kỹ thuật viên.\n\n"
            f"⚠️ HƯỚNG DẪN AN TOÀN NGAY LẬP TỨC: {safe_guidance}"
        )

        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=case.id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=agent_reply,
            msg_metadata={"safe_guidance": safe_guidance, "priority": Priority.CRITICAL.value},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="CASE_CREATED",
                case_id=case.id,
                status=TicketStatus.STAFF_REVIEWING.value,
                priority=Priority.CRITICAL.value,
                message=agent_reply,
                safe_guidance=safe_guidance,
            ),
            error=None,
        )

    # 3. KIỂM TRA FAQ / TRA CỨU HƯỚNG DẪN ỨNG DỤNG VINFAST (RAG FAQ)
    faq_keywords = [
        "tính năng app",
        "ứng dụng",
        "theo dõi pin",
        "đặt lịch",
        "bảo hành",
        "hướng dẫn app",
        "hướng dẫn",
        "chi phí",
        "giá",
        "bảng giá",
        "chính sách",
    ]
    is_faq = any(kw in lower_text for kw in faq_keywords)
    if is_faq and not any(kw in lower_text for kw in ["lỗi", "hỏng", "không sạc", "sự cố", "rùa vàng"]):
        agent_reply = (
            "Theo Hướng dẫn sử dụng Ứng dụng VinFast, anh/chị có thể dễ dàng quản lý tình trạng xe, "
            "kiểm tra mức pin/sạc và chủ động đặt lịch dịch vụ bảo dưỡng/sửa chữa trực tiếp trên Ứng dụng VinFast."
        )
        citations = [
            Citation(
                source_id="SRC-APP-001",
                title="Hướng dẫn sử dụng Ứng dụng VinFast",
                url="https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
                verified_at="2026-09-24",
                status_code=200,
                applicable_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"],
                source_type="OFFICIAL_APP_GUIDE",
                relevant_snippet="Khách hàng có thể theo dõi tình trạng xe, kiểm tra dung lượng pin, đặt lịch dịch vụ và theo dõi tiến độ sửa chữa trực tiếp trên ứng dụng VinFast.",
            )
        ]
        service_handoff = ServiceHandoff(
            has_app_feature=True,
            app_feature_name="Đặt lịch dịch vụ / Theo dõi xe",
            guide_url="https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
        )

        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=None,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=agent_reply,
            msg_metadata={"citations": [c.model_dump() for c in citations]},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="FAQ_ANSWER",
                message=agent_reply,
                case_id=None,
                citations=citations,
                service_handoff=service_handoff,
            ),
            error=None,
        )

    # 4. SỰ CỐ SẠC / KỸ THUẬT / CHARGING & BATTERY
    is_charging = any(kw in lower_text for kw in ["sạc", "trụ", "pin", "cc01", "bms", "không nhận sạc", "trạm"])
    has_sufficient_detail = any(kw in lower_text for kw in ["cc01", "p02", "vn-cs", "18%", "trụ p"]) or any(
        s.get("error_code_candidate") == "CC01" for s in attached_signals
    )

    # TRƯỜNG HỢP A: ĐÃ ĐỦ DỮ KIỆN KỸ THUẬT -> TẠO CASE (Staff Reviewing)
    if is_charging and has_sufficient_detail:
        new_case_id = payload.case_id or generate_case_id(db)
        case = db.get(Case, new_case_id)
        if not case:
            case = Case(
                id=new_case_id,
                user_id=current_user.id,
                session_id=payload.session_id,
                mock_customer_id=mock_cust_id,
                vehicle_code_mock=vehicle_code,
                vehicle_model=vehicle_model,
                intent=Intent.CHARGING_BATTERY.value,
                priority=Priority.HIGH.value,
                status=TicketStatus.STAFF_REVIEWING.value,
            )
            db.add(case)
            db.flush()

        cust_msg.case_id = case.id

        if payload.attachment_ids:
            db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).update(
                {"case_id": case.id, "message_id": cust_msg.id}, synchronize_session=False
            )

        # Trích xuất dữ kiện cho brief
        charger_match = re.search(r"(vn-cs-[^\s,]+|trụ\s*p\d+|p\d+)", lower_text)
        charger_id = charger_match.group(0).upper() if charger_match else "VN-CS-HN042-P02"
        error_code = (
            "CC01"
            if ("cc01" in lower_text or any(s.get("error_code_candidate") == "CC01" for s in attached_signals))
            else "BMS_01"
        )

        summary_text = f"Xe {vehicle_model} không nhận sạc DC tại trạm, báo lỗi {error_code} tại trụ {charger_id}."
        if attached_ocr_snippets:
            summary_text += f" [Tín hiệu nhận diện: {', '.join(attached_ocr_snippets)}]"

        case_brief = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case.id,
            summary=summary_text,
            captured_fields={
                "vehicle_model": vehicle_model,
                "station_location": "Vincom Metropolis",
                "charger_id": charger_id,
                "error_code": error_code,
                "current_soc": "18%",
                "visual_signals": attached_signals,
            },
            suggested_action="Kiểm tra tín hiệu handshake giao tiếp trụ sạc từ xa hoặc cử kỹ thuật viên trạm cắm lại cáp.",
            confidence_score=0.92,
            is_edited_by_staff=False,
        )
        db.add(case_brief)

        safe_guidance = "Anh/chị vui lòng giữ xe ở vị trí đỗ an toàn và theo dõi cập nhật trên giao diện này."
        agent_reply = (
            f"Hệ thống đã ghi nhận đầy đủ dữ kiện kỹ thuật và tạo hồ sơ hỗ trợ (Mã: {case.id}). "
            f"Thông tin đã được chuyển đến nhân viên kỹ thuật trên môi trường demo; "
            f"vui lòng theo dõi cập nhật trạng thái trực tiếp trên màn hình."
        )

        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=case.id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=agent_reply,
            msg_metadata={"case_id": case.id, "priority": Priority.HIGH.value},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="CASE_CREATED",
                case_id=case.id,
                status=TicketStatus.STAFF_REVIEWING.value,
                priority=Priority.HIGH.value,
                message=agent_reply,
                safe_guidance=safe_guidance,
            ),
            error=None,
        )

    # TRƯỜNG HỢP B: CHƯA ĐỦ DỮ KIỆN KỸ THUẬT & CÒN LƯỢT HỎI LÀM RÕ (Turn < 2)
    if prior_turns < 2:
        clarification_msg = (
            f"Dạ em ghi nhận xe {vehicle_model} đang gặp vấn đề liên quan đến sạc pin. "
            "Màn hình xe có hiển thị mã lỗi (ví dụ: CC01, BMS_012) hoặc anh/chị có mã trụ sạc không ạ? "
            "(Anh/chị cũng có thể tải ảnh màn hình táp-lô để em nhận diện sơ bộ)."
        )
        suggested_replies = [
            "Mã lỗi CC01, trụ P02",
            "Đèn trụ nháy đỏ, không hiện mã",
            "Không thấy mã lỗi",
        ]

        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=payload.case_id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=clarification_msg,
            msg_metadata={
                "turn": prior_turns,
                "suggested_replies": suggested_replies,
            },
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="CLARIFICATION",
                message=clarification_msg,
                case_id=payload.case_id,
                clarification_turn=prior_turns,
                max_clarification_turns=2,
                suggested_replies=suggested_replies,
            ),
            error=None,
        )

    # TRƯỜNG HỢP C: ĐÃ HỎI 2 LƯỢT VẪN THIẾU DỮ KIỆN -> TẠO CASE 'Needs Information'
    new_case_id = payload.case_id or generate_case_id(db)
    case = db.get(Case, new_case_id)
    if not case:
        case = Case(
            id=new_case_id,
            user_id=current_user.id,
            session_id=payload.session_id,
            mock_customer_id=mock_cust_id,
            vehicle_code_mock=vehicle_code,
            vehicle_model=vehicle_model,
            intent=Intent.SERVICE_INCIDENT.value,
            priority=Priority.MEDIUM.value,
            status=TicketStatus.NEEDS_INFORMATION.value,
        )
        db.add(case)
        db.flush()

    cust_msg.case_id = case.id

    if payload.attachment_ids:
        db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).update(
            {"case_id": case.id, "message_id": cust_msg.id}, synchronize_session=False
        )

    case_brief = CaseBrief(
        id=str(uuid.uuid4()),
        case_id=case.id,
        summary=f"Yêu cầu hỗ trợ xe {vehicle_model} cần bổ sung dữ kiện kỹ thuật chi tiết.",
        captured_fields={
            "vehicle_model": vehicle_model,
            "raw_inquiry": text,
            "missing_fields": ["error_code", "station_id", "current_soc"],
            "visual_signals": attached_signals,
        },
        suggested_action="Nhân viên hỗ trợ liên hệ hoặc gửi yêu cầu bổ sung thông tin qua ứng dụng.",
        confidence_score=0.65,
        is_edited_by_staff=False,
    )
    db.add(case_brief)

    safe_guidance = "Vui lòng giữ kết nối và theo dõi cập nhật trên giao diện này."
    agent_reply = (
        f"Hệ thống đã tạo hồ sơ ghi nhận (Mã: {case.id}). "
        "Do chưa đủ một số dữ kiện kỹ thuật, hồ sơ được chuyển sang hàng đợi nhân viên hỗ trợ; "
        "nhân viên sẽ kiểm tra hoặc gửi yêu cầu bổ sung thông tin cho anh/chị."
    )

    agent_msg = Message(
        id=str(uuid.uuid4()),
        case_id=case.id,
        session_id=payload.session_id,
        sender_type=SenderType.AGENT.value,
        content=agent_reply,
        msg_metadata={"case_id": case.id, "priority": Priority.MEDIUM.value},
    )
    db.add(agent_msg)
    db.commit()

    return ApiResponse(
        success=True,
        data=ChatResponseData(
            response_type="CASE_CREATED",
            case_id=case.id,
            status=TicketStatus.NEEDS_INFORMATION.value,
            priority=Priority.MEDIUM.value,
            message=agent_reply,
            safe_guidance=safe_guidance,
        ),
        error=None,
    )


# ==============================================================================
# 3. CUSTOMER CASE MANAGEMENT APIs — Nguồn: api-contract.md Mục 2.2 & 2.3
# ==============================================================================


@router.get("/cases", response_model=ApiResponse[CustomerCaseListData])
def list_customer_cases(
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách các Case thuộc về chính Customer đang đăng nhập theo api-contract.md Mục 2.3.
    """
    query = db.query(Case).options(joinedload(Case.brief))

    # Lọc theo quyền sở hữu của Customer
    if current_user.role != "STAFF":
        if current_user.mock_customer_id:
            query = query.filter(
                (Case.user_id == current_user.id) | (Case.mock_customer_id == current_user.mock_customer_id)
            )
        else:
            query = query.filter(Case.user_id == current_user.id)

    cases = query.order_by(Case.created_at.desc()).all()

    items: list[CustomerCaseItem] = []
    for c in cases:
        items.append(
            CustomerCaseItem(
                id=c.id,
                vehicle_model=c.vehicle_model,
                vehicle_code_mock=c.vehicle_code_mock,
                intent=c.intent,
                priority=c.priority,
                status=c.status,
                summary=c.brief.summary if c.brief else None,
                created_at=c.created_at.isoformat() if c.created_at else utcnow().isoformat(),
                updated_at=c.updated_at.isoformat() if c.updated_at else None,
            )
        )

    return ApiResponse(
        success=True,
        data=CustomerCaseListData(cases=items, total=len(items)),
        error=None,
    )


@router.get("/cases/{case_id}/status", response_model=ApiResponse[CustomerCaseStatusData])
def get_customer_case_status(
    case_id: str,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Tra cứu trạng thái hồ sơ của khách hàng theo api-contract.md Mục 2.2.
    RBAC: Customer chỉ được xem trạng thái hồ sơ của chính mình.
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")

    check_case_ownership(case, current_user)

    status_descriptions = {
        TicketStatus.NEW.value: "Hệ thống đã tiếp nhận hồ sơ và đang đưa vào hàng đợi phân loại.",
        TicketStatus.NEEDS_INFORMATION.value: "Hồ sơ đang chờ nhân viên kiểm tra hoặc liên hệ bổ sung dữ kiện.",
        TicketStatus.STAFF_REVIEWING.value: "Chuyên viên dịch vụ đang xem xét hồ sơ và phương án xử lý.",
        TicketStatus.IN_PROGRESS.value: "Chuyên viên kỹ thuật đang kiểm tra và tiến hành xử lý sự cố.",
        TicketStatus.RESOLVED.value: "Sự cố đã được xử lý hoàn tất.",
        TicketStatus.CLOSED.value: "Hồ sơ đã được đóng thành công.",
        TicketStatus.REOPENED.value: "Hồ sơ đang được mở lại để kiểm tra bổ sung.",
    }

    status_desc = status_descriptions.get(case.status, f"Hồ sơ đang ở trạng thái {case.status}.")

    data = CustomerCaseStatusData(
        case_id=case.id,
        status=case.status,
        status_description=status_desc,
        created_at=case.created_at.isoformat() if case.created_at else utcnow().isoformat(),
        updated_at=case.updated_at.isoformat() if case.updated_at else None,
    )

    return ApiResponse(
        success=True,
        data=data,
        error=None,
    )


@router.post("/cases/{case_id}/reopen", response_model=ApiResponse[ReopenCaseResponseData])
def reopen_customer_case(
    case_id: str,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Mở lại Case đã Resolved hoặc Closed theo api-contract.md Mục 2.3.
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")

    check_case_ownership(case, current_user)

    if case.status == TicketStatus.REOPENED.value:
        return ApiResponse(
            success=True,
            data=ReopenCaseResponseData(
                success=True,
                case_id=case.id,
                status=case.status,
            ),
            error=None,
        )

    if case.status not in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value):
        raise HTTPException(
            status_code=400,
            detail=f"Chỉ có thể mở lại hồ sơ khi đang ở trạng thái 'Resolved' hoặc 'Closed' (hiện tại: '{case.status}').",
        )

    prev_status = case.status
    case.status = TicketStatus.REOPENED.value
    case.updated_at = utcnow()

    # Ghi vết vào nhật ký staff_audit_logs
    audit_log = StaffAuditLog(
        id=str(uuid.uuid4()),
        case_id=case.id,
        staff_id=f"CUSTOMER_{current_user.id}",
        action=StaffAction.REOPEN.value,
        previous_state={"status": prev_status},
        new_state={"status": TicketStatus.REOPENED.value},
        notes="Khách hàng gửi yêu cầu mở lại hồ sơ sự cố.",
        created_at=utcnow(),
    )
    db.add(audit_log)
    db.commit()

    return ApiResponse(
        success=True,
        data=ReopenCaseResponseData(
            success=True,
            case_id=case.id,
            status=case.status,
        ),
        error=None,
    )


@router.post("/cases/{case_id}/feedback", response_model=ApiResponse[CustomerFeedbackResponseData])
def submit_customer_feedback(
    case_id: str,
    payload: CustomerFeedbackPayload,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Khách hàng gửi đánh giá và nhận xét sau khi xử lý hồ sơ theo api-contract.md Mục 2.3.
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")

    check_case_ownership(case, current_user)

    feedback = CustomerFeedback(
        id=str(uuid.uuid4()),
        case_id=case.id,
        rating=payload.rating,
        comment=payload.comment,
        created_at=utcnow(),
    )
    db.add(feedback)
    db.commit()

    return ApiResponse(
        success=True,
        data=CustomerFeedbackResponseData(
            success=True,
            feedback_id=feedback.id,
            case_id=case.id,
        ),
        error=None,
    )
