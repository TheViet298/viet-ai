import logging
import os
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy import func, update
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified

from src.agents.chatbot_agent import process_chat_message
from src.agents.guardrails import (
    EMERGENCY_SAFE_GUIDANCE,
    STANDARD_SAFE_GUIDANCE,
    VINFAST_HOTLINE,
    evaluate_hard_safety,
    sanitize_pii,
)
from src.agents.nodes.triage_node import classify_request_kind, extract_fields
from src.config import get_settings
from src.db import get_db
from src.models.db_models import (
    Attachment,
    AttachmentStatus,
    AuthorType,
    Case,
    CaseBrief,
    CaseLocation,
    CaseUpdate,
    ChatRequestRecord,
    ChatSession,
    CustomerFeedback,
    Intent,
    Message,
    Priority,
    SenderType,
    StaffAction,
    StaffAuditLog,
    TicketStatus,
    User,
    UserRole,
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
    ChatSessionListItem,
    ChatSessionListResponseData,
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
    UpdateSessionTitleRequest,
)
from src.services.auth import (
    check_case_ownership,
    get_optional_user,
    is_demo_user,
    require_customer,
    scoped_cases,
    scoped_sessions,
)
from src.services.chat_cases import (
    clean_case_references,
    generate_case_id,
    resolve_authorized_active_case,
    upsert_case_brief,
)
from src.services.chat_classification import classify_chat_context, normalized
from src.services.chat_turns import run_chat_turn, safety_fields, session_emergency_context
from src.services.conversation_context import ConversationContext, TurnUnderstanding
from src.services.conversation_progress import build_reply_constraints, derive_progress, progress_reply
from src.services.dashboard_conversation import (
    DASHBOARD_CHOICES,
    DASHBOARD_SAFE_GUIDANCE,
    EXPLANATION_CHOICE,
    INCIDENT_CHOICE,
    dashboard_question,
    explain_dashboard,
)
from src.services.dashboard_vision_service import analyze_dashboard_image, prepare_image
from src.services.dashboard_warning_service import (
    ALIASES,
    describe_dashboard_image,
    lookup_dashboard_warning,
    merge_dashboard_clarification,
)
from src.services.exterior_conversation import (
    EXTERIOR_CHOICES,
    REPAIR_CHOICE,
    describe_exterior,
    exterior_question,
    repair_advice,
)
from src.services.image_routing import classify_vehicle_image
from src.services.knowledge_questions import answer_sales_question, sales_parts
from src.services.observability import observation, trace_endpoint, update_trace_identity
from src.services.vehicle_context import resolve_vehicle_context
from src.services.vehicle_knowledge import is_general_vehicle_question
from src.services.vehicle_vision_service import recognize_vehicle_model
from src.services.vision.cardd_runtime import analyze_exterior_image

logger = logging.getLogger("customer_api")


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


def elevate_priority_one_level(current_priority: str | None) -> str:
    """Nâng ưu tiên lên 1 bậc khi khách mở lại ca (LOW -> MEDIUM -> HIGH -> CRITICAL)."""
    p = (current_priority or "LOW").upper()
    if p == Priority.LOW.value:
        return Priority.MEDIUM.value
    elif p == Priority.MEDIUM.value:
        return Priority.HIGH.value
    return Priority.CRITICAL.value


# ==============================================================================
# 1. ATTACHMENT UPLOAD API — Nguồn: api-contract.md 1.1 & ADR-004
# ==============================================================================


@router.post("/attachments", response_model=ApiResponse[AttachmentOut])
@trace_endpoint('p142.upload')
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
    update_trace_identity(session_id=None, user_id=current_user.id)
    settings = get_settings()
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
        if settings.cardd_enabled:
            evidence = await analyze_exterior_image(storage_path, att_id)
            detected_signals = {"evidence_type": "CARDD", "image_kind": resolved_kind, "vision_evidence": evidence}
            if evidence["damage"]["status"] == "unavailable":
                detected_signals["analysis_error"] = evidence["damage"]["reason"]
        else:
            vehicle_res = await recognize_vehicle_model(clean_bytes, mime_type)
            top_conf = (vehicle_res.get("candidates") or [{}])[0].get("confidence", 0.0)
            detected_signals = {
                "evidence_type": "VEHICLE_MODEL",
                "image_kind": resolved_kind,
                "vehicle_model": vehicle_res.get("model_label"),
                "vehicle_evidence": vehicle_res,
                "confidence": top_conf,
                "exterior_observation": vehicle_res.get("exterior_observation", {}),
            }
            if vehicle_res.get("status") == "unavailable":
                detected_signals["analysis_error"] = vehicle_res.get("reason")
    elif resolved_kind in {"dashboard", "charger"}:
        detected_signals = await analyze_dashboard_image(clean_bytes, mime_type)
        detected_signals["image_kind"] = resolved_kind
    else:
        detected_signals = {"evidence_type": "IMAGE_ROUTING", "image_kind": "unknown",
                            "needs_clarification": True, "analysis_error": routing.get("reason", "image_kind_uncertain") if routing else "image_kind_uncertain"}
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
    with observation('attachment.persist'):
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
    is_profile_vehicle: bool = False,
) -> tuple[str, list[str]]:
    lower = query.lower()
    from src.agents.guardrails import strip_accents
    lower_unaccented = strip_accents(lower)

    # 1. Subtype: Thân vỏ / Cửa / Khóa xe
    door_jam_accented = r"\b(kẹt cửa|cửa xe|cánh cửa|khóa cửa|kính cửa|cửa kính|không mở được cửa|mở cửa|cốp xe|khóa xe)\b"
    door_jam_unaccented = r"\b(ket cua|cua xe|canh cua|khoa cua|kinh cua|cua kinh|khong mo duoc cua|mo cua|cop xe|khoa xe)\b"
    if re.search(door_jam_accented, lower) or re.search(door_jam_unaccented, lower_unaccented):
        intro = f"Dạ em ghi nhận sự cố liên quan đến xe {car_label} của anh/chị đúng không ạ? " if is_profile_vehicle else f"Dạ em ghi nhận xe {car_label} đang gặp vấn đề về cửa/khóa xe. "
        msg = (
            intro +
            "Hiện tại người trên xe có bị mắc kẹt không ạ? Cửa nào đang bị kẹt và anh/chị có thể thoát ra ngoài xe an toàn không?"
        )
        suggested = ["Tôi đang ở ngoài xe", "Mọi người đều an toàn", "Cửa bên lái bị kẹt", "Cần hỗ trợ khẩn cấp"]
        if is_profile_vehicle:
            suggested = ["Đúng", "Xe khác"] + [s for s in suggested if s not in ["Đúng", "Xe khác"]]
        return msg, suggested

    # 2. Subtype: Cảnh báo táp-lô / Rùa vàng / Vận hành yếu / Vô lăng rung
    if (
        re.search(r"\b(rùa vàng|con rùa|chạy yếu|vô lăng rung|rung|mất lái|đèn vàng)\b", lower)
        or re.search(r"\b(rua vang|con rua|chay yeu|vo lang rung|rung|mat lai|den vang)\b", lower_unaccented)
    ):
        intro = f"Dạ em ghi nhận xe {car_label} của anh/chị đang có cảnh báo vận hành (rùa vàng hoặc chạy yếu/rung) đúng không ạ? " if is_profile_vehicle else f"Dạ em ghi nhận xe {car_label} đang có cảnh báo vận hành (rùa vàng hoặc chạy yếu/rung). "
        msg = (
            intro +
            "Anh/chị đã đỗ xe ở vị trí an toàn chưa ạ? Xe hiện còn di chuyển được không và mức pin còn khoảng bao nhiêu %?"
        )
        suggested = ["Đã dừng ở nơi an toàn", "Pin còn dưới 20%", "Xe vẫn di chuyển chậm được", "Cần gọi cứu hộ"]
        if is_profile_vehicle:
            suggested = ["Đúng", "Xe khác"] + [s for s in suggested if s not in ["Đúng", "Xe khác"]]
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
            intro = f"Dạ em đã ghi nhận xe {car_label} của anh/chị đúng không ạ? Xe đang báo lỗi {error_code.upper()}. " if is_profile_vehicle else f"Dạ em đã ghi nhận xe {car_label} đang báo lỗi {error_code.upper()}. "
            msg = (
                intro +
                "Anh/chị vui lòng cho em biết tên trạm sạc hoặc số trụ đang cắm để kỹ thuật viên kiểm tra kết nối từ xa nhé ạ?"
            )
            suggested = ["Trạm Vincom Landmark 81, trụ 3", "Trạm Vincom Metropolis, trụ P02", "Trạm sạc cao tốc"]
            if is_profile_vehicle:
                suggested = ["Đúng", "Xe khác"] + [s for s in suggested if s not in ["Đúng", "Xe khác"]]
            return msg, suggested
        elif (charger_id or station_name) and not error_code:
            loc = station_name or charger_id
            intro = f"Dạ em ghi nhận xe {car_label} của anh/chị đang ở {loc} đúng không ạ? " if is_profile_vehicle else f"Dạ em ghi nhận xe {car_label} đang ở {loc}. "
            msg = (
                intro +
                "Màn hình xe hoặc đèn trụ có báo mã lỗi cụ thể nào (ví dụ: CC01, 0x41) không ạ? "
                "Anh/chị cũng có thể chụp ảnh màn hình táp-lô để em nhận diện sơ bộ nhé."
            )
            suggested = ["Lỗi communication error 0x41", "Mã lỗi CC01", "Đèn trụ nháy đỏ, không hiện mã"]
            if is_profile_vehicle:
                suggested = ["Đúng", "Xe khác"] + [s for s in suggested if s not in ["Đúng", "Xe khác"]]
            return msg, suggested
        else:
            intro = f"Dạ em ghi nhận xe {car_label} của anh/chị đang gặp vấn đề kỹ thuật liên quan đến sạc pin đúng không ạ? " if is_profile_vehicle else f"Dạ em ghi nhận xe {car_label} đang gặp vấn đề kỹ thuật liên quan đến sạc pin. "
            msg = (
                intro +
                "Anh/chị có thể cho em biết trạm sạc, số trụ hoặc mã lỗi hiển thị trên táp-lô (ví dụ: CC01, 0x41) không ạ?"
            )
            suggested = ["Xem bản đồ trạm sạc ›", "Mã lỗi CC01, trụ P02", "Đèn trụ nháy đỏ"]
            if is_profile_vehicle:
                suggested = ["Đúng", "Xe khác"] + [s for s in suggested if s not in ["Đúng", "Xe khác"]]
            return msg, suggested

    # 4. Fallback sự cố kỹ thuật chung (KHÔNG giả định là sạc)
    intro = f"Dạ em ghi nhận sự cố liên quan đến xe {car_label} của anh/chị đúng không ạ? " if is_profile_vehicle else f"Dạ em ghi nhận xe {car_label} đang gặp sự cố kỹ thuật. "
    msg = (
        intro +
        "Anh/chị vui lòng cho em biết xe hiện đang báo mã lỗi gì trên táp-lô hoặc mô tả thêm tình trạng vận hành để kỹ thuật viên hỗ trợ nhé ạ."
    )
    suggested = ["Xe báo lỗi trên màn hình", "Xe không di chuyển được", "Cần gọi cứu hộ"]
    if is_profile_vehicle:
        suggested = ["Đúng", "Xe khác"] + [s for s in suggested if s not in ["Đúng", "Xe khác"]]
    return msg, suggested


@router.post("/chat", response_model=ApiResponse[ChatResponseData])
@trace_endpoint('p142.chat.customer')
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
    if current_user and current_user.role != UserRole.CUSTOMER.value:
        logger.warning(f"[403 FORBIDDEN] User {current_user.id} role '{current_user.role}' is not CUSTOMER")
        raise HTTPException(status_code=403, detail="Customer account required")

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
            payload = payload.model_copy(update={"guest_session_id": payload.session_id})
        guest_count = db.query(func.count(Message.id)).filter(
            (Message.session_id == payload.guest_session_id) | (Message.session_id == payload.session_id),
            Message.sender_type == SenderType.CUSTOMER.value,
        ).scalar() or 0
        remaining_guest_msgs = max(0, 5 - guest_count - 1)
        logger.info(f"[CHAT TRACE] Guest session='{payload.session_id}', guest_count={guest_count}, remaining={remaining_guest_msgs}")
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
            logger.warning(f"[403 FORBIDDEN] Guest session='{payload.session_id}' reached limit: guest_count={guest_count} >= 5")
            raise HTTPException(403, "Quý khách đã sử dụng hết 5 lượt chat thử nghiệm. Quý khách vui lòng đăng nhập để tiếp tục trải nghiệm ạ.")
    mock_cust_id = (current_user.mock_customer_id if current_user and current_user.mock_customer_id else
                    (ctx.mock_customer_id if ctx and ctx.mock_customer_id else f"GUEST_{(payload.guest_session_id or '')[:8]}"))
    user_is_demo = is_demo_user(db, current_user)
    previous_context = {}
    dashboard_image_context = {}
    exterior_image_context = {}
    prior_customer_messages = db.query(Message).filter(
        Message.session_id == payload.session_id,
        Message.sender_type == SenderType.CUSTOMER.value,
    ).order_by(Message.created_at.desc(), Message.id.desc()).all()
    for prior in prior_customer_messages:
        metadata = prior.msg_metadata or {}
        if metadata.get("user_id") == user_id and metadata.get("guest_session_id") == payload.guest_session_id:
            previous_context = metadata.get("vehicle_context", {})
            dashboard_image_context = metadata.get("dashboard_image_context", {})
            exterior_image_context = metadata.get("exterior_image_context", {})
            break
    prior_agent_messages = db.query(Message).filter(
        Message.session_id == payload.session_id,
        Message.sender_type == SenderType.AGENT.value,
    ).order_by(Message.created_at.desc(), Message.id.desc()).all()
    vehicle_context = resolve_vehicle_context(text, previous_context)
    understood = db.info.get('conversation_turn') or {}
    conversation = ConversationContext.model_validate(understood.get('context') or {})
    turn_understanding = TurnUnderstanding.model_validate(understood.get('understanding') or {
        'original_text': text, 'resolved_query': text,
    })
    if (turn_understanding.move in {'correct', 'verify_claim'} and conversation.active_goal != 'incident'
            and not classification.is_critical):
        vehicle_context['is_incident'] = False
    if conversation.subject and not vehicle_context['models'] and turn_understanding.move != 'new_incident':
        vehicle_context['models'] = [conversation.subject]
    if vehicle_context.get('scope_changed') or ('incident_case_id' in previous_context and vehicle_context['is_incident']):
        bound_case_id = vehicle_context.get('incident_case_id')
        active_case = resolve_authorized_active_case(db, current_user, payload.session_id, bound_case_id, payload.guest_session_id) if bound_case_id else None
        active_case_id = active_case.id if active_case else None
        payload = payload.model_copy(update={'case_id': active_case_id})
    explicit_model_match = re.search(r"\b(vf\s*e34|vf\s*[356789]|e34)\b", text, re.I)
    explicit_model = (
        "e34" if explicit_model_match and "e34" in explicit_model_match.group(0).lower()
        else (re.sub(r"\s+", "", explicit_model_match.group(0)).upper() if explicit_model_match else None)
    )

    clean_confirm = text.strip().lower()
    is_confirm_yes = clean_confirm in {"đúng", "dung", "đúng rồi", "chính xác", "dung roi", "chinh xac"}
    is_confirm_other = clean_confirm in {"xe khác", "xe khac", "dòng khác", "dong khac", "đổi xe", "doi xe"}
    is_short_model_answer = bool(explicit_model and len(text.strip().split()) <= 3 and previous_context.get("is_incident"))

    is_incident_flow = bool(
        vehicle_context.get("is_incident")
        or classification.request_kind in {"incident", "complaint"}
        or classification.is_critical
        or vehicle_context.get("customer_vehicle_incident")
        or (previous_context.get("is_incident") and (is_confirm_yes or is_confirm_other or is_short_model_answer))
    )
    if is_incident_flow:
        vehicle_context["is_incident"] = True

    profile_model = (
        current_user.vehicle_model if current_user and current_user.vehicle_model
        else (ctx.vehicle_model if ctx and ctx.vehicle_model else None)
    )

    # Kiểm tra xem phiên này đã từng hỏi xác nhận xe hồ sơ chưa
    profile_already_prompted = bool(
        previous_context.get("profile_vehicle_prompted")
        or any(
            (msg.msg_metadata or {}).get("profile_vehicle_prompted")
            for msg in prior_agent_messages
        )
    )

    vehicle_source: str | None = None
    is_profile_vehicle = False

    if is_incident_flow:
        # Luồng sự cố:
        # 1. Xe khách nêu tên rõ trong câu sự cố (user_stated)
        if explicit_model:
            vehicle_model = explicit_model
            vehicle_source = "user_stated"
        # 1.1 Khách xác nhận "Đúng" -> chuyển thành user_stated
        elif is_confirm_yes and (previous_context.get("vehicle_model") or profile_model):
            vehicle_model = previous_context.get("vehicle_model") or profile_model
            vehicle_source = "user_stated"
        # 1.2 Khách bấm "Xe khác" -> xóa dòng xe để hỏi lại
        elif is_confirm_other:
            vehicle_model = None
            vehicle_source = "user_stated"
        elif vehicle_context.get("incident_model"):
            vehicle_model = vehicle_context.get("incident_model")
            vehicle_source = previous_context.get("vehicle_source") or "profile"
        # 2. owned_model từ hồ sơ (profile)
        elif profile_model:
            vehicle_model = profile_model
            vehicle_source = previous_context.get("vehicle_source") or "profile"
            # Chỉ hỏi xác nhận nhẹ MỘT LẦN duy nhất khi mới bắt đầu luồng sự cố bằng xe hồ sơ
            if not profile_already_prompted:
                is_profile_vehicle = True
        # 3. Hỏi lại dòng xe nếu hồ sơ trống hoặc guest
        else:
            vehicle_model = None
            vehicle_source = "inferred"
    else:
        # Luồng tư vấn giữ nguyên: xe nêu tên thắng, câu tổng quan không ép model hồ sơ
        target_model = explicit_model or vehicle_context.get("target_model") or (
            vehicle_context["models"][0] if len(vehicle_context.get("models", [])) == 1 else None
        )
        if not target_model and ctx and ctx.vehicle_model:
            target_model = ctx.vehicle_model
        vehicle_model = target_model
        vehicle_source = "user_stated" if target_model else None

    vehicle_context["vehicle_source"] = vehicle_source
    vehicle_context["vehicle_model"] = vehicle_model
    vehicle_context["incident_model"] = vehicle_model if is_incident_flow else None
    if profile_model:
        vehicle_context["owned_model"] = profile_model
    vehicle_context["is_profile_vehicle"] = is_profile_vehicle
    if is_profile_vehicle or profile_already_prompted:
        vehicle_context["profile_vehicle_prompted"] = True

    vehicle_code = (ctx.vehicle_code_mock if ctx else None) or "VF-SF-00231"
    resolved_text = vehicle_context["resolved_query"]
    if conversation.active_goal and turn_understanding.move not in {'new_incident', 'new_question'}:
        resolved_text = turn_understanding.resolved_query
    vehicle_label = vehicle_model or "chưa xác định dòng"

    if active_case:
        new_model = vehicle_context.get("incident_model") or vehicle_model
        if new_model and active_case.vehicle_model != new_model:
            active_case.vehicle_model = new_model
            active_case.updated_at = datetime.now(UTC)
        if vehicle_source and active_case.vehicle_source != vehicle_source:
            active_case.vehicle_source = vehicle_source
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
    new_image = bool(payload.attachment_ids)
    dashboard_incident_selected = text == INCIDENT_CHOICE and bool(dashboard_image_context)
    dashboard_explanation = text == EXPLANATION_CHOICE or dashboard_question(text)
    exterior_incident_selected = text == INCIDENT_CHOICE and bool(exterior_image_context)
    exterior_advice_selected = text == REPAIR_CHOICE or exterior_question(text)
    # New sessions/images never inherit another image's context. Revalidate ownership
    # even for attachment IDs previously recorded in this customer's conversation.
    if vehicle_context.get("scope_changed"):
        dashboard_image_context = {}
        dashboard_incident_selected = False
        exterior_image_context = {}
        exterior_incident_selected = False
    if not new_image and dashboard_image_context and (dashboard_incident_selected or dashboard_explanation):
        payload = payload.model_copy(update={"attachment_ids": dashboard_image_context.get("attachment_ids", [])})
    if not new_image and exterior_image_context and (exterior_incident_selected or exterior_advice_selected):
        payload = payload.model_copy(update={"attachment_ids": exterior_image_context.get("attachment_ids", [])})
    if payload.attachment_ids:
        if not current_user:
            raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để sử dụng ảnh đính kèm.")
        atts = db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).all()
        if len(atts) != len(set(payload.attachment_ids)):
            raise HTTPException(status_code=404, detail="Không tìm thấy ảnh đính kèm.")
        for att in atts:
            owner_id = (att.detected_signals or {}).get("owner_user_id")
            legacy_case = scoped_cases(db, current_user).filter(Case.id == att.case_id).first() if owner_id is None and att.case_id else None
            if owner_id != user_id and not (legacy_case and legacy_case.user_id == user_id):
                raise HTTPException(status_code=403, detail="Ảnh đính kèm không thuộc khách hàng này.")
            if att.detected_signals:
                attached_signals.append(att.detected_signals)
            if att.ocr_text:
                attached_ocr_snippets.append(att.ocr_text)
    if new_image:
        dashboard_signals = [s for s in attached_signals if s.get("evidence_type") == "GEMINI_VISION"
                             and s.get("confidence", 0) >= .8 and not s.get("needs_clarification")
                             and (s.get("symptom_keys") or s.get("visible_warnings"))]
        dashboard_image_context = {"attachment_ids": payload.attachment_ids, "mode": "pending"} if dashboard_signals else {}
        dashboard_incident_selected = False
        exterior_signals = [s for s in attached_signals if s.get("exterior_observation", {}).get("damages")]
        exterior_image_context = {"attachment_ids": payload.attachment_ids, "mode": "pending",
                                  "case_id": active_case_id} if exterior_signals else {}
        exterior_incident_selected = False
    elif exterior_image_context and (exterior_incident_selected or exterior_advice_selected):
        bound_case_id = exterior_image_context.get("case_id")
        if bound_case_id:
            active_case = resolve_authorized_active_case(db, current_user, payload.session_id, bound_case_id,
                                                        payload.guest_session_id)
            active_case_id = active_case.id if active_case else None

    model_signals = [s for s in attached_signals if s.get("evidence_type") == "VEHICLE_MODEL" and s.get("vehicle_model")]
    if not vehicle_model and model_signals:
        vehicle_model = model_signals[0]["vehicle_model"]
        vehicle_label = vehicle_model

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
            "dashboard_image_context": dashboard_image_context,
            "exterior_image_context": exterior_image_context,
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
    if cust_msg.created_at:
        cust_at = cust_msg.created_at if cust_msg.created_at.tzinfo else cust_msg.created_at.replace(tzinfo=UTC)
        reply_created_at = max(reply_created_at, cust_at + timedelta(microseconds=1000))
    if history:
        previous_reply_at = history[0].created_at
        if previous_reply_at.tzinfo is None:
            previous_reply_at = previous_reply_at.replace(tzinfo=UTC)
        # UUIDs do not preserve turn order when the system clock returns a tie.
        reply_created_at = max(reply_created_at, previous_reply_at + timedelta(microseconds=1000))
    for message in history:
        if vehicle_context.get('scope_changed'):
            break
        if message.case_id:
            break
        metadata = message.msg_metadata or {}
        if metadata.get("response_type") == "CLARIFICATION" and metadata.get("user_id") == user_id:
            prior_turns += 1

    # Image recognition alone is not a customer report of a live incident.
    # Explicit live danger still takes the hard safety path below.
    live_danger, _, _ = evaluate_hard_safety(text)
    exterior_signals = [s for s in attached_signals if s.get("exterior_observation", {}).get("damages")]
    if exterior_image_context and exterior_signals and not live_danger and (
        new_image or exterior_incident_selected or exterior_advice_selected
    ):
        case = active_case
        citations = []
        guidance = DASHBOARD_SAFE_GUIDANCE
        if exterior_incident_selected:
            severe = any(s["exterior_observation"].get("severity") == "severe" for s in exterior_signals)
            priority = "CRITICAL" if severe else "HIGH"
            if not case:
                case = Case(id=generate_case_id(db), user_id=user_id, session_id=payload.session_id,
                            mock_customer_id=mock_cust_id, vehicle_model=vehicle_model,
                            vehicle_source=vehicle_source,
                            intent=Intent.SERVICE_INCIDENT.value, priority=priority,
                            status=TicketStatus.STAFF_REVIEWING.value,
                            is_demo=user_is_demo)
                db.add(case)
                db.flush()
            else:
                new_event = not exterior_image_context.get("incident_reported", False)
                ranks = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
                new_priority = priority if ranks[priority] > ranks.get(case.priority, 0) else case.priority
                values = {"priority": new_priority, "updated_at": datetime.now(UTC)}
                if new_event:
                    values.update(incident_version=Case.incident_version + 1,
                                  safety_status="unconfirmed", safety_acknowledged_at=None)
                db.execute(update(Case).where(Case.id == case.id).values(**values),
                           execution_options={"synchronize_session": False})
                db.refresh(case)
            cust_msg.case_id = case.id
            db.query(Attachment).filter(Attachment.id.in_(payload.attachment_ids)).update(
                {"case_id": case.id, "message_id": cust_msg.id}, synchronize_session=False)
            db.add(upsert_case_brief(db, id=str(uuid.uuid4()), case_id=case.id,
                   summary=describe_exterior(exterior_signals), captured_fields={
                       "vehicle_model": vehicle_model, "visual_signals": exterior_signals,
                       "customer_reported_incident": True,
                       "exterior_attachment_ids": payload.attachment_ids,
                   }, suggested_action="Liên hệ khách hàng, kiểm tra an toàn và điều phối hỗ trợ cứu hộ.",
                   confidence_score=.8, is_edited_by_staff=False))
            phone = re.sub(r"\D", "", VINFAST_HOTLINE)
            reply = f"**Hotline cứu hộ VinFast:** [{VINFAST_HOTLINE}](tel:{phone})"
            choices = [REPAIR_CHOICE]
            mode = "incident"
        elif not new_image:
            reply, raw_citations = await repair_advice(exterior_signals, text, payload.session_id)
            citations = [Citation(**item) for item in raw_citations]
            choices = [INCIDENT_CHOICE]
            mode = "advice"
        else:
            reply = describe_exterior(exterior_signals) + "\n\nVui lòng chọn cách em hỗ trợ bên dưới ạ."
            choices = EXTERIOR_CHOICES
            mode = "pending"
        cust_msg.msg_metadata = {**cust_msg.msg_metadata, "exterior_image_context": {
            **exterior_image_context, "mode": mode, "case_id": case.id if case else None,
            "incident_reported": exterior_incident_selected or exterior_image_context.get("incident_reported", False),
        }}
        response_type = "CASE_CREATED" if exterior_incident_selected else "FAQ_ANSWER"
        db.add(Message(id=str(uuid.uuid4()), case_id=case.id if case else None, session_id=payload.session_id,
                       sender_type=SenderType.AGENT.value, content=reply, created_at=reply_created_at,
                       msg_metadata={"response_type": response_type, "user_id": user_id,
                                     "suggested_replies": choices, "safe_guidance": guidance,
                                     "citations": [c.model_dump() for c in citations]}))
        db.flush()
        return ApiResponse(success=True, data=ChatResponseData(
            response_type=response_type, message=reply, safe_guidance=guidance, citations=citations,
            suggested_replies=choices, case_id=case.id if case else None,
            priority=case.priority if case else None, status=case.status if case else None,
            show_emergency_banner=bool(exterior_incident_selected and case and case.priority == "CRITICAL"),
            request_location=exterior_incident_selected,
        ), error=None)
    dashboard_signals = [s for s in attached_signals if s.get("evidence_type") == "GEMINI_VISION"]
    if dashboard_image_context and not dashboard_incident_selected and not live_danger and (
        new_image or dashboard_explanation
    ):
        explanation_selected = not new_image
        dashboard_image_context = {**dashboard_image_context, "mode": "explanation" if explanation_selected else "pending"}
        cust_msg.msg_metadata = {**cust_msg.msg_metadata, "dashboard_image_context": dashboard_image_context}
        reply = (explain_dashboard(dashboard_signals, text) if explanation_selected else
                 describe_dashboard_image(dashboard_signals)
                 + "\n\nĐây là các cảnh báo quan sát được, chưa xác định nguyên nhân hư hỏng."
                 + "\n\nVui lòng chọn cách em hỗ trợ bên dưới ạ.")
        positions = {"rear_right": "sau bên phải", "rear_left": "sau bên trái",
                     "front_right": "trước bên phải", "front_left": "trước bên trái"}
        wheels = {positions[s["wheel_position"]] for s in dashboard_signals
                  if s.get("confidence", 0) >= .8 and s.get("wheel_position") in positions}
        if wheels:
            reply += "\nVị trí bánh được đánh dấu: " + ", ".join(sorted(wheels)) + "."
        symptom_text = "\n".join(ALIASES[key][0] for s in dashboard_signals
                                 for key in s.get("symptom_keys", []) if key in ALIASES)
        _, model, records, _ = lookup_dashboard_warning(symptom_text, vehicle_model)
        citations = [Citation(source_id=record["id"], title=record["warning_name_vi"],
                              url=record["source_url"], source_type="DATASET_REFERENCE",
                              applicable_models=[model]) for record in records]
        choices = [INCIDENT_CHOICE] if explanation_selected else DASHBOARD_CHOICES
        db.add(Message(id=str(uuid.uuid4()), session_id=payload.session_id, case_id=active_case_id,
                       sender_type=SenderType.AGENT.value, content=reply, created_at=reply_created_at,
                       msg_metadata={"user_id": user_id, "response_type": "FAQ_ANSWER",
                                     "suggested_replies": choices, "safe_guidance": DASHBOARD_SAFE_GUIDANCE,
                                     "citations": [c.model_dump() for c in citations]}))
        db.flush()
        return ApiResponse(success=True, data=ChatResponseData(
            response_type="FAQ_ANSWER", message=reply, suggested_replies=choices,
            safe_guidance=DASHBOARD_SAFE_GUIDANCE, citations=citations, case_id=active_case_id,
        ), error=None)
    if dashboard_incident_selected:
        cust_msg.msg_metadata = {**cust_msg.msg_metadata, "dashboard_image_context": {
            **dashboard_image_context, "mode": "incident",
        }}

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
        case = scoped_cases(db, current_user).filter(Case.id == new_case_id).first()
        if not case:
            case = Case(
                id=new_case_id,
                user_id=user_id,
                session_id=payload.session_id,
                mock_customer_id=mock_cust_id,
                mock_customer_name=current_user.full_name if current_user and current_user.full_name else None,
                mock_customer_phone=current_user.phone if current_user and current_user.phone else None,
                vehicle_code_mock=vehicle_code,
                vehicle_model=vehicle_model,
                vehicle_source=vehicle_source,
                intent=Intent.SERVICE_INCIDENT.value,
                priority=Priority.CRITICAL.value,
                status=TicketStatus.STAFF_REVIEWING.value,
                is_demo=user_is_demo,
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

    if model_signals and not any(s.get("evidence_type") == "CARDD" for s in attached_signals):
        detected_model = model_signals[0].get("vehicle_model")
        if detected_model:
            reply = f'Em xin xác nhận hình ảnh anh/chị gửi là mẫu xe "VinFast {detected_model}", Anh/Chị cần em hỗ trợ thông tin gì về dòng xe này ạ'
            db.add(Message(id=str(uuid.uuid4()), session_id=payload.session_id, case_id=active_case_id,
                           sender_type=SenderType.AGENT.value, created_at=reply_created_at,
                           content=reply, msg_metadata={"response_type": "VEHICLE_MODEL_IDENTIFIED", "vehicle_model": detected_model}))
            db.flush()
            return ApiResponse(success=True, data=ChatResponseData(
                response_type="FAQ_ANSWER",
                message=reply,
                case_id=active_case_id,
                remaining_guest_messages=remaining_guest_msgs,
            ), error=None)
        elif model_signals[0].get("vehicle_evidence", {}).get("status") in {"unknown", "unavailable"}:
            reply = "Hệ thống chưa nhận diện rõ mẫu xe VinFast từ ảnh ngoại thất này. Quý khách vui lòng cung cấp thêm thông tin về dòng xe (ví dụ: VF 3, VF 7,...) hoặc chụp góc rõ hơn ạ."
            db.add(Message(id=str(uuid.uuid4()), session_id=payload.session_id, case_id=active_case_id,
                           sender_type=SenderType.AGENT.value, created_at=reply_created_at,
                           content=reply, msg_metadata={"response_type": "CLARIFICATION", "image_kind": "exterior"}))
            db.flush()
            return ApiResponse(success=True, data=ChatResponseData(
                response_type="CLARIFICATION",
                message=reply,
                case_id=active_case_id,
                remaining_guest_messages=remaining_guest_msgs,
            ), error=None)

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
                    vehicle_model=brief_data.get("vehicle_model") or vehicle_model,
                    vehicle_source=vehicle_source,
                    intent=ai_res.get("intent") or "Service/Incident",
                    priority=ai_res.get("priority", "MEDIUM"),
                    status=ai_res.get("ticket_status") or TicketStatus.STAFF_REVIEWING.value,
                    is_demo=user_is_demo,
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
            image_description = describe_dashboard_image(image_evidence)
            if image_description:
                follow_up = reply if warning else (
                    "Anh/chị vui lòng cho biết mẫu xe để em đối chiếu hướng dẫn phù hợp ạ."
                )
                reply = (
                    image_description + "\n\nĐây là các cảnh báo quan sát được, chưa xác định nguyên nhân hư hỏng.\n\n"
                    + follow_up
                )
            guidance = "Nếu xe có dấu hiệu nguy hiểm, hãy dừng tại nơi an toàn và liên hệ cứu hộ."
            visible_text = " | ".join(s.get("ocr_text", "") for s in image_evidence if s.get("ocr_text"))
            positions = {"rear_right": "sau bên phải", "rear_left": "sau bên trái",
                         "front_right": "trước bên phải", "front_left": "trước bên trái"}
            wheels = {positions[s["wheel_position"]] for s in image_evidence
                      if s.get("confidence", 0) >= 0.8 and s.get("wheel_position") in positions}
            if visible_text and not image_description:
                reply += f"\nChữ đọc sơ bộ từ ảnh: {visible_text}"
            if wheels:
                reply += "\nVị trí bánh được đánh dấu: " + ", ".join(sorted(wheels)) + "."
            if any(s.get("analysis_error") or s.get("needs_clarification") for s in image_evidence):
                reply += "\nẢnh chưa đọc được chắc chắn; vui lòng gửi ảnh rõ hơn hoặc mô tả cảnh báo."

        create_case = (
            dashboard_incident_selected or bool(warning and (warning.get("requires_staff_review")
                              or priority in {"HIGH", "CRITICAL"}))
            or (not warning and (prior_turns >= 2 or priority in {"HIGH", "CRITICAL"}))
        )
        case = None
        if create_case:
            case = scoped_cases(db, current_user).filter(Case.id == payload.case_id).first() if payload.case_id else None
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
                    vehicle_source=vehicle_source or "inferred",
                    intent=Intent.SERVICE_INCIDENT.value, priority=priority,
                    status=TicketStatus.STAFF_REVIEWING.value,
                    is_demo=user_is_demo,
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

        if dashboard_incident_selected:
            phone = re.sub(r"\D", "", VINFAST_HOTLINE)
            reply = f"**Hotline cứu hộ VinFast:** [{VINFAST_HOTLINE}](tel:{phone})"
            guidance = DASHBOARD_SAFE_GUIDANCE
            citations = []

        response_type = "CASE_CREATED" if case else "FAQ_ANSWER" if warning else "CLARIFICATION"
        db.add(Message(
            id=str(uuid.uuid4()), case_id=case.id if case else None,
            session_id=payload.session_id, sender_type=SenderType.AGENT.value,
            created_at=reply_created_at,
            content=reply, msg_metadata={
                "response_type": response_type, "user_id": user_id,
                "safe_guidance": guidance,
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
            request_location=bool(case and dashboard_incident_selected),
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
                        vehicle_model=vehicle_model, vehicle_source=vehicle_source,
                        intent=Intent.SERVICE_INCIDENT.value, priority="LOW", status="Staff Reviewing",
                        is_demo=user_is_demo)
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
        case = scoped_cases(db, current_user).filter(Case.id == new_case_id).first()
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
                mock_customer_name=current_user.full_name if current_user and current_user.full_name else None,
                mock_customer_phone=current_user.phone if current_user and current_user.phone else None,
                vehicle_code_mock=vehicle_code,
                vehicle_model=vehicle_model,
                vehicle_source=vehicle_source,
                intent=Intent.COMPLAINT_FEEDBACK.value,
                priority=case_prio,
                status=TicketStatus.STAFF_REVIEWING.value,
                is_demo=user_is_demo,
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
    elif (previous_context.get("is_incident") or is_incident_flow) and (
        is_confirm_yes or is_confirm_other or (explicit_model and len(text.strip().split()) <= 3)
    ):
        is_technical_incident = True

    if not classification.is_critical and not payload.attachment_ids:
        case_snapshot = None
        if active_case:
            brief = db.query(CaseBrief).filter_by(case_id=active_case.id).first()
            case_snapshot = {'id': active_case.id, 'status': active_case.status,
                             'facts': dict(brief.captured_fields or {}) if brief else {}}
        progress = derive_progress(conversation, {}, case_snapshot, None)
        reply_constraints = build_reply_constraints(turn_understanding, conversation, progress)
        reply = progress_reply(turn_understanding, conversation, progress, case_snapshot)
        if reply:
            db.info['conversation_route'] = 'progress'
            db.add(Message(id=str(uuid.uuid4()), session_id=payload.session_id, case_id=active_case_id,
                           sender_type=SenderType.AGENT.value, content=reply, created_at=reply_created_at,
                           msg_metadata={'user_id': user_id, 'response_type': 'FAQ_ANSWER'}))
            db.flush()
            return ApiResponse(success=True, data=ChatResponseData(
                response_type='FAQ_ANSWER', message=reply, case_id=active_case_id,
                remaining_guest_messages=remaining_guest_msgs,
            ), error=None)
        if conversation.active_goal in {'quote', 'test_drive', 'maintenance', 'warranty', 'range', 'charging', 'capacity', 'concept'}:
            is_technical_incident = False

    # --------------------------------------------------------------------------
    # NHÓM A: CHÀO HỎI & GIAO TIẾP XÃ GIAO (GREETINGS)
    # --------------------------------------------------------------------------
    intro_text = re.sub(r"\s+", " ", normalized(text)).strip()
    greeting_pattern = r"^(?:xin chao(?: ban|em|bot|tro ly)?|chao(?: ban|em|bot|tro ly)?|hello|hi(?: vinfast)?)\b[\s,.!?;:]*"
    greeting = re.match(greeting_pattern, intro_text)
    question = intro_text[greeting.end():] if greeting else intro_text
    question = question.strip(" .,!?:;")
    is_greeting = bool(greeting) and not question and not is_technical_incident
    is_capabilities = not is_technical_incident and bool(re.fullmatch(
        r"(?:(?:ban|em|bot|tro ly) )?(?:co the )?"
        r"(?:(?:ho tro|giup)(?: toi|minh|khach hang)? (?:nhung gi|gi|duoc gi)"
        r"(?: cho (?:toi|minh|khach hang))?|"
        r"lam (?:duoc )?(?:nhung )?gi|co (?:nhung )?chuc nang (?:gi|nao))", question,
    ))

    if is_greeting or is_capabilities:
        customer_name = payload.client_context.customer_name if payload.client_context else None
        short_name = customer_name.strip().split()[-1] if (customer_name and customer_name.strip()) else None

        if is_capabilities:
            greeting_reply = (
                "Chào Quý khách! Em là Trợ lý CSKH VinFast (VFServ). Em có thể hỗ trợ tìm hiểu xe VinFast, tra cứu bảo hành và bảo dưỡng, "
                "hướng dẫn về sạc và ứng dụng, tiếp nhận sự cố kỹ thuật hoặc khiếu nại, "
                "và theo dõi hồ sơ hỗ trợ. Quý khách cần em hỗ trợ nội dung nào ạ?"
            )
        elif short_name:
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
            salutation = f"{title} {short_name}" if title else short_name
            greeting_reply = f"Chào {salutation}! Em là Trợ lý CSKH VinFast (VFServ). Rất vui được hỗ trợ Quý khách hôm nay. Quý khách có thể chọn nhanh các chủ đề bên dưới hoặc nhập câu hỏi trực tiếp ạ!"
        else:
            greeting_reply = "Dạ chào Quý khách! Em là Trợ lý CSKH VinFast (VFServ). Rất vui được hỗ trợ Quý khách hôm nay. Quý khách có thể chọn nhanh các chủ đề bên dưới hoặc nhập câu hỏi trực tiếp ạ!"

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
            msg_metadata={"type": "CAPABILITIES" if is_capabilities else "GREETING", "suggested_replies": suggested_replies},
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
    if conversation.active_goal and conversation.active_goal not in {'quote', 'test_drive'} and turn_understanding.move != 'new_question':
        knowledge_parts = []

    # --------------------------------------------------------------------------
    # NHÓM B2: BIỂU TƯỢNG RÙA VÀNG TRÊN XE HIỆN TẠI (ACTIVE TURTLE ON VEHICLE)
    # Khách báo xe đang hiện rùa nhưng không ở trên cao tốc / chưa khẩn cấp
    # --------------------------------------------------------------------------
    is_active_turtle = has_turtle and any(
        kw in lower_text for kw in ["xe tôi", "xe của tôi", "đang hiện", "vừa hiện", "bị hiện", "đang bị", "bây giờ"]
    )
    if is_active_turtle and not is_turtle_critical and classification.temporal_context not in {"resolved_past", "hypothetical", "knowledge"}:
        effective_model = (
            vehicle_context.get("incident_model")
            or vehicle_model
            or (current_user.vehicle_model if current_user else None)
            or (payload.client_context.vehicle_model if payload.client_context else None)
        )
        if effective_model:
            vehicle_context["incident_model"] = effective_model
            turtle_reply = (
                f"Xe {effective_model} của anh/chị đang hiện cảnh báo rùa vàng, anh/chị đã ở nơi an toàn chưa?"
            )
        else:
            turtle_reply = (
                "Em đã ghi nhận xe của anh/chị đang hiện cảnh báo rùa vàng. "
                "Anh/chị đã ở vị trí an toàn chưa, và xe hiện còn di chuyển được không ạ? "
                "Anh/chị cho em biết dòng xe đang gặp sự cố nhé."
            )
        if any(term in text.casefold() for term in ("là gì", "ý nghĩa", "giải thích")):
            turtle_reply = (
                "Biểu tượng rùa vàng báo xe đang giới hạn công suất trong chế độ bảo vệ an toàn; "
                "chỉ biểu tượng này chưa đủ xác định nguyên nhân.\n\n" + turtle_reply
            )
        suggested_replies = [
            "Đã ở nơi an toàn",
            "Xe vẫn đi chậm được",
            "Xe không di chuyển được",
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

    if not is_technical_incident and any(k in lower_text for k in ["gần tôi", "gần nhất", "tìm trạm", "tìm showroom", "xung quanh đây", "trạm sạc quanh", "xưởng gần", "xưởng dịch vụ", "danh sách xưởng", "tìm xưởng"]):
        target = "showroom" if "showroom" in lower_text else "xưởng dịch vụ" if "xưởng" in lower_text else "trạm sạc"
        reply = f"Quý khách vui lòng chia sẻ vị trí để tìm {target} gần mình. Nếu không dùng GPS, Quý khách có thể nhập khu vực hoặc địa chỉ."
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
        has_owner_incident = any(
            k in lower_text for k in ("xe tôi", "xe của tôi", "xe mình", "bị ", "lỗi", "sạc", "bảo dưỡng", "rùa vàng")
        )
        is_general_inquiry = any(
            k in lower_text for k in ("các dòng xe", "dòng xe", "các mẫu xe", "mẫu xe", "dải sản phẩm", "toàn bộ xe", "mua xe gì", "tư vấn xe", "tư vấn mua", "xe nào hợp", "tổng quan")
        ) and not has_owner_incident

        if len(models_in_question) == 1:
            knowledge_model = models_in_question[0]
        elif len(models_in_question) > 1 or is_general_inquiry:
            knowledge_model = None
        else:
            knowledge_model = vehicle_model
        effective_user_vehicle = (
            (current_user.vehicle_model if current_user else None)
            or (payload.client_context.vehicle_model if payload.client_context else None)
        )
        if knowledge_parts:
            db.info['conversation_route'] = 'sales'
            ai_res = await answer_sales_question(resolved_text, knowledge_model, payload.session_id,
                                                conversation_context=conversation.model_dump(),
                                                turn_understanding=turn_understanding.model_dump(),
                                                llm_budget=understood.get('budget'),
                                                user_vehicle=effective_user_vehicle)
        else:
            db.info['conversation_route'] = 'knowledge'
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
                    "conversation_context": conversation.model_dump(),
                    "turn_understanding": turn_understanding.model_dump(),
                    "llm_budget": understood.get('budget'),
                    "reply_constraints": reply_constraints if not payload.attachment_ids else {},
                    "reset_faq_context": bool(history and "citations" not in (history[0].msg_metadata or {})),
                },
            )
        agent_reply = ai_res.get("reply") or (
            "Theo tài liệu chính thức từ VinFast, Quý khách có thể tra cứu thông tin chi tiết, "
            "quản lý tình trạng xe và đặt lịch dịch vụ trực tiếp trên Ứng dụng VinFast.\n\n"
            "Quý khách cần em hỗ trợ thao tác cụ thể nào không ạ?"
        )
        db.info['conversation_claims'] = ai_res.get('answer_claims', [])
        db.info['conversation_retrieval'] = ai_res.get('retrieval_diagnostics', {})
        if isinstance(agent_reply, list):
            agent_reply = "".join(
                b.get("text", "") if isinstance(b, dict) else getattr(b, "text", str(b))
                for b in agent_reply
            )
        elif not isinstance(agent_reply, str):
            agent_reply = str(agent_reply)
        agent_reply = clean_case_references(agent_reply, active_case_id)
        if (ai_res.get("is_no_source") and not knowledge_parts
                and turn_understanding.move not in {'elaborate', 'ask_status', 'ask_next_step', 'verify_claim'}):
            diag = ai_res.get("retrieval_diagnostics") or {}
            diag_cat = diag.get("category")
            diag_stage = diag.get("stage")
            if diag_cat == "context_budget_exceeded" or diag_stage == "prompt":
                agent_reply = "Tài liệu cần thiết vượt quá giới hạn xử lý hiện tại. Em sẽ chuyển chuyên viên kiểm tra đầy đủ điều kiện."
            elif (not agent_reply or "chưa hoàn tất" in agent_reply) and (diag_stage == "generation" or diag_cat in ("generation_unavailable", "provider_error", "circuit_open", "rate_limited")):
                agent_reply = "Em chưa hoàn tất được việc tạo câu trả lời từ tài liệu đã tìm thấy. Quý khách vui lòng thử lại; em chưa thể xác nhận nội dung lúc này."
            elif not agent_reply or "chưa có nguồn" in agent_reply:
                agent_reply = "Em chưa có nguồn đã xác thực cho câu hỏi này. Quý khách có thể yêu cầu chuyển chuyên viên hỗ trợ."
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
        case = scoped_cases(db, current_user).filter(Case.id == new_case_id).first()
        target_intent = Intent.CHARGING_BATTERY.value if is_charging_incident else Intent.SERVICE_INCIDENT.value
        if not case:
            case = Case(
                id=new_case_id,
                user_id=user_id,
                session_id=payload.session_id,
                mock_customer_id=mock_cust_id,
                mock_customer_name=current_user.full_name if current_user and current_user.full_name else None,
                mock_customer_phone=current_user.phone if current_user and current_user.phone else None,
                vehicle_code_mock=vehicle_code,
                vehicle_model=car_model,
                vehicle_source=vehicle_source,
                intent=target_intent,
                priority=Priority.HIGH.value,
                status=TicketStatus.STAFF_REVIEWING.value,
                is_demo=user_is_demo,
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
                "Mã lỗi: Đã ghi nhận không còn báo lỗi (xe vẫn không vào điện)\n\n" if denied_codes else "Mã lỗi: chưa cung cấp\n\n"
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
            soc_display = f"{current_soc}%" if current_soc and not str(current_soc).endswith("%") else (current_soc or "chưa rõ")
            agent_reply = (
                f"Dạ VinFast đã ghi nhận sự cố vận hành của xe {car_label}:\n\n"
                f"- **Tình trạng:** Cảnh báo rùa vàng, xe chạy yếu\n"
                f"- **Mức pin:** {soc_display}\n"
                f"- **Trạng thái:** Anh/chị đã dừng đỗ ở vị trí an toàn\n\n"
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
        elif is_confirm_yes:
            clarification_msg = (
                f"Dạ em đã ghi nhận xác nhận về xe {car_label}. "
                "Anh/chị vui lòng mô tả thêm triệu chứng hoặc mã lỗi hiển thị để em hỗ trợ nhé ạ."
            )
            suggested_replies = ["Xe báo lỗi trên màn hình", "Sạc không vào điện", "Xe có cảnh báo rùa vàng", "Cần gọi cứu hộ"]
        else:
            clarification_msg, suggested_replies = determine_incident_clarification_prompt(
                text, car_label, error_code=error_code, charger_id=charger_id, station_name=station_name,
                is_profile_vehicle=is_profile_vehicle,
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
                "profile_vehicle_prompted": is_profile_vehicle or profile_already_prompted,
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
    case = scoped_cases(db, current_user).filter(Case.id == new_case_id).first()
    if not case:
        case = Case(
            id=new_case_id,
            user_id=user_id,
            session_id=payload.session_id,
            mock_customer_id=mock_cust_id,
            mock_customer_name=current_user.full_name if current_user and current_user.full_name else None,
            mock_customer_phone=current_user.phone if current_user and current_user.phone else None,
            vehicle_code_mock=vehicle_code,
            vehicle_model=car_model,
            vehicle_source=vehicle_source,
            intent=Intent.SERVICE_INCIDENT.value,
            priority=Priority.MEDIUM.value,
            status=TicketStatus.NEEDS_INFORMATION.value,
            is_demo=user_is_demo,
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
    case = scoped_cases(db, current_user).filter(Case.id == payload.case_id).first()
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
    case = scoped_cases(db, current_user).filter(Case.id == case_id).first()
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
    case = scoped_cases(db, current_user).filter(Case.id == case_id).first()
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
            notes=f"[ACTOR: CUSTOMER] Khách hàng ({current_user.full_name or current_user.username}) xác nhận đã được hỗ trợ thỏa đáng. {payload.feedback_note or ''}".strip(),
            created_at=utcnow(),
        )
        db.add(audit)

        update = CaseUpdate(
            id=str(uuid.uuid4()),
            case_id=case.id,
            author_type=AuthorType.CUSTOMER.value,
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
        case.priority = elevate_priority_one_level(case.priority)
        case.updated_at = utcnow()

        if case.brief:
            fields = dict(case.brief.captured_fields or {})
            fields["reopen_reason"] = payload.feedback_note or "Khách hàng báo chưa được khắc phục triệt để"
            case.brief.captured_fields = fields

        audit = StaffAuditLog(
            id=str(uuid.uuid4()),
            case_id=case.id,
            staff_id=f"CUSTOMER_{current_user.id}",
            action=StaffAction.REOPEN.value,
            previous_state={"status": prev_status},
            new_state={"status": TicketStatus.REOPENED.value},
            notes=f"[ACTOR: CUSTOMER] Khách hàng báo vẫn chưa được giải quyết xong: {payload.feedback_note or ''}".strip(),
            created_at=utcnow(),
        )
        db.add(audit)

        update = CaseUpdate(
            id=str(uuid.uuid4()),
            case_id=case.id,
            author_type=AuthorType.CUSTOMER.value,
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
    case = scoped_cases(db, current_user).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")
    if current_user and current_user.role != UserRole.CUSTOMER.value:
        raise HTTPException(status_code=403, detail="Customer account required")
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
        case.priority = elevate_priority_one_level(case.priority)
        case.updated_at = utcnow()

        if case.brief:
            fields = dict(case.brief.captured_fields or {})
            fields["reopen_reason"] = payload.reason or payload.feedback_note or "Khách hàng yêu cầu kiểm tra lại"
            case.brief.captured_fields = fields

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
    db_query = scoped_cases(db, current_user).options(joinedload(Case.brief))

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
                vehicle_source=c.vehicle_source,
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
        scoped_cases(db, current_user)
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
        vehicle_source=case.vehicle_source,
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
    if current_user:
        case = scoped_cases(db, current_user).filter(Case.id == case_id).first()
    elif x_session_id:
        sess = db.query(ChatSession).filter(ChatSession.id == x_session_id).first()
        sess_demo = bool(sess.is_demo) if sess else False
        case = db.query(Case).filter(Case.id == case_id, Case.is_demo == sess_demo).first()
    else:
        case = scoped_cases(db, None).filter(Case.id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")

    if current_user and current_user.role != UserRole.CUSTOMER.value:
        raise HTTPException(status_code=403, detail="Customer account required")

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

    user_id = current_user.id if current_user else None
    data = CustomerCaseStatusData(
        emergency_context=session_emergency_context(db, user_id, case.session_id),
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
    case = scoped_cases(db, current_user).filter(Case.id == case_id).first()
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


def _handle_submit_feedback(
    target_case_id: str,
    payload: CustomerFeedbackPayload,
    current_user: User | None,
    x_session_id: str | None,
    db: Session,
) -> ApiResponse[CustomerFeedbackResponseData]:
    if not target_case_id:
        raise HTTPException(status_code=400, detail="Mã hồ sơ (case_id) không được để trống.")

    case = scoped_cases(db, current_user).filter(Case.id == target_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {target_case_id}")

    # Kiểm tra quyền sở hữu chặt chẽ: chỉ chủ sở hữu tài khoản hoặc guest session tạo ca mới có quyền đánh giá
    check_case_ownership(case, current_user, session_id=x_session_id)

    if case.status not in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value):
        raise HTTPException(
            status_code=409,
            detail=f"Hồ sơ ở trạng thái '{case.status}' chưa thể đánh giá dịch vụ. Chỉ có thể đánh giá khi ca đã được giải quyết (Resolved) hoặc đóng (Closed).",
        )

    # Ràng buộc Unique / Upsert: Nếu khách đã gửi feedback trước đó thì cập nhật
    existing = db.query(CustomerFeedback).filter(CustomerFeedback.case_id == case.id).first()
    if existing:
        # Giới hạn thời gian cho phép chỉnh sửa: tối đa 7 ngày kể từ lần gửi đầu
        if existing.created_at:
            created_ts = existing.created_at.replace(tzinfo=UTC) if existing.created_at.tzinfo is None else existing.created_at
            if (utcnow() - created_ts) > timedelta(days=7):
                raise HTTPException(
                    status_code=409,
                    detail="Đã quá thời hạn 7 ngày cho phép chỉnh sửa đánh giá dịch vụ.",
                )
        existing.rating = payload.rating
        existing.comment = payload.comment
        existing.reason_tags = payload.reason_tags
        existing.updated_at = utcnow()
        db.commit()
        feedback_id = existing.id
    else:
        now_ts = utcnow()
        feedback = CustomerFeedback(
            id=str(uuid.uuid4()),
            case_id=case.id,
            rating=payload.rating,
            comment=payload.comment,
            reason_tags=payload.reason_tags,
            created_at=now_ts,
            updated_at=now_ts,
        )
        db.add(feedback)
        db.commit()
        feedback_id = feedback.id

    return ApiResponse(
        success=True,
        data=CustomerFeedbackResponseData(
            success=True,
            feedback_id=feedback_id,
            case_id=case.id,
            rating=payload.rating,
            reason_tags=payload.reason_tags,
        ),
        error=None,
    )


@router.post("/cases/{case_id}/feedback", response_model=ApiResponse[CustomerFeedbackResponseData])
def submit_customer_feedback(
    case_id: str,
    payload: CustomerFeedbackPayload,
    current_user: User | None = Depends(get_optional_user),
    x_session_id: str | None = Header(None, alias="X-Session-Id"),
    db: Session = Depends(get_db),
):
    """
    Khách hàng gửi đánh giá và nhận xét sau khi xử lý hồ sơ theo api-contract.md Mục 2.3.
    Hỗ trợ cả người dùng đã đăng nhập hoặc khách vãng lai (qua header X-Session-Id).
    """
    return _handle_submit_feedback(case_id, payload, current_user, x_session_id, db)


@router.post("/feedback", response_model=ApiResponse[CustomerFeedbackResponseData])
def submit_customer_feedback_alias(
    payload: CustomerFeedbackPayload,
    current_user: User | None = Depends(get_optional_user),
    x_session_id: str | None = Header(None, alias="X-Session-Id"),
    db: Session = Depends(get_db),
):
    """
    Endpoint alias: Nhận đánh giá dịch vụ với case_id truyền trong body.
    Bắt buộc kiểm tra quyền sở hữu như endpoint chính.
    """
    if not payload.case_id:
        raise HTTPException(status_code=400, detail="Trường 'case_id' trong nội dung gửi là bắt buộc.")
    return _handle_submit_feedback(payload.case_id, payload, current_user, x_session_id, db)


@router.post("/cases/{case_id}/safety-acknowledgement", response_model=ApiResponse[SafetyAcknowledgementData])
def acknowledge_safety(case_id: str, payload: SafetyAcknowledgementPayload,
                       current_user: User = Depends(require_customer), db: Session = Depends(get_db)):
    case = scoped_cases(db, current_user).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Không tìm thấy hồ sơ.")
    check_case_ownership(case, current_user)
    if case.incident_version != payload.incident_version:
        raise HTTPException(409, "Tình trạng sự cố đã thay đổi. Vui lòng tải lại.")
    if case.priority not in {"CRITICAL", "HIGH"} or case.status in {"Closed", "Resolved"}:
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
@router.get("/chat/sessions/{session_id}/history", response_model=ApiResponse[SessionHistoryResponseData], deprecated=True, include_in_schema=False)
def get_session_chat_history(
    session_id: str,
    guest_session_id: str | None = Query(None),
    x_session_id: str | None = Header(None, alias="X-Session-Id"),
    x_guest_id: str | None = Header(None, alias="X-Guest-Id"),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    Lấy toàn bộ lịch sử hội thoại của một phiên chat theo session_id.
    Bảo đảm phân quyền truy cập: nếu không tìm thấy hoặc không thuộc về user/guest, trả về 404 để chống dò session.
    """
    session = scoped_sessions(db, current_user).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện.")

    if current_user:
        if session.owner != f"user:{current_user.id}" and current_user.role != "STAFF":
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện.")
    else:
        provided_guest = x_guest_id or guest_session_id or x_session_id
        is_owner = bool(provided_guest and session.owner == f"guest:{provided_guest}")
        if not is_owner:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện.")

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

        if msg_user_id:
            if not current_user:
                raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện.")
            if current_user.id != msg_user_id and current_user.role != "STAFF":
                raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện.")

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


GREETING_PREFIX_REGEX = re.compile(
    r"^(?:dạ\s+)?(?:em\s+)?(?:(?:xin\s+)?chào(?:\s+(?:bạn|em|ad|admin|trợ\s+lý|vinfast|vfserv|anh|chị|quý\s+khách|cô|chú|bác))?|"
    r"hello|hi|alo|hé\s+lô|hey)[\s,!\.:;~-]*",
    re.IGNORECASE,
)


def truncate_title(text: str, max_chars: int = 40) -> str:
    """Cắt tối đa max_chars theo ranh giới từ tiếng Việt, tránh cắt giữa chữ."""
    text = text.strip()
    if not text:
        return "Cuộc trò chuyện mới"
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space >= 15:
        truncated = truncated[:last_space]
    return truncated.rstrip() + "..."


def extract_session_title(messages: list[Message], default: str = "Cuộc trò chuyện mới") -> str:
    """
    Lấy tiêu đề tự động từ tin nhắn đầu có nội dung thực.
    Cắt bỏ phần chào đầu câu nếu câu có nội dung hỏi thực sự.
    Nếu toàn bộ là câu chào, trả về default để không đóng băng tiêu đề sớm.
    """
    for msg in messages:
        if msg.sender_type == "CUSTOMER" and msg.content:
            clean = msg.content.strip()
            first_line = clean.splitlines()[0].strip() if clean else ""
            if not first_line:
                continue
            stripped = GREETING_PREFIX_REGEX.sub("", first_line).strip()
            # Bỏ qua nếu quá ngắn (< 3 ký tự) hoặc chỉ là từ chào/thử nghiệm ("t", "test", "alo", "hi"...)
            if len(stripped) < 3 or stripped.lower() in (
                "trợ lý", "bot", "vinfast", "vfserv", "ad", "admin",
                "bạn", "em", "anh", "chị", "quý khách", "test", "alo", "cho hỏi"
            ):
                continue
            capitalized = stripped[0].upper() + stripped[1:] if len(stripped) > 1 else stripped.upper()
            return truncate_title(capitalized, 40)

    return default


@router.get("/sessions", response_model=ApiResponse[ChatSessionListResponseData])
@router.get("/chat/sessions", response_model=ApiResponse[ChatSessionListResponseData], deprecated=True, include_in_schema=False)
def list_chat_sessions(
    guest_session_id: str | None = Query(None),
    x_session_id: str | None = Header(None, alias="X-Session-Id"),
    x_guest_id: str | None = Header(None, alias="X-Guest-Id"),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Lấy danh sách các phiên trò chuyện của người dùng hiện tại hoặc guest."""
    if current_user:
        owner = f"user:{current_user.id}"
        sessions = scoped_sessions(db, current_user).filter(ChatSession.owner == owner).all()
    else:
        guest_id = x_guest_id or guest_session_id or x_session_id
        if not guest_id:
            return ApiResponse(success=True, data=ChatSessionListResponseData(sessions=[], total=0))
        sessions = scoped_sessions(db, None).filter(
            (ChatSession.owner == f"guest:{guest_id}") |
            (ChatSession.id == guest_id)
        ).all()

    session_ids = [s.id for s in sessions]
    if not session_ids:
        return ApiResponse(success=True, data=ChatSessionListResponseData(sessions=[], total=0))

    messages = (
        db.query(Message)
        .filter(Message.session_id.in_(session_ids))
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )

    messages_by_session: dict[str, list[Message]] = {sid: [] for sid in session_ids}
    for m in messages:
        if m.session_id in messages_by_session:
            messages_by_session[m.session_id].append(m)

    def has_customer_message(msgs: list[Message]) -> bool:
        return any(
            m.sender_type == "CUSTOMER" and m.content and m.content.strip()
            for m in msgs
        )

    # Dọn dẹp các session rỗng hoặc chỉ có tin nhắn tự động bot (không có tin nhắn của người dùng)
    empty_sessions = [
        s for s in sessions
        if not (s.memory_states or {}).get("title_edited")
        and not has_customer_message(messages_by_session.get(s.id, []))
    ]
    if empty_sessions:
        for es in empty_sessions:
            db.delete(es)
        try:
            db.commit()
        except Exception:
            db.rollback()
        sessions = [s for s in sessions if s not in empty_sessions]

    items = []
    has_dirty_titles = False
    for s in sessions:
        s_msgs = messages_by_session.get(s.id, [])
        mem = s.memory_states or {}
        custom_title = mem.get("title")
        title_edited = mem.get("title_edited", False)

        # Bỏ qua các session không có tin nhắn nào của người dùng (chỉ có lời chào tự động bot)
        if not title_edited and not has_customer_message(s_msgs):
            continue

        # Nếu title chưa từng được sửa tay mà bị cụt (<= 2 ký tự như "T" hoặc "Test"), coi là chưa hợp lệ
        is_invalid_persisted = (
            not title_edited
            and custom_title
            and (len(custom_title.strip()) < 3 or custom_title.strip().lower() in ("test", "t"))
        )

        if title_edited and custom_title:
            title = custom_title
        elif custom_title and custom_title != "Cuộc trò chuyện mới" and not is_invalid_persisted:
            title = custom_title
        else:
            title = extract_session_title(s_msgs)
            # Chỉ lưu title khi đã lấy được nội dung thực (không lưu nếu vẫn là "Cuộc trò chuyện mới")
            if title and title != "Cuộc trò chuyện mới":
                mem_copy = dict(mem)
                mem_copy["title"] = title
                s.memory_states = mem_copy
                flag_modified(s, "memory_states")
                has_dirty_titles = True
            elif is_invalid_persisted:
                # Dọn dẹp title bị hỏng trong memory_states
                mem_copy = dict(mem)
                mem_copy.pop("title", None)
                s.memory_states = mem_copy
                flag_modified(s, "memory_states")
                has_dirty_titles = True

        last_msg = s_msgs[-1].content if s_msgs else None
        created_at = s_msgs[0].created_at if s_msgs else utcnow()
        updated_at = s_msgs[-1].created_at if s_msgs else created_at

        items.append(
            ChatSessionListItem(
                session_id=s.id,
                title=title,
                last_message=last_msg,
                created_at=created_at.isoformat() if created_at else utcnow().isoformat(),
                updated_at=updated_at.isoformat() if updated_at else utcnow().isoformat(),
                message_count=len(s_msgs),
            )
        )

    if has_dirty_titles:
        try:
            db.commit()
        except Exception:
            db.rollback()

    items = [item for item in items if item.message_count > 0]
    items.sort(key=lambda x: x.updated_at, reverse=True)
    return ApiResponse(success=True, data=ChatSessionListResponseData(sessions=items, total=len(items)))


@router.patch("/sessions/{session_id}", response_model=ApiResponse[dict])
@router.patch("/chat/sessions/{session_id}", response_model=ApiResponse[dict], deprecated=True, include_in_schema=False)
def update_chat_session_title(
    session_id: str,
    payload: UpdateSessionTitleRequest,
    guest_session_id: str | None = Query(None),
    x_session_id: str | None = Header(None, alias="X-Session-Id"),
    x_guest_id: str | None = Header(None, alias="X-Guest-Id"),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Đổi tên phiên trò chuyện. Kiểm tra quyền sở hữu chặt chẽ, trả 404 nếu không khớp."""
    session = scoped_sessions(db, current_user).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện.")

    if current_user:
        if session.owner != f"user:{current_user.id}" and current_user.role != "STAFF":
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện.")
    else:
        provided_guest = x_guest_id or guest_session_id or x_session_id
        is_owner = (
            (provided_guest and session.owner == f"guest:{provided_guest}")
            or (session.owner == f"guest:{session_id}")
        )
        if not is_owner:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện.")

    new_title = payload.title.strip()
    if not new_title:
        raise HTTPException(status_code=400, detail="Tiêu đề cuộc trò chuyện không được để trống.")

    memories = dict(session.memory_states or {})
    memories["title"] = truncate_title(new_title, 50)
    memories["title_edited"] = True  # Đánh dấu đã đổi thủ công để auto-title không bao giờ ghi đè
    session.memory_states = memories
    flag_modified(session, "memory_states")
    db.commit()
    return ApiResponse(success=True, data={"session_id": session_id, "title": memories["title"]})


@router.delete("/sessions/{session_id}", response_model=ApiResponse[dict])
@router.delete("/chat/sessions/{session_id}", response_model=ApiResponse[dict], deprecated=True, include_in_schema=False)
def delete_chat_session(
    session_id: str,
    guest_session_id: str | None = Query(None),
    x_session_id: str | None = Header(None, alias="X-Session-Id"),
    x_guest_id: str | None = Header(None, alias="X-Guest-Id"),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Xóa một phiên trò chuyện và các tin nhắn liên quan. Trả 404 nếu không tìm thấy hoặc không thuộc sở hữu."""
    session = scoped_sessions(db, current_user).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện.")

    if current_user:
        if session.owner != f"user:{current_user.id}" and current_user.role != "STAFF":
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện.")
    else:
        provided_guest = x_guest_id or guest_session_id or x_session_id
        is_owner = (
            (provided_guest and session.owner == f"guest:{provided_guest}")
            or (session.owner == f"guest:{session_id}")
        )
        if not is_owner:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên trò chuyện.")

    db.query(Message).filter(Message.session_id == session_id).delete(synchronize_session=False)
    db.query(ChatRequestRecord).filter(ChatRequestRecord.session_id == session_id).delete(synchronize_session=False)
    db.delete(session)
    db.commit()
    return ApiResponse(success=True, data={"deleted_session_id": session_id})


@router.delete("/sessions", response_model=ApiResponse[dict])
@router.delete("/chat/sessions", response_model=ApiResponse[dict], deprecated=True, include_in_schema=False)
def delete_all_chat_sessions(
    guest_session_id: str | None = Query(None),
    x_session_id: str | None = Header(None, alias="X-Session-Id"),
    x_guest_id: str | None = Header(None, alias="X-Guest-Id"),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Xóa toàn bộ lịch sử trò chuyện của người dùng hiện tại (chỉ xóa đúng owner hiện tại)."""
    if current_user:
        owner = f"user:{current_user.id}"
        sessions = scoped_sessions(db, current_user).filter(ChatSession.owner == owner).all()
    else:
        provided_guest = x_guest_id or guest_session_id or x_session_id
        if not provided_guest:
            raise HTTPException(status_code=400, detail="Thiếu thông tin phiên guest.")
        owner = f"guest:{provided_guest}"
        sessions = scoped_sessions(db, None).filter(
            (ChatSession.owner == owner) |
            (ChatSession.id == provided_guest)
        ).all()

    deleted_count = len(sessions)
    session_ids = [s.id for s in sessions]
    if session_ids:
        db.query(Message).filter(Message.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(ChatRequestRecord).filter(ChatRequestRecord.session_id.in_(session_ids)).delete(synchronize_session=False)
        for s in sessions:
            db.delete(s)
        db.commit()

    return ApiResponse(success=True, data={"deleted_sessions_count": deleted_count})


