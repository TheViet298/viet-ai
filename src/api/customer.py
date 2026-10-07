import os
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal


def to_iso(dt: datetime | None) -> str:
    """Đảm bảo chuỗi ISO 8601 có timezone UTC để trình duyệt hiển thị chính xác theo giờ địa phương."""
    if not dt:
        return datetime.now(UTC).isoformat()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC).isoformat()
    return dt.isoformat()

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.agents.chatbot_agent import process_chat_message
from src.agents.guardrails import evaluate_hard_safety
from src.agents.nodes.triage_node import classify_request_kind
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
from src.services.dashboard_vision_service import analyze_dashboard_image, prepare_image
from src.services.dashboard_warning_service import ALIASES, lookup_dashboard_warning, merge_dashboard_clarification
from src.services.image_routing import classify_vehicle_image
from src.services.knowledge_questions import answer_sales_question, explicit_models, sales_parts
from src.services.vehicle_knowledge import is_general_vehicle_question
from src.services.vision.cardd_runtime import analyze_exterior_image

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
    if current_user and current_user.role != UserRole.CUSTOMER.value:
        raise HTTPException(status_code=403, detail="Customer account required")

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
    vehicle_model = (
        ctx.vehicle_model
        if ctx and ctx.vehicle_model
        else (current_user.vehicle_model if current_user and current_user.vehicle_model else "VF8")
    ).upper()
    vehicle_code = ctx.vehicle_code_mock if ctx else "VF-SF-00231"

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
            if owner_id != current_user.id and not (legacy_case and legacy_case.user_id == current_user.id):
                raise HTTPException(status_code=403, detail="Ảnh đính kèm không thuộc khách hàng này.")
            if att.detected_signals:
                attached_signals.append(att.detected_signals)
            if att.ocr_text:
                attached_ocr_snippets.append(att.ocr_text)

    # 0.5. Tìm active case của session nếu payload.case_id chưa truyền hoặc đã truyền
    active_case: Case | None = None
    if payload.case_id:
        active_case = db.get(Case, payload.case_id)
    if not active_case and payload.session_id:
        active_case = (
            db.query(Case)
            .filter(
                Case.session_id == payload.session_id,
                Case.status.in_([
                    TicketStatus.STAFF_REVIEWING.value,
                    TicketStatus.NEEDS_INFORMATION.value,
                    TicketStatus.IN_PROGRESS.value,
                    "New",
                ]),
            )
            .order_by(Case.created_at.desc())
            .first()
        )
    active_case_id = active_case.id if active_case else None

    # 1. Lưu tin nhắn của Khách hàng vào bảng messages
    cust_msg = Message(
        id=str(uuid.uuid4()),
        case_id=active_case_id or payload.case_id,
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
    reply_created_at = datetime.now(UTC)
    if history:
        previous_reply_at = history[0].created_at
        if previous_reply_at.tzinfo is None:
            previous_reply_at = previous_reply_at.replace(tzinfo=UTC)
        # UUIDs do not preserve turn order when the system clock returns a tie.
        reply_created_at = max(reply_created_at, previous_reply_at + timedelta(microseconds=1))
    for message in history:
        if message.case_id:
            break
        metadata = message.msg_metadata or {}
        if metadata.get("response_type") == "CLARIFICATION" and metadata.get("user_id") == current_user.id:
            prior_turns += 1

    # 2. KIỂM TRA HARD SAFETY RULES (Bắt buộc theo triage-and-hitl-rules.md)
    is_guardrail_crit, crit_rule, _ = evaluate_hard_safety(text)
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
                mock_customer_name=current_user.full_name if current_user and current_user.full_name else None,
                mock_customer_phone=current_user.phone if current_user and current_user.phone else None,
                vehicle_code_mock=vehicle_code,
                vehicle_model=vehicle_model,
                intent=Intent.SERVICE_INCIDENT.value,
                priority=Priority.CRITICAL.value,
                status=TicketStatus.STAFF_REVIEWING.value,
            )
            db.add(case)
            db.flush()
        else:
            case.priority = Priority.CRITICAL.value
            case.status = TicketStatus.STAFF_REVIEWING.value
            case.updated_at = datetime.now(UTC)

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

    if any(s.get("evidence_type") == "IMAGE_ROUTING" for s in attached_signals):
        if active_case and current_user:
            check_case_ownership(active_case, current_user)
        reply = "Tôi chưa xác định chắc loại ảnh. Anh/chị vui lòng chọn loại ảnh táp-lô/trụ sạc hoặc ngoại thất xe rồi tải lại, hoặc gửi ảnh rõ hơn."
        db.add(Message(id=str(uuid.uuid4()), session_id=payload.session_id, case_id=active_case_id,
                       sender_type=SenderType.AGENT.value, created_at=reply_created_at,
                       content=reply, msg_metadata={"response_type": "CLARIFICATION", "image_kind": "unknown"}))
        db.commit()
        return ApiResponse(success=True, data=ChatResponseData(response_type="CLARIFICATION", message=reply,
            case_id=active_case_id, show_emergency_banner=bool(active_case and active_case.priority == "CRITICAL")), error=None)
    exterior_signals = [s for s in attached_signals if s.get("evidence_type") == "CARDD"]
    prior_cardd = (history[0].msg_metadata or {}) if history else {}
    continue_cardd = prior_cardd.get("cardd_flow") and prior_cardd.get("user_id") == user_id and not attached_signals
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
            client_context={"vehicle_model": ctx.vehicle_model} if ctx and ctx.vehicle_model else {},
            damage_evidence=exterior_signals[0].get("vision_evidence") if exterior_signals else None,
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
        db.commit()
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
    dashboard_context_model = ctx.vehicle_model if ctx and "vehicle_model" in ctx.model_fields_set else None
    if history:
        pending = history[0].msg_metadata or {}
        if (pending.get("response_type") == "CLARIFICATION"
                and pending.get("user_id") == current_user.id
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
                    id=generate_case_id(db), user_id=current_user.id,
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
                "response_type": response_type, "user_id": current_user.id,
                "dashboard_warning_ids": [item["id"] for item in dashboard_records],
                "citations": [citation.model_dump() for citation in citations],
                "dashboard_text": dashboard_text,
                "dashboard_report": dashboard_report,
                "dashboard_context_model": dashboard_context_model,
            },
        ))
        db.commit()
        return ApiResponse(success=True, data=ChatResponseData(
            response_type=response_type, message=reply,
            case_id=case.id if case else None, status=case.status if case else None,
            priority=case.priority if case else priority if warning else None,
            safe_guidance=guidance, citations=citations,
            clarification_turn=prior_turns + 1 if response_type == "CLARIFICATION" else None,
            max_clarification_turns=2 if response_type == "CLARIFICATION" else None,
        ), error=None)

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
        db.commit()

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
        new_case_id = payload.case_id or generate_case_id(db)
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
                mock_customer_name=current_user.full_name if current_user and current_user.full_name else None,
                mock_customer_phone=current_user.phone if current_user and current_user.phone else None,
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
    has_incident_kw = any(kw in lower_text for kw in incident_keywords) or bool(payload.attachment_ids)

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
            case_id=active_case_id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=greeting_reply,
            msg_metadata={"type": "GREETING", "suggested_replies": suggested_replies},
        )
        db.add(agent_msg)
        if active_case:
            active_case.updated_at = datetime.now(UTC)
        db.commit()

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
    knowledge_parts = sales_parts(text, ctx.vehicle_model if ctx else None) if not is_technical_incident else []

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
            case_id=active_case_id or payload.case_id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=turtle_reply,
            msg_metadata={"type": "ACTIVE_TURTLE_CHECK", "suggested_replies": suggested_replies},
        )
        db.add(agent_msg)
        if active_case:
            active_case.updated_at = datetime.now(UTC)
        db.commit()

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

    # --------------------------------------------------------------------------
    # NHÓM C: TRA CỨU TRI THỨC / RAG FAQ (KHI KHÔNG PHẢI SỰ CỐ KỸ THUẬT)
    # --------------------------------------------------------------------------
    if not is_technical_incident:
        # Gọi Chatbot Agent Core AI (Tra cứu RAG ChromaDB / Fallback KB)
        models_in_question = explicit_models(text)
        knowledge_model = models_in_question[0] if len(models_in_question) == 1 else (
            None if len(models_in_question) > 1 else (ctx.vehicle_model if ctx else None)
        )
        if knowledge_parts:
            ai_res = await answer_sales_question(text, knowledge_model, payload.session_id)
        else:
            ai_res = await process_chat_message(
                text, session_id=payload.session_id,
                user_role="customer" if current_user else "guest",
                owner=user_id or f"guest:{payload.guest_session_id}",
                client_context={
                    "vehicle_model": knowledge_model,
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
            case_id=active_case_id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=agent_reply,
            msg_metadata={"citations": [c.model_dump() for c in citations]},
        )
        db.add(agent_msg)
        if active_case:
            active_case.updated_at = datetime.now(UTC)
        db.commit()

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
                mock_customer_name=current_user.full_name if current_user and current_user.full_name else None,
                mock_customer_phone=current_user.phone if current_user and current_user.phone else None,
                vehicle_code_mock=vehicle_code,
                vehicle_model=car_model,
                intent=Intent.CHARGING_BATTERY.value,
                priority=Priority.HIGH.value,
                status=TicketStatus.STAFF_REVIEWING.value,
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
            mock_customer_name=current_user.full_name if current_user and current_user.full_name else None,
            mock_customer_phone=current_user.phone if current_user and current_user.phone else None,
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
