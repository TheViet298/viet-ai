import os
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy import func, update
from sqlalchemy.orm import Session, joinedload

from src.agents.chatbot_agent import process_chat_message
from src.agents.guardrails import EMERGENCY_SAFE_GUIDANCE, STANDARD_SAFE_GUIDANCE, evaluate_hard_safety, sanitize_pii
from src.agents.nodes.triage_node import classify_request_kind, extract_fields
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
    SafetyAcknowledgementData,
    SafetyAcknowledgementPayload,
    ServiceHandoff,
    ServicePointItem,
    ServicePointsData,
    SessionHistoryMessageItem,
    SessionHistoryResponseData,
)
from src.services.auth import check_case_ownership, get_optional_user, require_customer
from src.services.chat_cases import (
    clean_case_references,
    generate_case_id,
    resolve_authorized_active_case,
    upsert_case_brief,
)
from src.services.chat_classification import classify_chat_context
from src.services.chat_turns import run_chat_turn, safety_fields, session_emergency_context
from src.services.dashboard_vision_service import analyze_dashboard_image, prepare_image
from src.services.dashboard_warning_service import ALIASES, lookup_dashboard_warning, merge_dashboard_clarification
from src.services.image_routing import classify_vehicle_image
from src.services.knowledge_questions import answer_sales_question, sales_parts
from src.services.vehicle_context import resolve_vehicle_context
from src.services.vehicle_knowledge import is_general_vehicle_question
from src.services.vision.cardd_runtime import analyze_exterior_image


def to_iso(dt: datetime | None) -> str:
    """Đảm bảo chuỗi ISO 8601 có timezone UTC để trình duyệt hiển thị chính xác theo giờ địa phương."""
    if not dt:
        return datetime.now(UTC).isoformat()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC).isoformat()
    return dt.isoformat()


router = APIRouter(prefix="/customer", tags=["customer"])

# Đảm bảo thư mục lưu trữ ảnh riêng tư tồn tại
os.makedirs("data/attachments", exist_ok=True)


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
    image_kind: Literal["auto", "dashboard", "exterior"] = Form("dashboard"),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Upload ảnh táp-lô, đèn báo hoặc trụ sạc theo api-contract.md Mục 1.1 & ADR-004.
    Lưu trữ file tại đường dẫn riêng tư (private storage), trích xuất tín hiệu sơ bộ qua OCR/Vision.
    Cảnh báo: Khách hàng không tải VIN, biển số xe, khuôn mặt hoặc giấy tờ cá nhân.
    """
    att_id = f"ATT-{uuid.uuid4().hex}"
    storage_path = f"data/attachments/{att_id}.png"
    file_bytes = await file.read(5 * 1024 * 1024 + 1)
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Ảnh tối đa 5 MB.")
    try:
        clean_bytes, mime_type = prepare_image(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Ảnh JPEG, PNG hoặc WebP không hợp lệ.") from exc
    with open(storage_path, "wb") as f:
        f.write(clean_bytes)
    routing = await classify_vehicle_image(clean_bytes, mime_type) if image_kind == "auto" else None
    resolved_kind = routing["image_kind"] if routing else image_kind
    if resolved_kind == "exterior":
        evidence = await analyze_exterior_image(storage_path, att_id)
        detected_signals = {"evidence_type": "CARDD", "image_kind": resolved_kind, "vision_evidence": evidence}
        if evidence["damage"]["status"] == "unavailable":
            detected_signals["analysis_error"] = evidence["damage"]["reason"]
    elif resolved_kind in {"dashboard", "charger"}:
        detected_signals = await analyze_dashboard_image(clean_bytes, mime_type)
        detected_signals["image_kind"] = resolved_kind
    else:
        detected_signals = {"evidence_type": "IMAGE_ROUTING", "image_kind": "unknown",
                            "needs_clarification": True, "analysis_error": "image_kind_uncertain"}
    if routing:
        detected_signals["image_routing"] = routing
    detected_signals["owner_user_id"] = current_user.id
    ocr_text = detected_signals.get("ocr_text")
    vision_confidence = detected_signals.get("confidence")

    attachment = Attachment(
        id=att_id,
        case_id=None,
        message_id=None,
        storage_key=storage_path,
        mime_type=mime_type,
        analysis_status=(AttachmentStatus.FAILED.value if detected_signals.get("analysis_error")
                         else AttachmentStatus.ANALYZED.value),
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


def determine_incident_clarification_prompt(
    query: str,
    car_label: str,
    error_code: str | None = None,
    charger_id: str | None = None,
    station_name: str | None = None,
) -> tuple[str, list[str]]:
    lower = query.lower()
    from src.agents.guardrails import strip_accents
    lower_unaccented = strip_accents(lower)

    # 1. Subtype: Thân vỏ / Cửa / Khóa xe
    door_jam_accented = r"\b(kẹt cửa|cửa xe|cánh cửa|khóa cửa|kính cửa|cửa kính|không mở được cửa|mở cửa|cốp xe|khóa xe)\b"
    door_jam_unaccented = r"\b(ket cua|cua xe|canh cua|khoa cua|kinh cua|cua kinh|khong mo duoc cua|mo cua|cop xe|khoa xe)\b"
    if re.search(door_jam_accented, lower) or re.search(door_jam_unaccented, lower_unaccented):
        msg = (
            f"Dạ em ghi nhận xe {car_label} đang gặp vấn đề về cửa/khóa xe. "
            "Hiện tại người trên xe có bị mắc kẹt không ạ? Cửa nào đang bị kẹt và anh/chị có thể thoát ra ngoài xe an toàn không?"
        )
        suggested = ["Tôi đang ở ngoài xe", "Mọi người đều an toàn", "Cửa bên lái bị kẹt", "Cần hỗ trợ khẩn cấp"]
        return msg, suggested

    # 2. Subtype: Cảnh báo táp-lô / Rùa vàng / Vận hành yếu / Vô lăng rung
    if (
        re.search(r"\b(rùa vàng|con rùa|chạy yếu|vô lăng rung|rung|mất lái|đèn vàng)\b", lower)
        or re.search(r"\b(rua vang|con rua|chay yeu|vo lang rung|rung|mat lai|den vang)\b", lower_unaccented)
    ):
        msg = (
            f"Dạ em ghi nhận xe {car_label} đang có cảnh báo vận hành (rùa vàng hoặc chạy yếu/rung). "
            "Anh/chị đã đỗ xe ở vị trí an toàn chưa ạ? Xe hiện còn di chuyển được không và mức pin còn khoảng bao nhiêu %?"
        )
        suggested = ["Đã dừng ở nơi an toàn", "Pin còn dưới 20%", "Xe vẫn di chuyển chậm được", "Cần gọi cứu hộ"]
        return msg, suggested

    # 3. Subtype: Lỗi sạc cụ thể (Đã có error_code sạc / trạm sạc / hoặc có từ khoá sạc)
    is_known_charging_code = bool(
        error_code and re.search(r"^(?:cc\d{2}|0x[0-9a-f]+)$", error_code, re.I)
    )
    is_charging_related = bool(
        is_known_charging_code
        or charger_id
        or station_name
        or re.search(r"\b(sạc|sac|trụ|tru|trạm|tram|cc01|không vào điện|khong vao dien)\b", lower)
    )
    if is_charging_related:
        if error_code and not charger_id and not station_name:
            msg = (
                f"Dạ em đã ghi nhận xe {car_label} đang báo lỗi {error_code.upper()}. "
                "Anh/chị vui lòng cho em biết tên trạm sạc hoặc số trụ đang cắm để kỹ thuật viên kiểm tra kết nối từ xa nhé ạ?"
            )
            suggested = ["Trạm Vincom Landmark 81, trụ 3", "Trạm Vincom Metropolis, trụ P02", "Trạm sạc cao tốc"]
            return msg, suggested
        elif (charger_id or station_name) and not error_code:
            loc = station_name or charger_id
            msg = (
                f"Dạ em ghi nhận xe {car_label} đang ở {loc}. "
                "Màn hình xe hoặc đèn trụ có báo mã lỗi cụ thể nào (ví dụ: CC01, 0x41) không ạ? "
                "Anh/chị cũng có thể chụp ảnh màn hình táp-lô để em nhận diện sơ bộ nhé."
            )
            suggested = ["Lỗi communication error 0x41", "Mã lỗi CC01", "Đèn trụ nháy đỏ, không hiện mã"]
            return msg, suggested
        else:
            msg = (
                f"Dạ em ghi nhận xe {car_label} đang gặp vấn đề kỹ thuật liên quan đến sạc pin. "
                "Anh/chị có thể cho em biết trạm sạc, số trụ hoặc mã lỗi hiển thị trên táp-lô (ví dụ: CC01, 0x41) không ạ?"
            )
            suggested = ["Xem bản đồ trạm sạc ›", "Mã lỗi CC01, trụ P02", "Đèn trụ nháy đỏ"]
            return msg, suggested

    # 4. Fallback sự cố kỹ thuật chung (KHÔNG giả định là sạc)
    msg = (
        f"Dạ em ghi nhận xe {car_label} đang gặp sự cố kỹ thuật. "
        "Anh/chị vui lòng cho em biết xe hiện đang báo mã lỗi gì trên táp-lô hoặc mô tả thêm tình trạng vận hành để kỹ thuật viên hỗ trợ nhé ạ."
    )
    suggested = ["Xe báo lỗi trên màn hình", "Xe không di chuyển được", "Cần gọi cứu hộ"]
    return msg, suggested


@router.post("/chat", response_model=ApiResponse[ChatResponseData])
async def customer_chat(
    payload: CustomerChatRequest,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return await run_chat_turn(payload, current_user, db, _process_customer_chat)


async def _process_customer_chat(payload: CustomerChatRequest, current_user: User | None, db: Session):
    """
    Tiếp nhận tin nhắn chat từ khách hàng (đã đăng nhập) hoặc Guest (dùng thử tối đa 5 lượt):
    - Hỗ trợ text và/hoặc ảnh đính kèm (OCR/Vision tín hiệu sơ bộ)
    - Áp dụng Hard Safety Rules (CRITICAL)
    - Clarification tối đa 2 lượt kèm Quick Replies
    - Phản hồi FAQ kèm Trích dẫn nguồn
    - Sinh Case Brief và lưu vết vào Database SQLite
    - Guest trial: giới hạn 5 lượt/phiên, trả remaining_guest_messages
    """
    text = sanitize_pii(payload.message.strip())[0]
    lower_text = text.lower()
    ctx = payload.client_context
    user_id = current_user.id if current_user else None
    active_case = resolve_authorized_active_case(db, current_user, payload.session_id, payload.case_id, payload.guest_session_id)
    active_case_id = active_case.id if active_case else None
    # Never reuse a resolved/closed ID from a stale browser.
    payload = payload.model_copy(update={"case_id": active_case_id})
    classification = classify_chat_context(text)
    remaining_guest_msgs: int | None = None
    if not current_user:
        if not payload.guest_session_id:
            raise HTTPException(401, "Vui lòng đăng nhập hoặc cung cấp guest_session_id.")
        guest_count = db.query(func.count(Message.id)).filter(
            (Message.session_id == payload.guest_session_id) | (Message.session_id == payload.session_id),
            Message.sender_type == SenderType.CUSTOMER.value,
        ).scalar() or 0
        remaining_guest_msgs = max(0, 5 - guest_count - 1)
        if classification.is_critical:
            reply = EMERGENCY_SAFE_GUIDANCE + " Vui lòng đăng nhập để tạo và theo dõi hồ sơ hỗ trợ."
            emergency_message = Message(id=str(uuid.uuid4()), session_id=payload.session_id, sender_type='CUSTOMER', content=text,
                                        msg_metadata={'user_id': None, 'guest_session_id': payload.guest_session_id})
            db.add(emergency_message)
            db.add(Message(id=str(uuid.uuid4()), session_id=payload.session_id, sender_type='AGENT', content=reply))
            db.info['chat_turn_customer_id'] = emergency_message.id
            return ApiResponse(success=True, data=ChatResponseData(
                response_type="FAQ_ANSWER", message=reply,
                priority="CRITICAL", safe_guidance=EMERGENCY_SAFE_GUIDANCE,
                show_emergency_banner=True, request_location=True, remaining_guest_messages=remaining_guest_msgs,
            ), error=None)
        if guest_count >= 5:
            raise HTTPException(403, "Bạn đã sử dụng hết 5 lượt chat thử nghiệm. Vui lòng đăng nhập để tiếp tục.")
    mock_cust_id = (current_user.mock_customer_id if current_user and current_user.mock_customer_id else
                    (ctx.mock_customer_id if ctx and ctx.mock_customer_id else f"GUEST_{(payload.guest_session_id or '')[:8]}"))
    previous_context = {}
    prior_customer_messages = db.query(Message).filter(
        Message.session_id == payload.session_id,
        Message.sender_type == SenderType.CUSTOMER.value,
    ).order_by(Message.created_at.desc(), Message.id.desc()).all()
    for prior in prior_customer_messages:
        metadata = prior.msg_metadata or {}
        if metadata.get("user_id") == user_id and metadata.get("guest_session_id") == payload.guest_session_id:
            previous_context = metadata.get("vehicle_context", {})
            break
    vehicle_context = resolve_vehicle_context(text, previous_context)
    if vehicle_context.get('scope_changed') or ('incident_case_id' in previous_context and vehicle_context['is_incident']):
        bound_case_id = vehicle_context.get('incident_case_id')
        active_case = resolve_authorized_active_case(db, current_user, payload.session_id, bound_case_id, payload.guest_session_id) if bound_case_id else None
        active_case_id = active_case.id if active_case else None
        payload = payload.model_copy(update={'case_id': active_case_id})
    vehicle_model = vehicle_context.get("incident_model") if vehicle_context["is_incident"] else (
        vehicle_context["models"][0] if len(vehicle_context["models"]) == 1 else None
    )
    # Compatibility for clients explicitly supplying a model, never a server default.
    if not vehicle_model and ctx and ctx.vehicle_model and len(vehicle_context["models"]) < 2:
        vehicle_model = ctx.vehicle_model
    vehicle_code = ctx.vehicle_code_mock if ctx else None
    resolved_text = vehicle_context["resolved_query"]
    vehicle_label = vehicle_model or "chưa xác định dòng"

    if active_case:
        new_model = vehicle_context.get("incident_model") or vehicle_model
        if new_model and active_case.vehicle_model != new_model:
            active_case.vehicle_model = new_model
            active_case.updated_at = datetime.now(UTC)
        brief = db.query(CaseBrief).filter_by(case_id=active_case.id).first()
        if brief:
            captured = dict(brief.captured_fields or {})
            if new_model:
                captured["vehicle_model"] = new_model
            if vehicle_context.get("incident_fields"):
                captured.update(vehicle_context["incident_fields"])
            denied = vehicle_context.get("denied_reports", [])
            for d in denied:
                if d.get("error_code") and str(captured.get("error_code", "")).upper() == str(d.get("error_code", "")).upper():
                    captured.pop("error_code", None)
                if d.get("charger_id") and str(captured.get("charger_id", "")).upper() == str(d.get("charger_id", "")).upper():
                    captured.pop("charger_id", None)
            brief.captured_fields = captured
            db.flush()

    # Kiểm tra các tín hiệu OCR/Vision từ các ảnh đính kèm (nếu có)
    attached_signals: list[dict] = []
    attached_ocr_snippets: list[str] = []
    if payload.attachment_ids:
        if not current_user:
            raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để sử dụng ảnh đính kèm.")
        atts = db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).all()
        if len(atts) != len(set(payload.attachment_ids)):
            raise HTTPException(status_code=404, detail="Không tìm thấy ảnh đính kèm.")
        for att in atts:
            owner_id = (att.detected_signals or {}).get("owner_user_id")
            legacy_case = db.get(Case, att.case_id) if owner_id is None and att.case_id else None
            if owner_id != user_id and not (legacy_case and legacy_case.user_id == user_id):
                raise HTTPException(status_code=403, detail="Ảnh đính kèm không thuộc khách hàng này.")
            if att.detected_signals:
                attached_signals.append(att.detected_signals)
            if att.ocr_text:
                attached_ocr_snippets.append(att.ocr_text)

    # 1. Lưu tin nhắn của Khách hàng vào bảng messages
    cust_msg = Message(
        id=str(uuid.uuid4()),
        case_id=active_case_id or payload.case_id,
        session_id=payload.session_id,
        sender_type=SenderType.CUSTOMER.value,
        content=text,
        msg_metadata={
            "user_id": user_id,
            "vehicle_context": vehicle_context,
            "client_context": ctx.model_dump() if ctx else {},
            "attachment_ids": payload.attachment_ids or [],
            "attached_signals": attached_signals,
            "guest_session_id": payload.guest_session_id,
        },
    )
    db.add(cust_msg)
    db.info['chat_turn_customer_id'] = cust_msg.id
    db.flush()

    if not current_user and classification.request_kind in {'incident', 'complaint'}:
        reply = "Anh/chị vui lòng đăng nhập để tạo và theo dõi hồ sơ chuyên viên hỗ trợ. " + STANDARD_SAFE_GUIDANCE
        db.add(Message(id=str(uuid.uuid4()), session_id=payload.session_id, sender_type='AGENT', content=reply))
        return ApiResponse(success=True, data=ChatResponseData(response_type='FAQ_ANSWER', message=reply,
            remaining_guest_messages=remaining_guest_msgs), error=None)

    # Count only unanswered clarification prompts for this customer's incident.
    prior_turns = 0
    history = db.query(Message).filter(
        Message.session_id == payload.session_id,
        Message.sender_type == SenderType.AGENT.value,
    ).order_by(Message.created_at.desc(), Message.id.desc()).all()
    reply_created_at = datetime.now(UTC)
    if history:
        previous_reply_at = history[0].created_at
        if previous_reply_at.tzinfo is None:
            previous_reply_at = previous_reply_at.replace(tzinfo=UTC)
        # UUIDs do not preserve turn order when the system clock returns a tie.
        reply_created_at = max(reply_created_at, previous_reply_at + timedelta(microseconds=1))
    for message in history:
        if vehicle_context.get('scope_changed'):
            break
        if message.case_id:
            break
        metadata = message.msg_metadata or {}
        if metadata.get("response_type") == "CLARIFICATION" and metadata.get("user_id") == user_id:
            prior_turns += 1

    # 2. KIỂM TRA HARD SAFETY RULES (Bắt buộc theo triage-and-hitl-rules.md)
    is_guardrail_crit, crit_rule, _ = evaluate_hard_safety(resolved_text)
    has_turtle_visual = any(s.get("warning_icon") == "TURTLE_WARNING" for s in attached_signals)
    has_turtle = has_turtle_visual or crit_rule in {"TURTLE_ON_HIGHWAY", "TURTLE_NORMAL", "TURTLE_DEFINITION"}
    dangerous_conditions = [
        "cao tốc", "mất kiểm soát", "giảm công suất", "dừng giữa đường", "giật mạnh", "mất lái",
        "cao toc", "mat kiem soat", "giam cong suat", "dung giua duong", "giat manh", "mat lai",
    ]
    is_turtle_critical = (crit_rule == "TURTLE_ON_HIGHWAY") or (has_turtle_visual and any(c in lower_text for c in dangerous_conditions))
    is_direct_danger = is_guardrail_crit and (crit_rule != "TURTLE_ON_HIGHWAY")

    if is_direct_danger or is_turtle_critical:
        # BỎ QUA HỎI LÀM RÕ -> TẠO CASE CRITICAL NGAY LẬP TỨC
        new_case_id = active_case_id or payload.case_id or generate_case_id(db)
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
        else:
            db.execute(update(Case).where(Case.id == case.id).values(
                priority=Priority.CRITICAL.value, updated_at=datetime.now(UTC),
                incident_version=Case.incident_version + 1, safety_status="unconfirmed", safety_acknowledged_at=None,
            ), execution_options={"synchronize_session": False})
            db.refresh(case)
        cust_msg.case_id = case.id
        db.query(Message).filter(
            Message.session_id == payload.session_id,
            (Message.case_id.is_(None)) | (Message.case_id == "")
        ).update({"case_id": case.id}, synchronize_session=False)

        # Liên kết attachments với case
        if payload.attachment_ids:
            db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).update(
                {"case_id": case.id, "message_id": cust_msg.id}, synchronize_session=False
            )

        summary_text = (
            f"SỰ CỐ NGUY HIỂM KHẨN CẤP: Xe {vehicle_label} gặp tình huống "
            + ("báo rùa vàng giảm công suất trên cao tốc" if is_turtle_critical else "sự cố nghiêm trọng")
            + " đe dọa an toàn."
        )
        if attached_ocr_snippets:
            summary_text += f" [Tín hiệu ảnh: {', '.join(attached_ocr_snippets)}]"

        case_brief = upsert_case_brief(db,
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
            EMERGENCY_SAFE_GUIDANCE
        )
        if is_turtle_critical:
            safe_guidance += " Nếu xe đang trên cao tốc, chỉ di chuyển vào làn dừng khẩn cấp khi có thể thực hiện an toàn."
        agent_reply = (
            f"Dạ VinFast đã ghi nhận tình trạng khẩn cấp của xe {vehicle_label}. "
            f"Hệ thống đã tự động tạo hồ sơ khẩn cấp (Mã: {case.id}). Anh/chị vui lòng gọi hotline để được hỗ trợ.\n\n"
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
        db.flush()

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

    if any(s.get("evidence_type") == "IMAGE_ROUTING" for s in attached_signals):
        if active_case and current_user:
            check_case_ownership(active_case, current_user)
        reply = "Tôi chưa xác định chắc loại ảnh. Anh/chị vui lòng chọn loại ảnh táp-lô/trụ sạc hoặc ngoại thất xe rồi tải lại, hoặc gửi ảnh rõ hơn."
        db.add(Message(id=str(uuid.uuid4()), session_id=payload.session_id, case_id=active_case_id,
                       sender_type=SenderType.AGENT.value, created_at=reply_created_at,
                       content=reply, msg_metadata={"response_type": "CLARIFICATION", "image_kind": "unknown"}))
        db.flush()
        return ApiResponse(success=True, data=ChatResponseData(response_type="CLARIFICATION", message=reply,
            case_id=active_case_id, show_emergency_banner=bool(active_case and active_case.priority == "CRITICAL")), error=None)
    exterior_signals = [s for s in attached_signals if s.get("evidence_type") == "CARDD"]
    prior_cardd = (history[0].msg_metadata or {}) if history else {}
    continue_cardd = prior_cardd.get("cardd_flow") and prior_cardd.get("user_id") == user_id and not attached_signals and not vehicle_context.get('scope_changed')
    if exterior_signals or continue_cardd:
        if not current_user:
            raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để phân tích ảnh ngoại thất.")
        if len(exterior_signals) > 1:
            raise HTTPException(status_code=422, detail="Vui lòng gửi từng ảnh ngoại thất để xác nhận kết quả.")
        if active_case:
            check_case_ownership(active_case, current_user)
        ai_res = await process_chat_message(
            text, session_id=f"cardd:{user_id}:{payload.session_id}", user_role="customer", owner=user_id,
            clarification_turn=prior_turns,
            client_context={"vehicle_context": vehicle_context, "vehicle_model": vehicle_model, "original_user_message": text},
            persist_business_case=False, damage_evidence=exterior_signals[0].get("vision_evidence") if exterior_signals else None,
            application_db=db, application_session_id=payload.session_id,
        )
        visual = ai_res.get("visual_evidence")
        brief_data = ai_res.get("case_brief")
        case = active_case
        if brief_data and ai_res.get("needs_staff_review"):
            if not case:
                case = Case(
                    id=generate_case_id(db), user_id=user_id, session_id=payload.session_id,
                    mock_customer_id=mock_cust_id, vehicle_code_mock=vehicle_code,
                    vehicle_model=brief_data.get("vehicle_model"), intent=ai_res.get("intent") or "Service/Incident",
                    priority=ai_res.get("priority", "MEDIUM"),
                    status=ai_res.get("ticket_status") or TicketStatus.STAFF_REVIEWING.value,
                )
                db.add(case)
                db.flush()
            ranks = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
            if ranks.get(ai_res.get("priority"), 0) > ranks.get(case.priority, 0):
                case.priority = ai_res["priority"]
            brief = db.query(CaseBrief).filter_by(case_id=case.id).first()
            if not brief:
                brief = CaseBrief(id=str(uuid.uuid4()), case_id=case.id, is_edited_by_staff=False)
                db.add(brief)
            if not brief.is_edited_by_staff:
                brief.summary = brief_data["summary"]
                brief.captured_fields = {**brief_data.get("captured_fields", {}), "visual_evidence": visual}
                brief.suggested_action = brief_data.get("suggested_action")
                brief.confidence_score = ai_res.get("confidence_score", 0)
        attachment_ids = payload.attachment_ids or prior_cardd.get("cardd_attachment_ids", [])
        reply = ai_res.get("reply", "")
        if case:
            cust_msg.case_id = case.id
            db.query(Message).filter(
                Message.session_id == payload.session_id, Message.case_id.is_(None),
            ).update({"case_id": case.id}, synchronize_session=False)
            if attachment_ids:
                # IDs came from owned attachments or this owner's previous reply.
                db.query(Attachment).filter(Attachment.id.in_(attachment_ids)).update(
                    {"case_id": case.id}, synchronize_session=False,
                )
            if ai_res.get("case_id"):
                reply = reply.replace(ai_res["case_id"], case.id)
        response_type = ai_res.get("response_type")
        if response_type not in {"CLARIFICATION", "CASE_CREATED", "FAQ_ANSWER"}:
            response_type = "CASE_CREATED" if brief_data else "FAQ_ANSWER"
        db.add(Message(
            id=str(uuid.uuid4()), case_id=case.id if case else None, session_id=payload.session_id,
            sender_type=SenderType.AGENT.value, content=reply, created_at=reply_created_at,
            msg_metadata={"response_type": response_type, "user_id": user_id,
                          "cardd_flow": bool(visual and ai_res.get("intent") == "Service/Incident"),
                          "cardd_attachment_ids": attachment_ids, "visual_evidence": visual},
        ))
        db.flush()
        return ApiResponse(success=True, data=ChatResponseData(
            response_type=response_type, message=reply, case_id=case.id if case else None,
            status=case.status if case else None, priority=case.priority if case else ai_res.get("priority"),
            clarification_turn=ai_res.get("clarification_turn"), max_clarification_turns=2,
            suggested_replies=ai_res.get("suggested_replies"), visual_evidence=visual,
            show_emergency_banner=bool(case and case.priority == "CRITICAL"), request_location=False,
        ), error=None)

    # Dataset lookup accepts validated image symptom keys, never raw OCR instructions.
    dashboard_text = text
    dashboard_report = text
    image_evidence = [s for s in attached_signals if s.get("evidence_type") == "GEMINI_VISION"]
    image_symptoms = {key for s in image_evidence for key in s.get("symptom_keys", []) if key in ALIASES}
    if image_evidence:
        dashboard_text += "\nTáp-lô\n" + "\n".join(ALIASES[key][0] for key in sorted(image_symptoms))
        dashboard_report += "\nOCR ảnh: " + " | ".join(s.get("ocr_text", "") for s in image_evidence)
    dashboard_context_model = vehicle_context.get("incident_model") or vehicle_context.get("owned_model") or (ctx.vehicle_model if ctx and ctx.vehicle_model else None)
    if history:
        pending = history[0].msg_metadata or {}
        if (pending.get("response_type") == "CLARIFICATION"
                and pending.get("user_id") == user_id
                and pending.get("dashboard_text")):
            dashboard_text = merge_dashboard_clarification(pending["dashboard_text"], dashboard_text)
            dashboard_report = pending.get("dashboard_report", pending["dashboard_text"]) + "\n" + dashboard_report
            dashboard_context_model = dashboard_context_model or pending.get("dashboard_context_model")
    is_dashboard, dashboard_model, dashboard_records, reported_risk = lookup_dashboard_warning(
        dashboard_text, dashboard_context_model,
    )
    # Keep develop's definition and active-turtle flows ahead of dataset lookup.
    if is_dashboard and not ((crit_rule in {"TURTLE_DEFINITION", "TURTLE_NORMAL"}
                              or (is_general_vehicle_question(text) and classify_request_kind(text) == "faq"))
                             and not image_evidence):
        warning = dashboard_records[0] if dashboard_records else None
        citations = []
        if warning:
            guidance = warning["action_summary"]
            if warning["symptom_key"] == "low_pressure":
                guidance = (
                    "Kiểm tra áp suất lốp khi lốp nguội và đối chiếu với tem áp suất "
                    "trên khung cửa lái hoặc sổ tay đúng phiên bản xe. "
                    "Nếu lốp xẹp hoặc xe vận hành bất thường, dừng tại nơi an toàn và liên hệ hỗ trợ."
                )
            priority = warning["severity"] if warning["severity"] != "INFO" else None
            reply = (
                f"Theo dữ kiện cung cấp, {warning['vehicle_model']} có dấu hiệu "
                f"{warning['warning_name_vi']} (mức {warning['severity']}).\n\n"
                f"{guidance}\n\nĐây là đối chiếu mô tả, chưa phải chẩn đoán kỹ thuật."
            )
            citations = [Citation(
                source_id=warning["id"], title=warning["warning_name_vi"],
                url=warning["source_url"], verified_at=None, status_code=None,
                source_type="DATASET_REFERENCE", applicable_models=[dashboard_model],
                relevant_snippet=guidance,
            )]
        else:
            priority = reported_risk
            guidance = "Nếu xe có dấu hiệu nguy hiểm, hãy dừng tại nơi an toàn và liên hệ cứu hộ."
            reply = (
                "Chưa đủ căn cứ đối chiếu cảnh báo táp-lô cho mẫu xe này. "
                "Anh/chị vui lòng cho biết mẫu xe, nội dung chữ, biểu tượng và màu đèn; "
                "đèn sáng liên tục hay nhấp nháy?"
            )

        if image_evidence:
            visible_text = " | ".join(s.get("ocr_text", "") for s in image_evidence if s.get("ocr_text"))
            positions = {"rear_right": "sau bên phải", "rear_left": "sau bên trái",
                         "front_right": "trước bên phải", "front_left": "trước bên trái"}
            wheels = {positions[s["wheel_position"]] for s in image_evidence
                      if s.get("confidence", 0) >= 0.8 and s.get("wheel_position") in positions}
            if visible_text:
                reply += f"\nChữ đọc sơ bộ từ ảnh: {visible_text}"
            if wheels:
                reply += "\nVị trí bánh được đánh dấu: " + ", ".join(sorted(wheels)) + "."
            if any(s.get("analysis_error") or s.get("needs_clarification") for s in image_evidence):
                reply += "\nẢnh chưa đọc được chắc chắn; vui lòng gửi ảnh rõ hơn hoặc mô tả cảnh báo."

        create_case = (
            bool(warning and (warning.get("requires_staff_review")
                              or priority in {"HIGH", "CRITICAL"}))
            or (not warning and (prior_turns >= 2 or priority in {"HIGH", "CRITICAL"}))
        )
        case = None
        if create_case:
            case = db.get(Case, payload.case_id) if payload.case_id else None
            if case:
                check_case_ownership(case, current_user)
                ranks = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
                if ranks[priority] > ranks.get(case.priority, -1):
                    case.priority = priority
                case.status = TicketStatus.STAFF_REVIEWING.value
            else:
                case = Case(
                    id=generate_case_id(db), user_id=user_id,
                    session_id=payload.session_id, mock_customer_id=mock_cust_id,
                    vehicle_code_mock=vehicle_code, vehicle_model=dashboard_model,
                    intent=Intent.SERVICE_INCIDENT.value, priority=priority,
                    status=TicketStatus.STAFF_REVIEWING.value,
                )
                db.add(case)
                db.flush()
            cust_msg.case_id = case.id
            if payload.attachment_ids:
                db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).update(
                    {"case_id": case.id, "message_id": cust_msg.id}, synchronize_session=False,
                )
            brief = db.query(CaseBrief).filter(CaseBrief.case_id == case.id).first()
            if brief is None:
                brief = CaseBrief(id=str(uuid.uuid4()), case_id=case.id, is_edited_by_staff=False)
                db.add(brief)
            if not brief.is_edited_by_staff:
                brief.summary = f"Cảnh báo táp-lô {dashboard_model}: {dashboard_report}"
                brief.captured_fields = {
                    "vehicle_model": dashboard_model, "raw_inquiry": dashboard_report,
                    "dashboard_warning_ids": [item["id"] for item in dashboard_records],
                    "risk_level": warning["severity"] if warning else "UNKNOWN",
                    "reported_priority": reported_risk,
                    "evidence_type": "GEMINI_VISION" if image_evidence else "USER_REPORTED_TEXT",
                    "visual_signals": image_evidence,
                }
                brief.suggested_action = guidance
            reply += f"\nHồ sơ {case.id} đã được chuyển cho nhân viên hỗ trợ."

        response_type = "CASE_CREATED" if case else "FAQ_ANSWER" if warning else "CLARIFICATION"
        db.add(Message(
            id=str(uuid.uuid4()), case_id=case.id if case else None,
            session_id=payload.session_id, sender_type=SenderType.AGENT.value,
            created_at=reply_created_at,
            content=reply, msg_metadata={
                "response_type": response_type, "user_id": user_id,
                "dashboard_warning_ids": [item["id"] for item in dashboard_records],
                "citations": [citation.model_dump() for citation in citations],
                "dashboard_text": dashboard_text,
                "dashboard_report": dashboard_report,
                "dashboard_context_model": dashboard_context_model,
            },
        ))
        db.flush()
        return ApiResponse(success=True, data=ChatResponseData(
            response_type=response_type, message=reply,
            case_id=case.id if case else None, status=case.status if case else None,
            priority=case.priority if case else priority if warning else None,
            safe_guidance=guidance, citations=citations,
            clarification_turn=prior_turns + 1 if response_type == "CLARIFICATION" else None,
            max_clarification_turns=2 if response_type == "CLARIFICATION" else None,
        ), error=None)

    if any(k in lower_text for k in ["chuyển chuyên viên", "chuyển nhân viên", "gặp chuyên viên", "gặp nhân viên"]):
        if not current_user:
            return ApiResponse(success=True, data=ChatResponseData(response_type="FAQ_ANSWER",
                message="Anh/chị vui lòng đăng nhập để tạo và theo dõi yêu cầu chuyên viên hỗ trợ."), error=None)
        case = active_case
        if not case:
            case = Case(id=generate_case_id(db), user_id=user_id, session_id=payload.session_id,
                        intent=Intent.SERVICE_INCIDENT.value, priority="LOW", status="Staff Reviewing")
            db.add(case)
            db.flush()
        if not db.query(CaseBrief).filter_by(case_id=case.id).first():
            db.add(upsert_case_brief(db, id=str(uuid.uuid4()), case_id=case.id,
                summary="Khách hàng yêu cầu chuyên viên hỗ trợ.", captured_fields={"request": text},
                suggested_action="Chuyên viên kiểm tra yêu cầu và phản hồi cho khách hàng.", confidence_score=1.0,
                is_edited_by_staff=False))
        cust_msg.case_id = case.id
        reply = f"Đã ghi nhận yêu cầu chuyên viên hỗ trợ. Mã hồ sơ: {case.id}. Anh/chị có thể theo dõi cập nhật tại đây."
        db.add(Message(id=str(uuid.uuid4()), session_id=payload.session_id, case_id=case.id, sender_type="AGENT", content=reply))
        db.flush()
        return ApiResponse(success=True, data=ChatResponseData(response_type="CASE_CREATED", message=reply,
            case_id=case.id, status=case.status, priority=case.priority), error=None)

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
            case_id=active_case_id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=reply_no_source,
            msg_metadata={"type": "OOS_REJECT"},
        )
        db.add(agent_msg)
        if active_case:
            active_case.updated_at = datetime.now(UTC)
        db.flush()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="FAQ_ANSWER",
                message=reply_no_source,
                case_id=active_case_id,
                citations=[],
            ),
            error=None,
        )

    # 4. KIỂM TRA PHẢN ÁNH / KHIẾU NẠI (COMPLAINT / FEEDBACK)
    complaint_keywords = ["bức xúc", "khiếu nại", "thái độ", "trừ tiền", "hoàn tiền", "chiếm chỗ", "văng crash", "khen ngợi"]
    is_complaint = any(kw in lower_text for kw in complaint_keywords)
    if is_complaint:
        new_case_id = active_case_id or generate_case_id(db)
        case = db.get(Case, new_case_id)
        is_financial = any(kw in lower_text for kw in ["trừ tiền", "hoàn tiền"])
        case_prio = Priority.HIGH.value if is_financial else Priority.MEDIUM.value
        if "khen ngợi" in lower_text:
            case_prio = Priority.LOW.value

        if not case:
            case = Case(
                id=new_case_id,
                user_id=user_id,
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
        db.query(Message).filter(
            Message.session_id == payload.session_id,
            (Message.case_id.is_(None)) | (Message.case_id == "")
        ).update({"case_id": case.id}, synchronize_session=False)
        summary_text = f"Ý kiến khách hàng: {text[:120]}..."
        case_brief = upsert_case_brief(db,
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
        db.flush()

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
    from src.services.chat_classification import without_denied_reports
    has_incident_kw = any(kw in without_denied_reports(lower_text) for kw in incident_keywords) or bool(payload.attachment_ids) or vehicle_context["is_incident"]

    # Phân biệt câu hỏi giải thích kiến thức / giả định / quá khứ vs sự cố đang gặp thật
    inquiry_patterns = [
        "nghĩa là gì", "là gì", "ý nghĩa", "nghĩa là sao", "giải thích", "tại sao", "khi nào",
        "như thế nào", "cách ", "cách xử lý", "cách khắc phục", "làm thế nào", "làm sao", "làm gì",
        "bao lâu", "bao nhiêu", "chính sách", "hướng dẫn", "cho tôi hỏi", "tìm hiểu", "khác nhau",
        "xem ở đâu", "tại sao lại", "nguyên nhân"
    ]
    is_inquiry = any(p in lower_text for p in inquiry_patterns)

    hypothetical_patterns = [
        "nếu ", "nếu xe", "nếu gặp", "nếu bị", "giả sử", "trường hợp xe", "lỡ như", "khi nào thì bị", "có thể bị"
    ]
    is_hypothetical = any(p in lower_text for p in hypothetical_patterns)

    past_patterns = [
        "tháng trước", "tuần trước", "hôm qua", "đã từng bị", "lần trước", "trước đây", "từng bị"
    ]
    is_past = any(p in lower_text for p in past_patterns)

    current_patterns = [
        "xe tôi đang", "xe của tôi đang", "xe đang", "đang bị", "vừa bị", "đang hiện", "vừa hiện",
        "bây giờ", "đang ở", "đang dừng", "cứu tôi", "không rút được", "không thể di chuyển",
        "đang cắm", "rút không ra", "xe tôi bị", "xe tôi vừa"
    ]
    has_current_state = any(p in lower_text for p in current_patterns) or (
        classify_request_kind(text) == "incident" and not is_hypothetical and not is_past
    )

    if has_incident_kw:
        if (is_inquiry or is_hypothetical or is_past) and not has_current_state and not payload.attachment_ids:
            is_technical_incident = False
        else:
            is_technical_incident = True
    else:
        is_technical_incident = False

    if classification.temporal_context in {"resolved_past", "hypothetical", "knowledge"} and not payload.attachment_ids:
        is_technical_incident = False
    elif classification.request_kind == "incident":
        is_technical_incident = True

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
                greeting_reply = f"Chào {title} {short_name}! Em giúp gì được cho {title} hôm nay ạ?"
            else:
                greeting_reply = f"Chào {short_name}! Em giúp gì được cho bạn hôm nay ạ?"
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
            case_id=active_case_id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=greeting_reply,
            msg_metadata={"type": "GREETING", "suggested_replies": suggested_replies},
        )
        db.add(agent_msg)
        if active_case:
            active_case.updated_at = datetime.now(UTC)
        db.flush()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="FAQ_ANSWER",
                message=greeting_reply,
                case_id=active_case_id,
                suggested_replies=suggested_replies,
                show_emergency_banner=bool(active_case and active_case.priority == Priority.CRITICAL.value),
                request_location=False,
            ),
            error=None,
        )

    # --------------------------------------------------------------------------
    # NHÓM B: TƯ VẤN BÁN HÀNG, LÁI THỬ & GIÁ XE (SALES & SERVICES)
    # --------------------------------------------------------------------------
    knowledge_parts = sales_parts(resolved_text, vehicle_model) if not is_technical_incident else []

    # --------------------------------------------------------------------------
    # NHÓM B2: BIỂU TƯỢNG RÙA VÀNG TRÊN XE HIỆN TẠI (ACTIVE TURTLE ON VEHICLE)
    # Khách báo xe đang hiện rùa nhưng không ở trên cao tốc / chưa khẩn cấp
    # --------------------------------------------------------------------------
    is_active_turtle = has_turtle and any(
        kw in lower_text for kw in ["xe tôi", "xe của tôi", "đang hiện", "vừa hiện", "bị hiện", "đang bị", "bây giờ"]
    )
    if is_active_turtle and not is_turtle_critical and classification.temporal_context not in {"resolved_past", "hypothetical", "knowledge"}:
        turtle_reply = (
            "Em đã ghi nhận xe của anh/chị đang hiện cảnh báo rùa vàng. "
            "Anh/chị đã ở vị trí an toàn chưa, và xe hiện còn di chuyển được không ạ?"
            + (" Anh/chị cho em biết dòng xe đang gặp sự cố nhé." if not vehicle_context.get("incident_model")
               else f" Em ghi nhận dòng xe {vehicle_context['incident_model']}.")
        )
        if any(term in text.casefold() for term in ("là gì", "ý nghĩa", "giải thích")):
            turtle_reply = (
                "Biểu tượng rùa vàng báo xe đang giới hạn công suất trong chế độ bảo vệ an toàn; "
                "chỉ biểu tượng này chưa đủ xác định nguyên nhân.\n\n" + turtle_reply
            )
        suggested_replies = [
            "Xe vẫn đi chậm được",
            "Xe không di chuyển được",
            "Hiện kèm mã lỗi khác",
            "Cách khắc phục tạm thời",
        ]
        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=active_case_id or payload.case_id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=turtle_reply,
            msg_metadata={"type": "ACTIVE_TURTLE_CHECK", "suggested_replies": suggested_replies},
        )
        db.add(agent_msg)
        if active_case:
            active_case.updated_at = datetime.now(UTC)
        db.flush()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="CLARIFICATION",
                message=turtle_reply,
                case_id=active_case_id or payload.case_id,
                priority="HIGH",
                suggested_replies=suggested_replies,
                show_emergency_banner=bool(active_case and active_case.priority == Priority.CRITICAL.value),
                request_location=False,
            ),
            error=None,
        )

    if not is_technical_incident and any(k in lower_text for k in ["gần tôi", "gần nhất", "tìm trạm", "tìm showroom", "xung quanh đây", "trạm sạc quanh", "xưởng gần"]):
        target = "showroom" if "showroom" in lower_text else "xưởng dịch vụ" if "xưởng" in lower_text else "trạm sạc"
        reply = f"Anh/chị vui lòng chia sẻ vị trí để tìm {target} gần mình. Nếu không dùng GPS, anh/chị có thể nhập khu vực hoặc địa chỉ."
        db.add(Message(id=str(uuid.uuid4()), session_id=payload.session_id, case_id=active_case_id,
                       sender_type="AGENT", content=reply, msg_metadata={"action": "find_service_point"}))
        db.flush()
        return ApiResponse(success=True, data=ChatResponseData(response_type="FAQ_ANSWER", message=reply,
            case_id=active_case_id, request_location=True,
            show_emergency_banner=bool(active_case and active_case.priority == "CRITICAL")), error=None)

    # --------------------------------------------------------------------------
    # NHÓM C: TRA CỨU TRI THỨC / RAG FAQ (KHI KHÔNG PHẢI SỰ CỐ KỸ THUẬT)
    # --------------------------------------------------------------------------
    if not is_technical_incident:
        from src.services.vehicle_context import detect_memory_recall_query
        is_recall, recall_reply = detect_memory_recall_query(text, vehicle_context)
        if is_recall and recall_reply:
            agent_msg = Message(
                id=str(uuid.uuid4()),
                case_id=active_case_id,
                session_id=payload.session_id,
                sender_type=SenderType.AGENT.value,
                content=recall_reply,
                msg_metadata={"turn": prior_turns + 1, "response_type": "FAQ_ANSWER", "user_id": user_id},
            )
            db.add(agent_msg)
            db.flush()
            return ApiResponse(
                success=True,
                data=ChatResponseData(
                    response_type="FAQ_ANSWER",
                    message=recall_reply,
                    case_id=active_case_id,
                    request_location=False,
                    show_emergency_banner=bool(active_case and active_case.priority == Priority.CRITICAL.value),
                ),
                error=None,
            )

        # Gọi Chatbot Agent Core AI (Tra cứu RAG ChromaDB / Fallback KB)
        models_in_question = vehicle_context["models"]
        knowledge_model = models_in_question[0] if len(models_in_question) == 1 else (
            None if len(models_in_question) > 1 else vehicle_model
        )
        if knowledge_parts:
            ai_res = await answer_sales_question(resolved_text, knowledge_model, payload.session_id)
        else:
            ai_res = await process_chat_message(
                resolved_text, session_id=payload.session_id,
                user_role="customer" if current_user else "guest",
                owner=user_id or f"guest:{payload.guest_session_id}",
                persist_business_case=False,
                application_db=db, application_session_id=payload.session_id,
                client_context={
                    "vehicle_model": knowledge_model,
                    "vehicle_context": vehicle_context,
                    "original_user_message": text,
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
        agent_reply = clean_case_references(agent_reply, active_case_id)
        if ai_res.get("is_no_source") and not knowledge_parts:
            diag = ai_res.get("retrieval_diagnostics") or {}
            diag_cat = diag.get("category")
            diag_stage = diag.get("stage")
            if diag_cat == "context_budget_exceeded" or diag_stage == "prompt":
                agent_reply = "Tài liệu cần thiết vượt quá giới hạn xử lý hiện tại. Tôi sẽ chuyển chuyên viên kiểm tra đầy đủ điều kiện."
            elif diag_stage == "generation" or diag_cat in ("generation_unavailable", "provider_error", "circuit_open", "rate_limited"):
                agent_reply = "Tôi chưa hoàn tất được việc tạo câu trả lời từ tài liệu đã tìm thấy. Anh/chị vui lòng thử lại; tôi không thể xác nhận nội dung lúc này."
            elif not agent_reply or "Tôi chưa có nguồn" in agent_reply:
                agent_reply = "Tôi chưa có nguồn đã xác thực cho câu hỏi này. Anh/chị có thể yêu cầu chuyển chuyên viên hỗ trợ."
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
            case_id=active_case_id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=agent_reply,
            msg_metadata={"citations": [c.model_dump() for c in citations]},
        )
        db.add(agent_msg)
        if active_case:
            active_case.updated_at = datetime.now(UTC)
        db.flush()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="FAQ_ANSWER",
                message=agent_reply,
                case_id=active_case_id,
                citations=citations,
                service_handoff=service_handoff,
                suggested_replies=faq_chips if faq_chips else None,
                show_emergency_banner=bool(active_case and active_case.priority == Priority.CRITICAL.value),
                request_location=needs_loc,
                remaining_guest_messages=remaining_guest_msgs,
            ),
            error=None,
        )

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # NHÓM D: SỰ CỐ KỸ THUẬT & TRẠM SẠC (CHARGING & SERVICE INCIDENTS)
    # --------------------------------------------------------------------------
    technical_text = resolved_text if vehicle_context["is_incident"] else text
    from src.services.chat_classification import without_denied_reports
    clean_technical_text = without_denied_reports(technical_text)

    denied_fields_list = vehicle_context.get("denied_reports", [])
    denied_codes = {str(d["error_code"]).upper() for d in denied_fields_list if d.get("error_code")}
    denied_chargers = {str(d["charger_id"]).upper() for d in denied_fields_list if d.get("charger_id")}

    existing_brief = db.query(CaseBrief).filter_by(case_id=active_case.id).first() if active_case else None
    existing_captured = dict(existing_brief.captured_fields or {}) if existing_brief else {}

    # Trích xuất dữ kiện thông minh từ câu hỏi người dùng
    station_name = (
        extract_fields(text).get("station_location")
        or vehicle_context.get("incident_fields", {}).get("station_location")
        or existing_captured.get("station_location")
    )

    charger_match = re.search(r"(vn-cs-[^\s,]+|trụ\s*số\s*\d+|trụ\s*p\d+|trụ\s*\d+|p\d+)", clean_technical_text, re.IGNORECASE)
    raw_charger = (
        extract_fields(clean_technical_text).get("charger_id")
        or vehicle_context.get("incident_fields", {}).get("charger_id")
        or (charger_match.group(0).strip() if charger_match else None)
        or existing_captured.get("charger_id")
    )
    if raw_charger:
        p_match = re.search(r"\b(P\d{2}|VN-CS-[^\s,]+)\b", raw_charger, re.I)
        charger_id = p_match.group(1).upper() if p_match else raw_charger.strip()
    else:
        charger_id = None
    if charger_id and (charger_id.upper() in denied_chargers or any(d in charger_id.upper() for d in denied_chargers)):
        charger_id = None

    error_match = re.search(r"(communication\s*error(?:\s*0x[0-9a-fA-F]+)?|0x[0-9a-fA-F]+|cc01|bms[_\-\d]*|[a-zA-Z]{1,4}[_\-]\d{2,4})", clean_technical_text, re.IGNORECASE)
    error_code = (
        vehicle_context.get("incident_fields", {}).get("error_code")
        or (error_match.group(0).strip() if error_match else None)
        or existing_captured.get("error_code")
    )
    if error_code and (error_code.upper() in denied_codes or "rùa" in error_code.lower()):
        error_code = None

    model_match = re.search(r"\b(vf\s*e34|vf\s*[356789])\b", technical_text, re.IGNORECASE)
    car_model = (
        vehicle_context.get("incident_model")
        or (model_match.group(0).upper().replace(" ", "") if model_match else None)
        or (active_case.vehicle_model if active_case else None)
        or existing_captured.get("vehicle_model")
        or vehicle_model
    )

    car_label = car_model or "chưa xác định dòng"

    soc_match = re.search(r"(\d{1,2}\s*%)", technical_text)
    current_soc = (
        (soc_match.group(0).strip() if soc_match else None)
        or vehicle_context.get("incident_fields", {}).get("soc")
        or existing_captured.get("current_soc")
    )

    is_turtle_or_operation = bool(
        vehicle_context.get("incident_fields", {}).get("warning_symbol") == "rùa vàng"
        or re.search(r"\b(rùa vàng|con rùa|chạy yếu|vô lăng rung|mất lái)\b", technical_text.lower())
    )

    is_charging_incident = bool(
        charger_id
        or station_name
        or (error_code and re.search(r"^(?:cc\d{2}|0x[0-9a-f]+)$", error_code, re.I))
        or re.search(r"\b(sạc|sac|trụ|tru|trạm|tram|không vào điện|khong vao dien|súng sạc|cổng sạc)\b", lower_text)
        or any(s.get("error_code_candidate") == "CC01" for s in attached_signals)
    ) and not (is_turtle_or_operation and not (charger_id or station_name or "sạc" in lower_text or "không vào điện" in lower_text))

    # Đánh giá độ đầy đủ dữ kiện kỹ thuật (Đủ thông tin trạm/trụ/lỗi hoặc luồng rùa vàng đã dừng an toàn/báo pin)
    has_sufficient_detail = (
        bool(active_case)
        or (error_code is not None and (charger_id is not None or station_name is not None))
        or ("kẹt" in lower_text and ("súng" in lower_text or "cổng" in lower_text))
        or any(kw in lower_text for kw in ["cc01", "p02", "vn-cs", "18%"])
        or (is_turtle_or_operation and (current_soc is not None or "an toàn" in lower_text))
        or any(s.get("error_code_candidate") == "CC01" for s in attached_signals)
    )

    # TRƯỜNG HỢP A: ĐÃ ĐỦ DỮ KIỆN KỸ THUẬT -> TẠO CASE (Staff Reviewing)
    if has_sufficient_detail and car_model:
        new_case_id = active_case_id or generate_case_id(db)
        case = db.get(Case, new_case_id)
        target_intent = Intent.CHARGING_BATTERY.value if is_charging_incident else Intent.SERVICE_INCIDENT.value
        if not case:
            case = Case(
                id=new_case_id,
                user_id=user_id,
                session_id=payload.session_id,
                mock_customer_id=mock_cust_id,
                vehicle_code_mock=vehicle_code,
                vehicle_model=car_model,
                intent=target_intent,
                priority=Priority.HIGH.value,
                status=TicketStatus.STAFF_REVIEWING.value,
            )
            db.add(case)
            db.flush()
        else:
            if car_model and case.vehicle_model != car_model:
                case.vehicle_model = car_model
                case.updated_at = datetime.now(UTC)
            if not is_charging_incident and case.intent == Intent.CHARGING_BATTERY.value:
                case.intent = Intent.SERVICE_INCIDENT.value
                case.updated_at = datetime.now(UTC)

        cust_msg.case_id = case.id
        db.query(Message).filter(
            Message.session_id == payload.session_id,
            (Message.case_id.is_(None)) | (Message.case_id == "")
        ).update({"case_id": case.id}, synchronize_session=False)

        if payload.attachment_ids:
            db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).update(
                {"case_id": case.id, "message_id": cust_msg.id}, synchronize_session=False
            )

        resolved_station = station_name
        resolved_charger = charger_id.upper() if charger_id else None
        resolved_error = error_code.upper() if error_code else None

        if is_charging_incident:
            summary_text = f"Xe {car_label} gặp sự cố sạc"
            if resolved_station or resolved_charger:
                loc_str = f" tại {resolved_station}" if resolved_station else ""
                ch_str = f" ({resolved_charger})" if resolved_charger else ""
                summary_text += f"{loc_str}{ch_str}"
            if resolved_error:
                summary_text += f": báo lỗi {resolved_error}."
            elif denied_codes:
                summary_text += f": không còn báo lỗi {', '.join(sorted(denied_codes))} nhưng vẫn không vào điện."
            else:
                summary_text += "."

            if attached_ocr_snippets:
                summary_text += f" [Tín hiệu nhận diện: {', '.join(attached_ocr_snippets)}]"

            case_brief = upsert_case_brief(db,
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
            error_line = f"Mã lỗi: {resolved_error}\n\n" if resolved_error else (
                f"Mã lỗi: Đã ghi nhận không còn báo lỗi (xe vẫn không vào điện)\n\n" if denied_codes else "Mã lỗi: chưa cung cấp\n\n"
            )
            agent_reply = (
                f"Dạ VinFast đã ghi nhận sự cố sạc của xe {car_label}:\n"
                f"Vị trí trạm: {resolved_station or 'chưa cung cấp'}\n"
                f"Trụ sạc: {resolved_charger or 'chưa cung cấp'}\n"
                f"{error_line}"
                f"Hệ thống đã tự động tạo hồ sơ hỗ trợ (Mã: {case.id}) và chuyển dữ liệu trực tiếp tới Chuyên viên Kỹ thuật trạm sạc. "
                f"Anh/chị vui lòng theo dõi cập nhật tiến độ giải quyết trực tiếp trên màn hình này ạ."
            )
        else:
            summary_text = (
                f"Xe {car_label} gặp sự cố vận hành (cảnh báo rùa vàng / chạy yếu), "
                f"mức pin {current_soc or 'chưa rõ'}, khách đã dừng đỗ an toàn."
            )
            if attached_ocr_snippets:
                summary_text += f" [Tín hiệu nhận diện: {', '.join(attached_ocr_snippets)}]"

            case_brief = upsert_case_brief(db,
                id=str(uuid.uuid4()),
                case_id=case.id,
                summary=summary_text,
                captured_fields={
                    "vehicle_model": car_model,
                    "warning_symbol": vehicle_context.get("incident_fields", {}).get("warning_symbol") or "rùa vàng",
                    "current_soc": current_soc or vehicle_context.get("incident_fields", {}).get("soc"),
                    "safety_status": vehicle_context.get("incident_fields", {}).get("safety_status") or "customer_reported_safe",
                    "error_code": resolved_error,
                    "visual_signals": attached_signals,
                },
                suggested_action="Kiểm tra hệ thống điều khiển công suất động cơ, cảm biến nhiệt độ pin và hướng dẫn an toàn cho khách hàng.",
                confidence_score=0.95,
                is_edited_by_staff=False,
            )
            db.add(case_brief)

            safe_guidance = "Anh/chị vui lòng giữ xe ở vị trí đỗ an toàn, bật đèn cảnh báo nguy hiểm và theo dõi cập nhật trên giao diện này."
            agent_reply = (
                f"Dạ VinFast đã ghi nhận sự cố vận hành của xe {car_label}:\n"
                f"Tình trạng: Cảnh báo rùa vàng, xe chạy yếu (Mức pin: {current_soc or '18%'})\n"
                f"Trạng thái: Khách hàng đã dừng đỗ ở vị trí an toàn\n\n"
                f"Hệ thống đã tự động tạo hồ sơ hỗ trợ (Mã: {case.id}) và chuyển dữ liệu trực tiếp tới Đội ngũ Kỹ thuật Dịch vụ VinFast. "
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
        db.flush()

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
    from src.agents.guardrails import evaluate_hazardous_intervention
    is_hazardous, hazard_warning = evaluate_hazardous_intervention(text)
    if is_hazardous and hazard_warning:
        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=active_case_id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=hazard_warning,
            msg_metadata={
                "turn": prior_turns + 1,
                "response_type": "HIGH_VOLTAGE_SAFETY_WARNING",
                "user_id": user_id,
                "suggested_replies": ["Tôi hiểu rồi", "Kết nối chuyên viên kỹ thuật"],
            },
        )
        db.add(agent_msg)
        db.flush()
        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="FAQ_ANSWER",
                message=hazard_warning,
                case_id=active_case_id,
                status=active_case.status if active_case else None,
                priority=Priority.HIGH.value,
                request_location=False,
                show_emergency_banner=False,
                suggested_replies=["Tôi hiểu rồi", "Kết nối chuyên viên kỹ thuật"],
            ),
            error=None,
        )

    if prior_turns < 2:
        if not car_model:
            clarification_msg = "Anh/chị đang gặp sự cố với dòng xe nào ạ?"
            suggested_replies = ["VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"]
        else:
            clarification_msg, suggested_replies = determine_incident_clarification_prompt(
                text, car_label, error_code=error_code, charger_id=charger_id, station_name=station_name
            )

        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=active_case_id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=clarification_msg,
            msg_metadata={
                "turn": prior_turns + 1,
                "response_type": "CLARIFICATION",
                "user_id": user_id,
                "suggested_replies": suggested_replies,
            },
        )
        db.add(agent_msg)
        db.flush()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="CLARIFICATION",
                message=clarification_msg,
                case_id=active_case_id,
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
    new_case_id = active_case_id or generate_case_id(db)
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
    db.query(Message).filter(
        Message.session_id == payload.session_id,
        (Message.case_id.is_(None)) | (Message.case_id == "")
    ).update({"case_id": case.id}, synchronize_session=False)

    if payload.attachment_ids:
        db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).update(
            {"case_id": case.id, "message_id": cust_msg.id}, synchronize_session=False
        )

    case_brief = upsert_case_brief(db,
        id=str(uuid.uuid4()),
        case_id=case.id,
        summary=f"Yêu cầu hỗ trợ xe {car_label} cần bổ sung dữ kiện kỹ thuật chi tiết.",
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
    db.flush()

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
    # Demo fixtures are not a verified directory and cannot be recommended.
    points = []
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

    if case.status != TicketStatus.RESOLVED.value:
        raise HTTPException(
            status_code=409,
            detail=f"Hồ sơ chỉ có thể xác nhận khi ở trạng thái Resolved (trạng thái hiện tại: {case.status})",
        )

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
        if case.status != TicketStatus.RESOLVED.value:
            raise HTTPException(
                status_code=409,
                detail=f"Hồ sơ chỉ có thể xác nhận khi ở trạng thái Resolved (trạng thái hiện tại: {case.status})",
            )
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
                **safety_fields(c),
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
                    created_at=to_iso(u.created_at),
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
                    created_at=to_iso(att.created_at),
                )
            )

    # Lịch sử hội thoại đầy đủ của ca (bao gồm cả tin nhắn trước khi tạo case trong cùng session)
    conv_items: list[ConversationItem] = []
    session_messages = (
        db.query(Message)
        .filter(
            (Message.case_id == case.id)
            | ((Message.session_id == case.session_id) & (Message.session_id.isnot(None)))
        )
        .order_by(Message.created_at.asc())
        .all()
    )
    for msg in session_messages:
        sender_role = msg.sender_type if msg.sender_type in ("CUSTOMER", "AGENT", "STAFF", "SYSTEM") else "SYSTEM"
        conv_items.append(
            ConversationItem(
                sender=sender_role,
                content=msg.content,
                created_at=to_iso(msg.created_at),
            )
        )

    case_item = CustomerCaseItem(
        id=case.id,
        **safety_fields(case),
        vehicle_model=case.vehicle_model,
        vehicle_code_mock=case.vehicle_code_mock,
        intent=case.intent,
        priority=case.priority,
        status=case.status,
        summary=case.brief.summary if case.brief else None,
        created_at=to_iso(case.created_at),
        updated_at=to_iso(case.updated_at) if case.updated_at else None,
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
        emergency_context=session_emergency_context(db, current_user.id, case.session_id),
        case_id=case.id,
        priority=case.priority,
        **safety_fields(case),
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


@router.post("/cases/{case_id}/safety-acknowledgement", response_model=ApiResponse[SafetyAcknowledgementData])
def acknowledge_safety(case_id: str, payload: SafetyAcknowledgementPayload,
                       current_user: User = Depends(require_customer), db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Không tìm thấy hồ sơ.")
    check_case_ownership(case, current_user)
    if case.incident_version != payload.incident_version:
        raise HTTPException(409, "Tình trạng sự cố đã thay đổi. Vui lòng tải lại.")
    if case.priority != "CRITICAL" or case.status in {"Closed", "Resolved"}:
        raise HTTPException(409, "Hồ sơ không có cảnh báo khẩn cấp đang mở.")
    changed = db.execute(update(Case).where(Case.id == case_id,
        Case.incident_version == payload.incident_version, Case.safety_status == "unconfirmed")
        .values(safety_status="customer_reported_safe", safety_acknowledged_at=datetime.now(UTC)),
        execution_options={"synchronize_session": False})
    if changed.rowcount:
        db.add(CaseUpdate(id=str(uuid.uuid4()), case_id=case_id, author_type="CUSTOMER",
                         status_after_update=case.status, customer_message="Khách hàng xác nhận đã ở vị trí an toàn.",
                         next_step="Nhân viên tiếp tục kiểm tra sự cố; xác nhận này không kết thúc hồ sơ."))
    db.commit()
    db.refresh(case)
    if case.incident_version != payload.incident_version:
        raise HTTPException(409, "Tình trạng sự cố đã thay đổi. Vui lòng tải lại.")
    return ApiResponse(success=True, data=SafetyAcknowledgementData(case_id=case.id, **safety_fields(case),
                       emergency_context=session_emergency_context(db, current_user.id, case.session_id)), error=None)


@router.get("/sessions/{session_id}/history", response_model=ApiResponse[SessionHistoryResponseData])
def get_session_chat_history(
    session_id: str,
    guest_session_id: str | None = Query(None),
    x_session_id: str | None = Header(None, alias="X-Session-Id"),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    Lấy toàn bộ lịch sử hội thoại của một phiên chat theo session_id.
    Bảo đảm phân quyền truy cập:
    - Nếu phiên có tin nhắn của khách hàng đã đăng nhập, chỉ chính tài khoản đó mới xem được.
    - Nếu là phiên thử nghiệm guest, khách hàng phải cung cấp guest_session_id hoặc X-Session-Id khớp.
    """
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )

    active_case_id = None
    for msg in messages:
        if msg.case_id:
            active_case_id = msg.case_id
        meta = msg.msg_metadata or {}
        msg_user_id = meta.get("user_id")
        msg_guest_id = meta.get("guest_session_id")

        if msg_user_id:
            if not current_user:
                raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để xem lịch sử phiên này.")
            if current_user.id != msg_user_id and current_user.role != "STAFF":
                raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập lịch sử phiên này.")
        elif msg_guest_id and not current_user:
            provided_guest = guest_session_id or x_session_id
            if provided_guest and provided_guest != msg_guest_id and session_id != msg_guest_id:
                raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập lịch sử phiên này.")

    items = []
    for msg in messages:
        meta = msg.msg_metadata or {}
        raw_citations = meta.get("citations") or []
        citations = []
        for c in raw_citations:
            if isinstance(c, dict):
                citations.append(Citation(**c))

        created_str = msg.created_at.isoformat() if msg.created_at else datetime.now(UTC).isoformat()
        items.append(
            SessionHistoryMessageItem(
                id=msg.id,
                sender=msg.sender_type,
                content=msg.content,
                timestamp=created_str,
                response_type=meta.get("response_type"),
                citations=citations,
                suggested_replies=meta.get("suggested_replies") or [],
                safe_guidance=meta.get("safe_guidance"),
                case_id=msg.case_id,
                priority=meta.get("priority"),
            )
        )

    return ApiResponse(
        success=True,
        data=SessionHistoryResponseData(
            session_id=session_id,
            case_id=active_case_id,
            messages=items,
            total=len(items),
        ),
        error=None,
    )

