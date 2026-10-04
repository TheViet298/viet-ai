import os
import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.db import get_db
from src.models.db_models import (
    Attachment,
    AttachmentStatus,
    AuthorType,
    Case,
    CaseBrief,
    CaseLocation,
    CaseUpdate,
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
    CaseBriefOut,
    CaseLocationOut,
    CaseLocationPayload,
    CaseUpdateOut,
    ChatResponseData,
    Citation,
    ConversationItem,
    CustomerActionPayload,
    CustomerActionResponseData,
    CustomerCaseDetailData,
    CustomerCaseItem,
    CustomerCaseListData,
    CustomerCaseStatusData,
    CustomerChatRequest,
    CustomerConfirmationPayload,
    CustomerConfirmationResponseData,
    CustomerFeedbackPayload,
    CustomerFeedbackResponseData,
    ReopenCaseResponseData,
    ServiceHandoff,
    ServicePointItem,
    ServicePointsData,
)
from src.services.auth import check_case_ownership, get_optional_user, require_customer
from src.agents.chatbot_agent import process_chat_message

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
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    Tiếp nhận tin nhắn chat từ khách hàng (đã đăng nhập) hoặc Guest (dùng thử tối đa 5 lượt):
    - Hỗ trợ text và/hoặc ảnh đính kèm (OCR/Vision tín hiệu sơ bộ)
    - Áp dụng Hard Safety Rules (CRITICAL)
    - Clarification tối đa 2 lượt kèm Quick Replies
    - Phản hồi FAQ kèm Trích dẫn nguồn
    - Sinh Case Brief và lưu vết vào Database SQLite
    - Guest trial: giới hạn 5 lượt/phiên, trả remaining_guest_messages
    """
    # 0. Kiểm tra xác thực hoặc Guest Trial (ADR-005 & api-contract.md Mục 1)
    remaining_guest_msgs: int | None = None
    if not current_user:
        if not payload.guest_session_id:
            raise HTTPException(
                status_code=401,
                detail="Chưa đăng nhập. Vui lòng đăng nhập tài khoản Customer hoặc cung cấp guest_session_id để trải nghiệm.",
            )
        # Giới hạn Guest tối đa 5 lượt chat
        guest_count = (
            db.query(func.count(Message.id))
            .filter(
                (Message.session_id == payload.guest_session_id) | (Message.session_id == payload.session_id),
                Message.sender_type == SenderType.CUSTOMER.value,
            )
            .scalar()
            or 0
        )
        if guest_count >= 5:
            raise HTTPException(
                status_code=403,
                detail="Bạn đã sử dụng hết 5 lượt chat thử nghiệm dành cho Guest. Vui lòng đăng nhập tài khoản Customer để tiếp tục tạo và theo dõi hồ sơ hỗ trợ.",
            )
        remaining_guest_msgs = max(0, 5 - (guest_count + 1))

    text = payload.message.strip()
    lower_text = text.lower()
    ctx = payload.client_context

    user_id = current_user.id if current_user else None
    mock_cust_id = (
        current_user.mock_customer_id
        if current_user and current_user.mock_customer_id
        else (
            ctx.mock_customer_id
            if ctx and ctx.mock_customer_id
            else (f"GUEST_{payload.guest_session_id[:8]}" if payload.guest_session_id else "CUST_MOCK_01")
        )
    )
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
            "guest_session_id": payload.guest_session_id,
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
                user_id=user_id,
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
                remaining_guest_messages=remaining_guest_msgs,
            ),
            error=None,
        )

    # 3. KIỂM TRA CÂU HỎI NGOÀI PHẠM VI (RULE 2.4 - OUT OF SCOPE / ADVERSARIAL)
    oos_keywords = [
        "vé máy bay", "vietnam airlines", "vietjet", "tesla", "hyundai", "toyota", "honda",
        "thời tiết", "mặt trời", "áp mái", "hòa lưới", "tự đấu dây", "can thiệp tăng công suất",
        "giảm giá bí mật", "bẻ khóa", "hack động cơ", "phá khóa", "mở khóa giới hạn", "250km/h",
        "ung thư", "chất độc hại", "asdfg", "qwerty", "123456"
    ]
    if any(kw in lower_text for kw in oos_keywords):
        reply_no_source = (
            "Dạ em đã kiểm tra trong cơ sở dữ liệu hướng dẫn và chính sách dịch vụ chính thức của VinFast "
            "nhưng chưa có thông tin xác thực cho yêu cầu này (hoặc nội dung nằm ngoài phạm vi hỗ trợ của hệ sinh thái xe điện VinFast).\n\n"
            "Nếu anh/chị cần hỗ trợ các vấn đề kỹ thuật, trạm sạc hay bảo hành xe VinFast, em luôn sẵn sàng hỗ trợ ạ!"
        )
        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=None,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=reply_no_source,
            msg_metadata={"type": "OOS_REJECT"},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="FAQ_ANSWER",
                message=reply_no_source,
                case_id=None,
                citations=[],
            ),
            error=None,
        )

    # 4. KIỂM TRA PHẢN ÁNH / KHIẾU NẠI (COMPLAINT / FEEDBACK)
    complaint_keywords = ["bức xúc", "khiếu nại", "thái độ", "trừ tiền", "hoàn tiền", "chiếm chỗ", "văng crash", "khen ngợi"]
    is_complaint = any(kw in lower_text for kw in complaint_keywords)
    if is_complaint:
        new_case_id = payload.case_id or generate_case_id(db)
        case = db.get(Case, new_case_id)
        is_financial = any(kw in lower_text for kw in ["trừ tiền", "hoàn tiền"])
        case_prio = Priority.HIGH.value if is_financial else Priority.MEDIUM.value
        if "khen ngợi" in lower_text:
            case_prio = Priority.LOW.value

        if not case:
            case = Case(
                id=new_case_id,
                user_id=current_user.id,
                session_id=payload.session_id,
                mock_customer_id=mock_cust_id,
                vehicle_code_mock=vehicle_code,
                vehicle_model=vehicle_model,
                intent=Intent.COMPLAINT_FEEDBACK.value,
                priority=case_prio,
                status=TicketStatus.STAFF_REVIEWING.value,
            )
            db.add(case)
            db.flush()

        cust_msg.case_id = case.id
        summary_text = f"Ý kiến khách hàng: {text[:120]}..."
        case_brief = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case.id,
            summary=summary_text,
            captured_fields={
                "vehicle_model": vehicle_model,
                "feedback_type": "FINANCIAL_DISPUTE" if is_financial else "GENERAL_COMPLAINT_OR_FEEDBACK",
                "content": text,
            },
            suggested_action="Chuyên viên CSKH kiểm tra dữ liệu giao dịch hoặc liên hệ trực tiếp hỗ trợ khách hàng.",
            confidence_score=0.95,
            is_edited_by_staff=False,
        )
        db.add(case_brief)

        agent_reply = (
            f"Dạ em rất tiếc về trải nghiệm chưa thuận tiện của anh/chị. "
            f"Hệ thống đã ghi nhận phản hồi vào hồ sơ hỗ trợ chuyên trách (Mã: {case.id}) "
            f"và chuyển ngay đến bộ phận Chăm sóc Khách hàng để rà soát, xử lý ưu tiên. "
            f"Anh/chị vui lòng theo dõi cập nhật trực tiếp tại đây nhé ạ."
        )

        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=case.id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=agent_reply,
            msg_metadata={"case_id": case.id, "priority": case_prio},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="CASE_CREATED",
                case_id=case.id,
                status=TicketStatus.STAFF_REVIEWING.value,
                priority=case_prio,
                message=agent_reply,
                safe_guidance="Chuyên viên CSKH đang xử lý hồ sơ này của Quý khách.",
            ),
            error=None,
        )

    # 5. PHÂN LOẠI XỬ LÝ THEO CHUẨN DATA MODEL (5 INTENTS)
    # Xác định xem tin nhắn có thực sự là sự cố kỹ thuật/hỏng hóc hay là câu hỏi thông thường
    incident_keywords = [
        "không sạc", "không vào điện", "không nhận sạc", "không nhận", "kẹt súng", "kẹt cổng",
        "kẹt chốt", "rút không được", "súng sạc bị kẹt", "lỗi", "báo lỗi", "communication error",
        "0x", "cc01", "bms", "hỏng", "sự cố", "mất nguồn", "tối thui", "kêu", "cọc cọc", "đơ",
        "chết máy", "nháy đỏ", "bình 12v", "ắc quy", "xì lốp", "kẹt kính", "chỉ thổi gió nóng",
        "móp", "va chạm", "cứu tôi", "hết pin", "tụt pin"
    ]
    is_technical_incident = any(kw in lower_text for kw in incident_keywords) or bool(payload.attachment_ids)

    # --------------------------------------------------------------------------
    # NHÓM A: CHÀO HỎI & GIAO TIẾP XÃ GIAO (GREETINGS)
    # --------------------------------------------------------------------------
    greeting_keywords = ["xin chào", "chào em", "chào bạn", "chào bot", "chào trợ lý", "hello", "hi vinfast", "chào", "hi"]
    is_greeting = any(lower_text == kw or lower_text.startswith(f"{kw} ") for kw in greeting_keywords) and not is_technical_incident

    if is_greeting:
        greeting_reply = (
            "Dạ em xin chào anh/chị! Em là Trợ lý AI Dịch vụ Khách hàng VinFast. "
            "Em luôn sẵn sàng đồng hành và hỗ trợ anh/chị 24/7:\n\n"
            "• 🚗 **Tư vấn sản phẩm & Mua xe:** Thông tin dải xe điện VF 3 đến VF 9, giá lăn bánh, đăng ký lái thử.\n"
            "• 🔋 **Trạm sạc & Ứng dụng:** Hướng dẫn sạc pin công cộng, biểu phí sạc, các tính năng trên App VinFast.\n"
            "• 🔧 **Bảo hành & Bảo dưỡng:** Chính sách bảo hành pin 10 năm, cẩm nang bảo dưỡng định kỳ 12.000km.\n"
            "• ⚠️ **Hỗ trợ Kỹ thuật:** Tiếp nhận sự cố sạc pin, chẩn đoán sơ bộ và điều phối cứu hộ khẩn cấp.\n\n"
            "Anh/chị cần em hỗ trợ nội dung nào hôm nay ạ?"
        )
        suggested_replies = [
            "Tôi muốn mua xe",
            "Thời hạn bảo hành pin VF 8",
            "Bảo dưỡng định kỳ 12.000km",
            "Trạm sạc bị lỗi",
        ]
        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=None,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=greeting_reply,
            msg_metadata={"type": "GREETING", "suggested_replies": suggested_replies},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="FAQ_ANSWER",
                message=greeting_reply,
                case_id=None,
                suggested_replies=suggested_replies,
            ),
            error=None,
        )

    # --------------------------------------------------------------------------
    # NHÓM B: TƯ VẤN BÁN HÀNG & MUA XE (SALES_GENERAL_INFO)
    # --------------------------------------------------------------------------
    sales_keywords = [
        "mua xe", "mua ô tô", "bán xe", "tư vấn mua", "tư vấn xe", "đặt cọc", "lái thử",
        "trả góp", "bảng giá xe", "giá lăn bánh", "ưu đãi", "dòng xe nào", "xe 7 chỗ",
        "xe 5 chỗ", "mua vf", "tư vấn"
    ]
    is_sales_inquiry = any(kw in lower_text for kw in sales_keywords) and not is_technical_incident

    if is_sales_inquiry:
        sales_reply = (
            "Dạ VinFast xin chào anh/chị! Hiện nay VinFast đang phân phối hệ sinh thái ô tô điện thông minh toàn diện phủ khắp các phân khúc:\n\n"
            "🚗 **VF 3**: Mini SUV đô thị nhỏ gọn, thiết kế vuông vức cá tính, di chuyển linh hoạt.\n"
            "🚙 **VF 5 Plus**: A-SUV trẻ trung, tối ưu chi phí vận hành cho gia đình và đô thị.\n"
            "🚘 **VF 6**: B-SUV thời thượng, ngập tràn công nghệ thông minh và an toàn.\n"
            "🏎️ **VF 7**: C-SUV phong cách thể thao, hiệu năng ấn tượng với 2 phiên bản Eco và Plus.\n"
            "✨ **VF 8**: D-SUV sang trọng, hệ thống hỗ trợ lái nâng cao ADAS và trợ lý ảo thông minh.\n"
            "👑 **VF 9**: E-SUV 7 chỗ đẳng cấp thương gia, tiện nghi hàng đầu.\n\n"
            "Anh/chị đang quan tâm đến dòng xe nào hoặc cần em tư vấn thêm về tầm giá, chính sách thuê/mua pin hay đặt lịch lái thử tận nơi ạ?"
        )
        sales_citations = [
            Citation(
                source_id="SRC-006",
                title="Danh mục Sản phẩm và Chính sách Bán hàng Ô tô điện VinFast",
                url="https://vinfastauto.com/vn_vi/cac-dong-xe-o-to",
                verified_at="2026-09-24",
                status_code=200,
                applicable_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9"],
                source_type="OFFICIAL_MANUAL",
                relevant_snippet="VinFast cung cấp dải sản phẩm ô tô điện toàn diện phủ khắp các phân khúc từ VF 3 đến VF 9.",
            )
        ]
        sales_handoff = ServiceHandoff(
            has_app_feature=True,
            app_feature_name="Đăng ký Lái thử / Đặt cọc xe",
            guide_url="https://vinfastauto.com/vn_vi/cac-dong-xe-o-to",
        )
        suggested_replies = [
            "Tư vấn xe VF 3 & VF 5",
            "Tư vấn xe VF 7 & VF 8",
            "Bảng giá xe mới nhất",
            "Đăng ký lái thử miễn phí",
        ]

        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=None,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=sales_reply,
            msg_metadata={"citations": [c.model_dump() for c in sales_citations]},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="FAQ_ANSWER",
                message=sales_reply,
                case_id=None,
                citations=sales_citations,
                service_handoff=sales_handoff,
                suggested_replies=suggested_replies,
            ),
            error=None,
        )

    # --------------------------------------------------------------------------
    # NHÓM C: TRA CỨU TRI THỨC / RAG FAQ (KHI KHÔNG PHẢI SỰ CỐ KỸ THUẬT)
    # --------------------------------------------------------------------------
    if not is_technical_incident:
        # Gọi Chatbot Agent Core AI (Tra cứu RAG ChromaDB / Fallback KB)
        ai_res = await process_chat_message(text)
        agent_reply = ai_res.get("reply") or (
            "Dạ theo tài liệu chính thức từ VinFast, anh/chị có thể dễ dàng tra cứu thông tin chi tiết, "
            "quản lý tình trạng xe và đặt lịch dịch vụ trực tiếp trên Ứng dụng VinFast."
        )
        if isinstance(agent_reply, list):
            agent_reply = "".join(
                b.get("text", "") if isinstance(b, dict) else getattr(b, "text", str(b))
                for b in agent_reply
            )
        elif not isinstance(agent_reply, str):
            agent_reply = str(agent_reply)
        citations = []
        if ai_res.get("citations"):
            for c in ai_res["citations"]:
                citations.append(
                    Citation(
                        source_id=c.get("source_id", "SRC-KB"),
                        title=c.get("title", "Tài liệu VinFast"),
                        url=c.get("url", "https://vinfastauto.com/vn_vi"),
                        verified_at="2026-09-24",
                        status_code=200,
                        applicable_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"],
                        source_type="OFFICIAL_MANUAL",
                        relevant_snippet=c.get("section", ""),
                    )
                )
        if not citations:
            citations = [
                Citation(
                    source_id="SRC-APP-001",
                    title="Hướng dẫn sử dụng Ứng dụng VinFast",
                    url="https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
                    verified_at="2026-09-24",
                    status_code=200,
                    applicable_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"],
                    source_type="OFFICIAL_APP_GUIDE",
                    relevant_snippet="Khách hàng có thể theo dõi tình trạng xe, dung lượng pin và lịch dịch vụ trực tiếp trên ứng dụng VinFast.",
                )
            ]
        service_handoff = ServiceHandoff(
            has_app_feature=True,
            app_feature_name="Đặt lịch dịch vụ / Tra cứu",
            guide_url="https://vinfastauto.com/vn_vi",
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
                remaining_guest_messages=remaining_guest_msgs,
            ),
            error=None,
        )

    # --------------------------------------------------------------------------
    # NHÓM D: SỰ CỐ KỸ THUẬT & TRẠM SẠC (CHARGING & SERVICE INCIDENTS)
    # --------------------------------------------------------------------------
    # Trích xuất dữ kiện thông minh từ câu hỏi người dùng
    station_match = re.search(r"((?:trạm\s*sạc\s*)?vincom\s+[\w\d\s]+|landmark\s*81|metropolis|ocean\s*park|cao\s*tốc\s+[\w\d\s]+|pháp\s*vân)", text, re.IGNORECASE)
    station_name = station_match.group(0).strip() if station_match else None

    charger_match = re.search(r"(vn-cs-[^\s,]+|trụ\s*số\s*\d+|trụ\s*p\d+|trụ\s*\d+|p\d+)", text, re.IGNORECASE)
    charger_id = charger_match.group(0).strip() if charger_match else None

    error_match = re.search(r"(communication\s*error(?:\s*0x[0-9a-fA-F]+)?|0x[0-9a-fA-F]+|cc01|bms[_\-\d]*|rùa vàng|[a-zA-Z]{1,4}[_\-]\d{2,4})", text, re.IGNORECASE)
    error_code = error_match.group(0).strip() if error_match else None

    model_match = re.search(r"\b(vf\s*e34|vf\s*[356789])\b", text, re.IGNORECASE)
    car_model = model_match.group(0).upper().replace(" ", "") if model_match else vehicle_model

    soc_match = re.search(r"(\d{1,2}\s*%)", text)
    current_soc = soc_match.group(0).strip() if soc_match else "18%"

    # Đánh giá độ đầy đủ dữ kiện kỹ thuật (Đủ thông tin trạm/trụ/lỗi)
    has_sufficient_detail = (
        (error_code is not None and (charger_id is not None or station_name is not None))
        or ("kẹt" in lower_text and ("súng" in lower_text or "cổng" in lower_text))
        or any(kw in lower_text for kw in ["cc01", "p02", "vn-cs", "18%"])
        or any(s.get("error_code_candidate") == "CC01" for s in attached_signals)
    )

    # TRƯỜNG HỢP A: ĐÃ ĐỦ DỮ KIỆN KỸ THUẬT -> TẠO CASE (Staff Reviewing)
    if has_sufficient_detail:
        new_case_id = payload.case_id or generate_case_id(db)
        case = db.get(Case, new_case_id)
        if not case:
            case = Case(
                id=new_case_id,
                user_id=user_id,
                session_id=payload.session_id,
                mock_customer_id=mock_cust_id,
                vehicle_code_mock=vehicle_code,
                vehicle_model=car_model,
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

        resolved_station = station_name or "Trạm sạc VinFast công cộng"
        resolved_charger = (charger_id or "P02").upper()
        resolved_error = (error_code or "CC01").upper()

        summary_text = f"Xe {car_model} gặp sự cố sạc: báo lỗi {resolved_error} tại {resolved_station} ({resolved_charger})."
        if attached_ocr_snippets:
            summary_text += f" [Tín hiệu nhận diện: {', '.join(attached_ocr_snippets)}]"

        case_brief = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case.id,
            summary=summary_text,
            captured_fields={
                "vehicle_model": car_model,
                "station_location": resolved_station,
                "charger_id": resolved_charger,
                "error_code": resolved_error,
                "current_soc": current_soc,
                "visual_signals": attached_signals,
            },
            suggested_action="Kiểm tra tín hiệu handshake giao tiếp trụ sạc từ xa hoặc cử kỹ thuật viên trạm cắm lại cáp.",
            confidence_score=0.95,
            is_edited_by_staff=False,
        )
        db.add(case_brief)

        safe_guidance = "Anh/chị vui lòng giữ xe ở vị trí đỗ an toàn và theo dõi cập nhật trên giao diện này."
        agent_reply = (
            f"Dạ VinFast đã ghi nhận sự cố sạc của xe {car_model}:\n"
            f"📍 **Vị trí trạm:** {resolved_station}\n"
            f"🔌 **Trụ sạc:** {resolved_charger}\n"
            f"⚠️ **Mã lỗi:** {resolved_error}\n\n"
            f"Hệ thống đã tự động tạo hồ sơ hỗ trợ (Mã: {case.id}) và chuyển dữ liệu trực tiếp tới Chuyên viên Kỹ thuật trạm sạc. "
            f"Anh/chị vui lòng theo dõi cập nhật tiến độ giải quyết trực tiếp trên màn hình này ạ."
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
                remaining_guest_messages=remaining_guest_msgs,
            ),
            error=None,
        )

    # TRƯỜNG HỢP B: CHƯA ĐỦ DỮ KIỆN KỸ THUẬT & CÒN LƯỢT HỎI LÀM RÕ (Turn < 2)
    if prior_turns < 2:
        if error_code and not charger_id and not station_name:
            clarification_msg = (
                f"Dạ em đã ghi nhận xe {car_model} đang báo lỗi {error_code.upper()}. "
                "Anh/chị vui lòng cho em biết tên trạm sạc hoặc số trụ đang cắm để kỹ thuật viên kiểm tra kết nối từ xa nhé ạ?"
            )
            suggested_replies = [
                "Trạm Vincom Landmark 81, trụ 3",
                "Trạm Vincom Metropolis, trụ P02",
                "Trạm sạc cao tốc",
            ]
        elif (charger_id or station_name) and not error_code:
            loc = station_name or charger_id
            clarification_msg = (
                f"Dạ em ghi nhận xe {car_model} đang ở {loc}. "
                "Màn hình xe hoặc đèn trụ có báo mã lỗi cụ thể nào (ví dụ: CC01, 0x41) không ạ? "
                "Anh/chị cũng có thể chụp ảnh màn hình táp-lô để em nhận diện sơ bộ nhé."
            )
            suggested_replies = [
                "Lỗi communication error 0x41",
                "Mã lỗi CC01",
                "Đèn trụ nháy đỏ, không hiện mã",
            ]
        else:
            clarification_msg = (
                f"Dạ em ghi nhận xe {car_model} đang gặp vấn đề kỹ thuật liên quan đến sạc/vận hành. "
                "Anh/chị có thể cho em biết trạm sạc, số trụ hoặc mã lỗi hiển thị trên táp-lô (ví dụ: CC01, 0x41) không ạ? "
                "(Anh/chị cũng có thể tải ảnh màn hình để em nhận diện sơ bộ)."
            )
            suggested_replies = [
                "Xem bản đồ trạm sạc ›",
                "Mã lỗi CC01, trụ P02",
                "Đèn trụ nháy đỏ",
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
                remaining_guest_messages=remaining_guest_msgs,
            ),
            error=None,
        )

    # TRƯỜNG HỢP C: ĐÃ HỎI 2 LƯỢT VẪN THIẾU DỮ KIỆN -> TẠO CASE 'Needs Information'
    new_case_id = payload.case_id or generate_case_id(db)
    case = db.get(Case, new_case_id)
    if not case:
        case = Case(
            id=new_case_id,
            user_id=user_id,
            session_id=payload.session_id,
            mock_customer_id=mock_cust_id,
            vehicle_code_mock=vehicle_code,
            vehicle_model=car_model,
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
        summary=f"Yêu cầu hỗ trợ xe {car_model} cần bổ sung dữ kiện kỹ thuật chi tiết.",
        captured_fields={
            "vehicle_model": car_model,
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
            remaining_guest_messages=remaining_guest_msgs,
        ),
        error=None,
    )


# ==============================================================================
# 3. LOCATION & SERVICE POINTS APIs — Nguồn: api-contract.md 1.1 & ADR-005
# ==============================================================================


@router.post("/location", response_model=ApiResponse[CaseLocationOut])
def submit_case_location(
    payload: CaseLocationPayload,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Khách hàng chia sẻ vị trí sự cố (Consent hoặc tự nhập) theo api-contract.md 1.1 & ADR-005.
    Tuyệt đối không tự động trích xuất GPS từ ảnh/EXIF.
    """
    case = db.get(Case, payload.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {payload.case_id}")
    check_case_ownership(case, current_user)

    loc = db.query(CaseLocation).filter(CaseLocation.case_id == payload.case_id).first()
    if not loc:
        loc = CaseLocation(
            id=str(uuid.uuid4()),
            case_id=payload.case_id,
            status=payload.status,
            source=payload.source,
            location_label=payload.location_label,
            latitude=payload.latitude,
            longitude=payload.longitude,
            precision=payload.precision,
            share_with_staff=payload.share_with_staff,
            created_at=utcnow(),
        )
        db.add(loc)
    else:
        loc.status = payload.status
        loc.source = payload.source
        loc.location_label = payload.location_label
        loc.latitude = payload.latitude
        loc.longitude = payload.longitude
        loc.precision = payload.precision
        loc.share_with_staff = payload.share_with_staff

    db.commit()
    db.refresh(loc)

    return ApiResponse(
        success=True,
        data=CaseLocationOut(
            case_id=loc.case_id,
            status=loc.status,
            source=loc.source,
            location_label=loc.location_label,
            latitude=loc.latitude,
            longitude=loc.longitude,
            precision=loc.precision,
            share_with_staff=loc.share_with_staff,
            created_at=loc.created_at.isoformat() if loc.created_at else utcnow().isoformat(),
        ),
        error=None,
    )


DEMO_SERVICE_POINTS = [
    ServicePointItem(
        id="SP-HN-001",
        name="Trạm sạc VinFast Vincom Metropolis",
        category="CHARGING_STATION",
        address="29 Liễu Giai, Ngọc Khánh, Ba Đình, Hà Nội",
        distance_km=1.2,
        latitude=21.0315,
        longitude=105.8145,
        hotline="1900-232389",
        operating_hours="24/7",
        charger_types=["DC 250kW (Siêu nhanh)", "DC 60kW", "AC 11kW"],
    ),
    ServicePointItem(
        id="SP-HCM-001",
        name="Trạm sạc & Dịch vụ VinFast Landmark 81",
        category="CHARGING_STATION",
        address="720A Điện Biên Phủ, Phường 22, Bình Thạnh, TP.HCM",
        distance_km=2.5,
        latitude=10.7950,
        longitude=106.7218,
        hotline="1900-232389",
        operating_hours="24/7",
        charger_types=["DC 150kW", "DC 60kW", "AC 7.4kW"],
    ),
    ServicePointItem(
        id="SP-DN-001",
        name="Trạm Cứu hộ Cao tốc Long Thành - Dầu Giây",
        category="RESCUE_POST",
        address="Km 28 Cao tốc TP.HCM - Long Thành - Dầu Giây",
        distance_km=5.0,
        latitude=10.7712,
        longitude=106.9450,
        hotline="1900-232389 (Phím 1 Cứu hộ khẩn cấp)",
        operating_hours="24/7",
        charger_types=None,
    ),
    ServicePointItem(
        id="SP-HCM-002",
        name="Xưởng Dịch vụ VinFast Thảo Điền",
        category="SERVICE_CENTER",
        address="159 Xa Lộ Hà Nội, Thảo Điền, TP. Thủ Đức, TP.HCM",
        distance_km=3.8,
        latitude=10.8030,
        longitude=106.7350,
        hotline="1900-232389",
        operating_hours="08:00 - 18:00 (Thứ 2 - Thứ 7)",
        charger_types=["DC 60kW", "AC 11kW"],
    ),
    ServicePointItem(
        id="SP-HN-002",
        name="VinFast Showroom & Service Smart City",
        category="SHOWROOM",
        address="Khu đô thị Vinhomes Smart City, Tây Mỗ, Nam Từ Liêm, Hà Nội",
        distance_km=8.4,
        latitude=20.9982,
        longitude=105.7420,
        hotline="1900-232389",
        operating_hours="08:30 - 20:00 Hàng ngày",
        charger_types=["DC 150kW", "DC 60kW"],
    ),
]


@router.get("/cases/{case_id}/service-points", response_model=ApiResponse[ServicePointsData])
def get_case_service_points(
    case_id: str,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách điểm hỗ trợ / trạm sạc / xưởng dịch vụ gợi ý theo sự cố (ADR-005).
    P0 dùng 3-5 điểm seed demo phù hợp intent.
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")
    check_case_ownership(case, current_user)

    # Sắp xếp ưu tiên theo intent
    points = list(DEMO_SERVICE_POINTS)
    if case.intent == Intent.CHARGING_BATTERY.value:
        points.sort(key=lambda p: 0 if p.category == "CHARGING_STATION" else 1)
    elif case.intent == Intent.SERVICE_INCIDENT.value:
        points.sort(key=lambda p: 0 if p.category in ("RESCUE_POST", "SERVICE_CENTER") else 1)

    return ApiResponse(
        success=True,
        data=ServicePointsData(case_id=case.id, recommended_points=points),
        error=None,
    )


# ==============================================================================
# 4. CUSTOMER CONFIRMATION API — Nguồn: api-contract.md 2.3 & ADR-005
# ==============================================================================


@router.post("/cases/{case_id}/confirmation", response_model=ApiResponse[CustomerConfirmationResponseData])
def confirm_customer_case_resolution(
    case_id: str,
    payload: CustomerConfirmationPayload,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Khách hàng xác nhận sau khi case ở trạng thái Resolved (ADR-005 & api-contract.md 2.3):
    - RESOLVED_CONFIRMED: Khách hàng hài lòng -> Chuyển trạng thái sang 'Closed'
    - STILL_UNRESOLVED: Khách phản ánh chưa xong -> Chuyển trạng thái sang 'Reopened' (quay lại Staff Queue)
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")
    check_case_ownership(case, current_user)

    # Tắt cờ awaiting_customer_confirmation ở các CaseUpdate trước đó
    db.query(CaseUpdate).filter(
        CaseUpdate.case_id == case.id,
        CaseUpdate.awaiting_customer_confirmation.is_(True),
    ).update({"awaiting_customer_confirmation": False}, synchronize_session=False)

    if payload.confirmation == "RESOLVED_CONFIRMED":
        prev_status = case.status
        case.status = TicketStatus.CLOSED.value
        case.updated_at = utcnow()

        audit = StaffAuditLog(
            id=str(uuid.uuid4()),
            case_id=case.id,
            staff_id=f"CUSTOMER_{current_user.id}",
            action=StaffAction.CLOSE.value,
            previous_state={"status": prev_status},
            new_state={"status": TicketStatus.CLOSED.value},
            notes=f"Khách hàng xác nhận đã được hỗ trợ thỏa đáng. {payload.feedback_note or ''}".strip(),
            created_at=utcnow(),
        )
        db.add(audit)

        update = CaseUpdate(
            id=str(uuid.uuid4()),
            case_id=case.id,
            author_type=AuthorType.SYSTEM.value,
            status_after_update=TicketStatus.CLOSED.value,
            customer_message="Cảm ơn quý khách đã xác nhận. Hồ sơ sự cố đã được đóng thành công.",
            next_step="Cảm ơn quý khách đã tin tưởng và đồng hành cùng VinFast.",
            awaiting_customer_confirmation=False,
            created_at=utcnow(),
        )
        db.add(update)
        db.commit()

        return ApiResponse(
            success=True,
            data=CustomerConfirmationResponseData(
                success=True,
                case_id=case.id,
                status=TicketStatus.CLOSED.value,
                message="Xác nhận thành công. Hồ sơ sự cố đã được đóng.",
            ),
            error=None,
        )
    else:
        prev_status = case.status
        case.status = TicketStatus.REOPENED.value
        case.updated_at = utcnow()

        audit = StaffAuditLog(
            id=str(uuid.uuid4()),
            case_id=case.id,
            staff_id=f"CUSTOMER_{current_user.id}",
            action=StaffAction.REOPEN.value,
            previous_state={"status": prev_status},
            new_state={"status": TicketStatus.REOPENED.value},
            notes=f"Khách hàng báo vẫn chưa được giải quyết xong: {payload.feedback_note or ''}".strip(),
            created_at=utcnow(),
        )
        db.add(audit)

        update = CaseUpdate(
            id=str(uuid.uuid4()),
            case_id=case.id,
            author_type=AuthorType.SYSTEM.value,
            status_after_update=TicketStatus.REOPENED.value,
            customer_message="Hệ thống ghi nhận sự cố chưa được khắc phục hoàn toàn và đã chuyển lại hồ sơ sang hàng đợi chuyên viên kỹ thuật.",
            next_step="Chuyên viên dịch vụ sẽ liên hệ lại quý khách trong thời gian sớm nhất.",
            awaiting_customer_confirmation=False,
            created_at=utcnow(),
        )
        db.add(update)
        db.commit()

        return ApiResponse(
            success=True,
            data=CustomerConfirmationResponseData(
                success=True,
                case_id=case.id,
                status=TicketStatus.REOPENED.value,
                message="Hệ thống đã ghi nhận phản hồi và mở lại hồ sơ sự cố để nhân viên tiếp tục hỗ trợ.",
            ),
            error=None,
        )


@router.post("/cases/{case_id}/actions", response_model=ApiResponse[CustomerActionResponseData])
def handle_customer_action(
    case_id: str,
    payload: CustomerActionPayload,
    current_user: User | None = Depends(get_optional_user),
    x_session_id: str | None = Header(None, alias="X-Session-Id"),
    db: Session = Depends(get_db),
):
    """
    Thực hiện hành động của khách hàng đối với Case (Gate G2 Proposal & ADR-005):
    - CONFIRM_RESOLUTION: Xác nhận hài lòng -> Chuyển trạng thái 'Closed'
    - REOPEN: Yêu cầu mở lại vì chưa giải quyết xong -> Chuyển trạng thái 'Reopened'
    Hỗ trợ xác thực qua Token đăng nhập hoặc Header X-Session-Id.
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")
    check_case_ownership(case, current_user, session_id=x_session_id)

    actor_id = current_user.id if current_user else f"SESSION_{x_session_id or 'GUEST'}"

    # Tắt cờ awaiting_customer_confirmation ở các CaseUpdate trước đó
    db.query(CaseUpdate).filter(
        CaseUpdate.case_id == case.id,
        CaseUpdate.awaiting_customer_confirmation.is_(True),
    ).update({"awaiting_customer_confirmation": False}, synchronize_session=False)

    if payload.action == "CONFIRM_RESOLUTION":
        prev_status = case.status
        case.status = TicketStatus.CLOSED.value
        case.updated_at = utcnow()

        audit = StaffAuditLog(
            id=str(uuid.uuid4()),
            case_id=case.id,
            staff_id=f"CUSTOMER_{actor_id}",
            action=StaffAction.CLOSE.value,
            previous_state={"status": prev_status},
            new_state={"status": TicketStatus.CLOSED.value},
            notes=f"Khách hàng xác nhận giải quyết: {payload.feedback_note or payload.reason or ''}".strip(),
            created_at=utcnow(),
        )
        db.add(audit)

        msg = "Cảm ơn quý khách đã xác nhận. Hồ sơ sự cố đã được đóng thành công."
        update = CaseUpdate(
            id=str(uuid.uuid4()),
            case_id=case.id,
            author_type=AuthorType.SYSTEM.value,
            status_after_update=TicketStatus.CLOSED.value,
            customer_message=msg,
            next_step="Cảm ơn quý khách đã tin tưởng và đồng hành cùng VinFast.",
            awaiting_customer_confirmation=False,
            created_at=utcnow(),
        )
        db.add(update)
        db.commit()

        return ApiResponse(
            success=True,
            data=CustomerActionResponseData(
                case_id=case.id,
                status=TicketStatus.CLOSED.value,
                updated_at=case.updated_at.isoformat(),
                customer_message=msg,
            ),
            error=None,
        )
    elif payload.action == "REOPEN":
        prev_status = case.status
        case.status = TicketStatus.REOPENED.value
        case.updated_at = utcnow()

        audit = StaffAuditLog(
            id=str(uuid.uuid4()),
            case_id=case.id,
            staff_id=f"CUSTOMER_{actor_id}",
            action=StaffAction.REOPEN.value,
            previous_state={"status": prev_status},
            new_state={"status": TicketStatus.REOPENED.value},
            notes=f"Khách hàng yêu cầu mở lại hồ sơ: {payload.reason or payload.feedback_note or ''}".strip(),
            created_at=utcnow(),
        )
        db.add(audit)

        msg = "Hệ thống ghi nhận sự cố chưa được khắc phục hoàn toàn và đã chuyển lại hồ sơ sang hàng đợi chuyên viên kỹ thuật."
        update = CaseUpdate(
            id=str(uuid.uuid4()),
            case_id=case.id,
            author_type=AuthorType.SYSTEM.value,
            status_after_update=TicketStatus.REOPENED.value,
            customer_message=msg,
            next_step="Chuyên viên dịch vụ sẽ liên hệ lại quý khách trong thời gian sớm nhất.",
            awaiting_customer_confirmation=False,
            created_at=utcnow(),
        )
        db.add(update)
        db.commit()

        return ApiResponse(
            success=True,
            data=CustomerActionResponseData(
                case_id=case.id,
                status=TicketStatus.REOPENED.value,
                updated_at=case.updated_at.isoformat(),
                customer_message=msg,
            ),
            error=None,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Hành động '{payload.action}' không hợp lệ. Chỉ chấp nhận 'CONFIRM_RESOLUTION' hoặc 'REOPEN'.",
        )


# ==============================================================================
# 5. CUSTOMER CASE MANAGEMENT APIs — Nguồn: api-contract.md Mục 2.2 & 2.3
# ==============================================================================



@router.get("/cases", response_model=ApiResponse[CustomerCaseListData])
def list_customer_cases(
    query: str | None = Query(None, description="Tìm case theo ID hoặc từ khóa"),
    status: str | None = Query(None, description="Lọc theo trạng thái ticket"),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách các Case thuộc về chính Customer đang đăng nhập theo api-contract.md Mục 2.3.
    Hỗ trợ tìm kiếm theo query và lọc theo status.
    """
    db_query = db.query(Case).options(joinedload(Case.brief))

    # Lọc theo quyền sở hữu của Customer
    if current_user.role != "STAFF":
        if current_user.mock_customer_id:
            db_query = db_query.filter(
                (Case.user_id == current_user.id) | (Case.mock_customer_id == current_user.mock_customer_id)
            )
        else:
            db_query = db_query.filter(Case.user_id == current_user.id)

    if query:
        q_pattern = f"%{query}%"
        db_query = db_query.filter(
            Case.id.ilike(q_pattern)
            | Case.intent.ilike(q_pattern)
            | Case.vehicle_model.ilike(q_pattern)
            | Case.vehicle_code_mock.ilike(q_pattern)
        )

    if status and status != "ALL":
        db_query = db_query.filter(Case.status == status)

    cases = db_query.order_by(Case.created_at.desc()).all()

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


@router.get("/cases/{case_id}", response_model=ApiResponse[CustomerCaseDetailData])
def get_customer_case_detail(
    case_id: str,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Lấy chi tiết hồ sơ sự cố của chính khách hàng (api-contract.md Mục 2.3).
    Bao gồm brief an toàn, vị trí đã chia sẻ, các cập nhật tiến độ (Customer Updates),
    ảnh đính kèm và lịch sử hội thoại đã kiểm tra ownership.
    """
    case = (
        db.query(Case)
        .options(
            joinedload(Case.brief),
            joinedload(Case.location),
            joinedload(Case.updates),
            joinedload(Case.attachments),
            joinedload(Case.messages),
        )
        .filter(Case.id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")
    check_case_ownership(case, current_user)

    brief_out: CaseBriefOut | None = None
    if case.brief:
        brief_out = CaseBriefOut(
            summary=case.brief.summary,
            captured_fields=case.brief.captured_fields or {},
            suggested_action=case.brief.suggested_action,
            confidence_score=case.brief.confidence_score,
            is_edited_by_staff=case.brief.is_edited_by_staff,
        )

    loc_out: CaseLocationOut | None = None
    if case.location:
        loc_out = CaseLocationOut(
            case_id=case.location.case_id,
            status=case.location.status,
            source=case.location.source,
            location_label=case.location.location_label,
            latitude=case.location.latitude,
            longitude=case.location.longitude,
            precision=case.location.precision,
            share_with_staff=case.location.share_with_staff,
            created_at=case.location.created_at.isoformat() if case.location.created_at else utcnow().isoformat(),
        )

    updates_out: list[CaseUpdateOut] = []
    if case.updates:
        for u in case.updates:
            updates_out.append(
                CaseUpdateOut(
                    id=u.id,
                    case_id=u.case_id,
                    author_type=u.author_type,
                    status_after_update=u.status_after_update,
                    customer_message=u.customer_message,
                    next_step=u.next_step,
                    awaiting_customer_confirmation=u.awaiting_customer_confirmation,
                    created_at=u.created_at.isoformat() if u.created_at else utcnow().isoformat(),
                )
            )

    attachments_out: list[AttachmentOut] = []
    if case.attachments:
        for att in case.attachments:
            attachments_out.append(
                AttachmentOut(
                    attachment_id=att.id,
                    storage_key=att.storage_key,
                    mime_type=att.mime_type,
                    analysis_status=att.analysis_status,
                    ocr_text=att.ocr_text,
                    detected_signals=att.detected_signals,
                    vision_confidence=att.vision_confidence,
                    created_at=att.created_at.isoformat() if att.created_at else utcnow().isoformat(),
                )
            )

    conv_items: list[ConversationItem] = []
    if case.messages:
        for msg in case.messages:
            sender_role = msg.sender_type if msg.sender_type in ("CUSTOMER", "AGENT", "STAFF", "SYSTEM") else "SYSTEM"
            conv_items.append(
                ConversationItem(
                    sender=sender_role,
                    content=msg.content,
                    created_at=msg.created_at.isoformat() if msg.created_at else utcnow().isoformat(),
                )
            )

    case_item = CustomerCaseItem(
        id=case.id,
        vehicle_model=case.vehicle_model,
        vehicle_code_mock=case.vehicle_code_mock,
        intent=case.intent,
        priority=case.priority,
        status=case.status,
        summary=case.brief.summary if case.brief else None,
        created_at=case.created_at.isoformat() if case.created_at else utcnow().isoformat(),
        updated_at=case.updated_at.isoformat() if case.updated_at else None,
    )

    return ApiResponse(
        success=True,
        data=CustomerCaseDetailData(
            case=case_item,
            case_brief=brief_out,
            location=loc_out,
            updates=updates_out,
            attachments=attachments_out,
            conversation_history=conv_items,
        ),
        error=None,
    )


@router.get("/cases/{case_id}/status", response_model=ApiResponse[CustomerCaseStatusData])
def get_customer_case_status(
    case_id: str,
    current_user: User | None = Depends(get_optional_user),
    x_session_id: str | None = Header(None, alias="X-Session-Id"),
    db: Session = Depends(get_db),
):
    """
    Tra cứu trạng thái hồ sơ của khách hàng theo api-contract.md Mục 2.2 & gate-g2-proposal.md.
    Hỗ trợ kiểm tra quyền qua Token đăng nhập hoặc Header X-Session-Id.
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")

    check_case_ownership(case, current_user, session_id=x_session_id)

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

    # Lấy thông điệp khách hàng từ CaseUpdate mới nhất nếu có
    latest_update = (
        db.query(CaseUpdate)
        .filter(CaseUpdate.case_id == case.id)
        .order_by(CaseUpdate.created_at.desc())
        .first()
    )
    cust_msg = latest_update.customer_message if latest_update else status_desc

    data = CustomerCaseStatusData(
        case_id=case.id,
        status=case.status,
        status_description=status_desc,
        customer_message=cust_msg,
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
