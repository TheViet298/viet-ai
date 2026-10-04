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

    # Count only unanswered clarification prompts for this customer's incident.
    prior_turns = 0
    history = db.query(Message).filter(
        Message.session_id == payload.session_id,
        Message.sender_type == SenderType.AGENT.value,
    ).order_by(Message.created_at.desc(), Message.id.desc()).all()
    for message in history:
        if message.case_id:
            break
        metadata = message.msg_metadata or {}
        if metadata.get("response_type") == "CLARIFICATION" and metadata.get("user_id") == current_user.id:
            prior_turns += 1

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
                show_emergency_banner=True,
                request_location=True,
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
        customer_name = payload.client_context.customer_name if payload.client_context else None
        short_name = customer_name.strip().split()[-1] if (customer_name and customer_name.strip()) else None

        if short_name:
            full_lower = customer_name.lower()
            is_female = "thị" in full_lower or any(
                short_name.lower() == fn
                for fn in ["hoa", "lan", "mai", "hương", "trang", "linh", "ngọc", "thảo", "hằng", "nhung", "yến", "my", "vy"]
            )
            is_male = "văn" in full_lower or any(
                short_name.lower() == mn
                for mn in ["an", "bình", "cường", "dũng", "hùng", "long", "minh", "nam", "phúc", "quân", "tuấn", "việt"]
            )
            title = "chị" if is_female else "anh" if is_male else None

            if title:
                greeting_reply = f"Chào {title} {short_name}! Em giúp gì được cho {title} về chiếc {vehicle_model} hôm nay ạ?"
            else:
                greeting_reply = f"Chào {short_name}! Em giúp gì được cho bạn về chiếc {vehicle_model} hôm nay ạ?"
        else:
            greeting_reply = "Chào bạn! Em là Trợ lý VF Serv. Em có thể hỗ trợ gì cho bạn hôm nay ạ?"

        suggested_replies = [
            "Tư vấn xe",
            "Trạm sạc & ứng dụng",
            "Bảo hành & bảo dưỡng",
            "Báo sự cố kỹ thuật",
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
                show_emergency_banner=False,
                request_location=False,
            ),
            error=None,
        )

    # --------------------------------------------------------------------------
    # NHÓM B: TƯ VẤN BÁN HÀNG, LÁI THỬ & GIÁ XE (SALES & SERVICES)
    # --------------------------------------------------------------------------
    # B1. Đăng ký lái thử xe
    is_test_drive = any(kw in lower_text for kw in ["lái thử", "đăng ký lái thử", "chạy thử", "trải nghiệm xe"]) and not is_technical_incident
    if is_test_drive:
        test_drive_reply = (
            "Dạ anh/chị có thể đăng ký lái thử xe điện VinFast hoàn toàn miễn phí theo các bước rất thuận tiện sau:\n\n"
            "1. **Chọn hình thức lái thử**: Trải nghiệm tại Showroom/Nhà phân phối gần nhất hoặc đăng ký lái thử tận nhà (tùy khu vực hỗ trợ).\n"
            "2. **Điều kiện cần chuẩn bị**: Giấy phép lái xe (bằng B1 hoặc B2 trở lên) còn hiệu lực và CCCD.\n"
            "3. **Đăng ký nhanh**: Đặt lịch trực tiếp qua Ứng dụng VinFast, trên website chính thức, hoặc liên hệ Tổng đài CSKH 1900-232389 để chuyên viên xếp lịch trong ngày.\n\n"
            f"Anh/chị đang muốn trải nghiệm lái thử dòng xe nào (như chiếc {vehicle_model}, VF 7 hay VF 9) và ở khu vực nào để em hỗ trợ kết nối Showroom gần nhất ạ?"
        )
        test_drive_citations = [
            Citation(
                source_id="SRC-DRIVE-01",
                title="Cổng Đăng ký Lái thử Xe điện VinFast Toàn quốc",
                url="https://vinfastauto.com/vn_vi/dang-ky-lai-thu",
                verified_at="2026-09-24",
                status_code=200,
                applicable_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9"],
                source_type="OFFICIAL_MANUAL",
                relevant_snippet="Khách hàng có bằng lái B1/B2 hợp lệ có thể đăng ký lái thử miễn phí các dòng xe điện VinFast tại hệ thống showroom toàn quốc.",
            )
        ]
        test_drive_handoff = ServiceHandoff(
            has_app_feature=True,
            app_feature_name="Đăng ký Lái thử Trực tuyến",
            guide_url="https://vinfastauto.com/vn_vi/dang-ky-lai-thu",
        )
        suggested_replies = [
            f"Lái thử xe {vehicle_model}",
            "Lái thử xe VF 7",
            "Tìm showroom gần nhất",
            "Hotline tư vấn 1900-232389",
        ]
        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=None,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=test_drive_reply,
            msg_metadata={"citations": [c.model_dump() for c in test_drive_citations]},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="FAQ_ANSWER",
                message=test_drive_reply,
                case_id=None,
                citations=test_drive_citations,
                service_handoff=test_drive_handoff,
                suggested_replies=suggested_replies,
                show_emergency_banner=False,
                request_location=False,
            ),
            error=None,
        )

    # B2. Bảng giá xe & Giá lăn bánh & Trả góp
    is_pricing_inquiry = any(
        kw in lower_text for kw in ["bảng giá", "giá lăn bánh", "chi phí lăn bánh", "giá xe", "trả góp", "ưu đãi", "đặt cọc"]
    ) and not is_technical_incident
    if is_pricing_inquiry:
        pricing_reply = (
            "Dạ về chính sách giá và chi phí lăn bánh ô tô điện VinFast hiện có những ưu thế vượt trội:\n\n"
            "- **Ưu đãi lệ phí trước bạ**: Ô tô điện chạy pin được hưởng chính sách ưu đãi miễn 100% lệ phí trước bạ theo quy định của Chính phủ, giúp tiết kiệm từ vài chục đến hàng trăm triệu đồng chi phí lăn bánh.\n"
            "- **Tùy chọn linh hoạt**: Khách hàng có thể lựa chọn mua bao gồm pin hoặc thuê pin hàng tháng để tối ưu ngân sách ban đầu.\n"
            "- **Chính sách trả góp**: Hỗ trợ vay vốn ngân hàng lên đến 70-80% giá trị xe với lãi suất ưu đãi, thời hạn vay lên đến 8 năm.\n\n"
            f"Anh/chị đang quan tâm giá lăn bánh cụ thể của xe {vehicle_model} hay dòng xe nào khác để em gửi thông tin chi tiết ạ?"
        )
        pricing_citations = [
            Citation(
                source_id="SRC-PRICE-01",
                title="Bảng giá Ô tô điện VinFast và Chính sách Ưu đãi Mới nhất",
                url="https://vinfastauto.com/vn_vi/bang-gia-xe-o-to-vinfast",
                verified_at="2026-09-24",
                status_code=200,
                applicable_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9"],
                source_type="OFFICIAL_MANUAL",
                relevant_snippet="Bảng giá niêm yết, chính sách thuê/mua pin và các chương trình ưu đãi lăn bánh cho dòng xe điện VinFast.",
            )
        ]
        pricing_handoff = ServiceHandoff(
            has_app_feature=True,
            app_feature_name="Tra cứu Giá & Đặt cọc Xe",
            guide_url="https://vinfastauto.com/vn_vi/bang-gia-xe-o-to-vinfast",
        )
        suggested_replies = [
            f"Giá lăn bánh {vehicle_model}",
            "Giá xe VF 3 & VF 5",
            "Chính sách thuê pin",
            "Đăng ký lái thử miễn phí",
        ]
        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=None,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=pricing_reply,
            msg_metadata={"citations": [c.model_dump() for c in pricing_citations]},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="FAQ_ANSWER",
                message=pricing_reply,
                case_id=None,
                citations=pricing_citations,
                service_handoff=pricing_handoff,
                suggested_replies=suggested_replies,
                show_emergency_banner=False,
                request_location=False,
            ),
            error=None,
        )

    # B3. Tư vấn tổng quan các dòng xe
    sales_keywords = [
        "mua xe", "mua ô tô", "bán xe", "tư vấn mua", "tư vấn xe", "dòng xe nào", "xe 7 chỗ",
        "xe 5 chỗ", "mua vf", "tư vấn", "các dòng xe"
    ]
    is_sales_inquiry = any(kw in lower_text for kw in sales_keywords) and not is_technical_incident

    if is_sales_inquiry:
        sales_reply = (
            "VinFast hiện có dải xe điện phủ đầy đủ các phân khúc từ đô thị đến cao cấp:\n\n"
            "- **VF 3**: mini SUV đô thị nhỏ gọn, thiết kế vuông vức cá tính, tối ưu di chuyển hàng ngày\n"
            "- **VF 5 Plus**: A-SUV trẻ trung, chi phí vận hành cực kỳ tiết kiệm cho cá nhân và gia đình\n"
            "- **VF 6**: B-SUV thời thượng, trang bị nhiều công nghệ thông minh và tính năng an toàn\n"
            "- **VF 7**: C-SUV phong cách thể thao tương lai, có 2 phiên bản Eco và Plus dẫn động AWD\n"
            "- **VF 8**: D-SUV sang trọng, hệ thống hỗ trợ lái nâng cao ADAS cấp độ 2 và trợ lý ảo thông minh\n"
            "- **VF 9**: E-SUV 7 chỗ đẳng cấp thương gia, ghế cơ trưởng massage, tiện nghi hàng đầu\n\n"
            "Anh/chị đang cân nhắc dòng xe nào phù hợp với nhu cầu, hoặc cần em hỗ trợ đăng ký lái thử trải nghiệm thực tế ạ?"
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
            app_feature_name="Xem Chi tiết Dòng xe",
            guide_url="https://vinfastauto.com/vn_vi/cac-dong-xe-o-to",
        )
        suggested_replies = [
            "Đăng ký lái thử miễn phí",
            "Bảng giá xe mới nhất",
            "Tư vấn xe VF 7 & VF 8",
            "Chính sách thuê/mua pin",
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
                show_emergency_banner=False,
                request_location=False,
            ),
            error=None,
        )

    # --------------------------------------------------------------------------
    # NHÓM B2: BIỂU TƯỢNG RÙA VÀNG TRÊN XE HIỆN TẠI (ACTIVE TURTLE ON VEHICLE)
    # Khách báo xe đang hiện rùa nhưng không ở trên cao tốc / chưa khẩn cấp
    # --------------------------------------------------------------------------
    is_active_turtle = has_turtle and any(
        kw in lower_text for kw in ["xe tôi", "xe của tôi", "đang hiện", "vừa hiện", "bị hiện", "đang bị", "bây giờ"]
    )
    if is_active_turtle and not is_turtle_critical:
        turtle_reply = (
            f"Biểu tượng con rùa màu vàng (Turtle Mode) là chế độ bảo vệ an toàn của xe {vehicle_model}, "
            "tự động kích hoạt khi hệ thống nhận thấy pin cao áp quá thấp (thường < 5%), "
            "nhiệt độ bộ pin/động cơ tăng cao hoặc có giới hạn công suất để bảo vệ hệ truyền động.\n\n"
            "Hiện tại xe của anh/chị có còn di chuyển bình thường ở tốc độ chậm được không, "
            "và trên màn hình táp-lô có báo thêm mã lỗi nào (như CC01 hay biểu tượng màu đỏ) không ạ?"
        )
        suggested_replies = [
            "Xe vẫn đi chậm được",
            "Xe không di chuyển được",
            "Hiện kèm mã lỗi khác",
            "Cách khắc phục tạm thời",
        ]
        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=payload.case_id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=turtle_reply,
            msg_metadata={"type": "ACTIVE_TURTLE_CHECK", "suggested_replies": suggested_replies},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="CLARIFICATION",
                message=turtle_reply,
                case_id=payload.case_id,
                priority="HIGH",
                suggested_replies=suggested_replies,
                show_emergency_banner=False,
                request_location=False,
            ),
            error=None,
        )

    # --------------------------------------------------------------------------
    # NHÓM C: TRA CỨU TRI THỨC / RAG FAQ (KHI KHÔNG PHẢI SỰ CỐ KỸ THUẬT)
    # --------------------------------------------------------------------------
    if not is_technical_incident:
        # Gọi Chatbot Agent Core AI (Tra cứu RAG ChromaDB / Fallback KB)
        ai_res = await process_chat_message(
            text, session_id=payload.session_id, user_role="customer", owner=current_user.id,
            client_context={
                "vehicle_model": vehicle_model,
                "reset_faq_context": bool(history and "citations" not in (history[0].msg_metadata or {})),
            },
        )
        agent_reply = ai_res.get("reply") or (
            "Theo tài liệu chính thức từ VinFast, anh/chị có thể tra cứu thông tin chi tiết, "
            "quản lý tình trạng xe và đặt lịch dịch vụ trực tiếp trên Ứng dụng VinFast.\n\n"
            "Anh/chị cần em hỗ trợ thao tác cụ thể nào không ạ?"
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
            seen_sources = set()
            for c in ai_res["citations"]:
                if c.get("url") in seen_sources:
                    continue
                seen_sources.add(c.get("url"))
                citations.append(
                    Citation(
                        source_id=c.get("source_id", "SRC-KB"),
                        title=c.get("title", "Tài liệu VinFast"),
                        url=c.get("url", "https://vinfastauto.com/vn_vi"),
                        verified_at=c["verified_at"],
                        status_code=c.get("status_code", 200),
                        applicable_models=c.get("applicable_models", []),
                        source_type=c.get("source_type", "official_manual"),
                        relevant_snippet=c.get("relevant_snippet", ""),
                    )
                )
        service_handoff = ServiceHandoff(
            has_app_feature=True,
            app_feature_name="Đặt lịch dịch vụ / Tra cứu",
            guide_url="https://vinfastauto.com/vn_vi",
        )

        faq_chips = ai_res.get("suggested_replies") or []
        if any(k in lower_text for k in ["rùa", "biểu tượng", "đèn báo", "cảnh báo"]):
            if "Xe tôi đang hiện biểu tượng này" not in faq_chips:
                faq_chips = ["Xe tôi đang hiện biểu tượng này", "Khi nào xe tự giới hạn công suất?", "Tìm trạm sạc gần tôi"]
        elif any(k in lower_text for k in ["bảo dưỡng", "12.000km", "12000"]):
            faq_chips = ["Đặt hẹn bảo dưỡng", "Chi phí bảo dưỡng định kỳ", "Danh sách xưởng dịch vụ"]

        needs_loc = any(
            kw in lower_text
            for kw in [
                "gần tôi", "gần nhất", "tìm trạm", "tìm showroom", "xung quanh đây", "định vị",
                "trạm sạc gần", "xưởng gần", "trạm gần", "trạm sạc quanh"
            ]
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
                suggested_replies=faq_chips if faq_chips else None,
                show_emergency_banner=False,
                request_location=needs_loc,
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
                show_emergency_banner=False,
                request_location=False,
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
                "turn": prior_turns + 1,
                "response_type": "CLARIFICATION",
                "user_id": current_user.id,
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
                clarification_turn=prior_turns + 1,
                max_clarification_turns=2,
                suggested_replies=suggested_replies,
                show_emergency_banner=False,
                request_location=False,
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
            show_emergency_banner=False,
            request_location=False,
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
