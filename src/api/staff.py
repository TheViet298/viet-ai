import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from src.db import get_db
from src.models.db_models import (
    Case,
    CaseBrief,
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
    ConversationItem,
    StaffActionPayload,
    StaffActionResponseData,
    TicketDetailCase,
    TicketDetailData,
    TicketItem,
    TicketQueueData,
)
from src.services.auth import require_staff

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/tickets", response_model=ApiResponse[TicketQueueData])
def get_ticket_queue(
    status: str | None = Query(None, description="Lọc theo trạng thái Ticket"),
    priority: str | None = Query(None, description="Lọc theo mức ưu tiên: LOW/MEDIUM/HIGH/CRITICAL"),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách Ticket trong hàng đợi Service Agent Console theo api-contract.md Mục 3.1.
    RBAC: Chỉ nhân viên (Staff) mới có quyền truy cập.
    """
    query = db.query(Case).options(joinedload(Case.brief))

    if status and status != "ALL":
        query = query.filter(Case.status == status)

    if priority and priority != "ALL":
        query = query.filter(Case.priority == priority.upper())

    cases = query.order_by(Case.created_at.desc()).all()

    items: list[TicketItem] = []
    for c in cases:
        conf_score = c.brief.confidence_score if c.brief else 0.90
        items.append(
            TicketItem(
                id=c.id,
                mock_customer_id=c.mock_customer_id or f"CUST_{c.id}",
                vehicle_model=c.vehicle_model or "VF8",
                intent=c.intent,
                priority=c.priority,
                status=c.status,
                missing_info_flag=(c.status == TicketStatus.NEEDS_INFORMATION.value),
                created_at=c.created_at.isoformat() if c.created_at else utcnow().isoformat(),
                confidence_score=round(conf_score, 2),
            )
        )

    return ApiResponse(
        success=True,
        data=TicketQueueData(items=items, total=len(items)),
        error=None,
    )


@router.get("/tickets/{case_id}", response_model=ApiResponse[TicketDetailData])
def get_ticket_detail(
    case_id: str,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Lấy chi tiết Ticket, Case Brief, Lịch sử hội thoại và Ảnh đính kèm theo api-contract.md Mục 3.2.
    RBAC: Chỉ nhân viên (Staff) mới có quyền truy cập.
    """
    case = (
        db.query(Case)
        .options(
            joinedload(Case.brief),
            joinedload(Case.messages),
            joinedload(Case.attachments),
        )
        .filter(Case.id == case_id)
        .first()
    )

    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")

    # Brief Data
    if case.brief:
        brief_out = CaseBriefOut(
            summary=case.brief.summary,
            captured_fields=case.brief.captured_fields or {},
            suggested_action=case.brief.suggested_action,
            confidence_score=case.brief.confidence_score,
            is_edited_by_staff=case.brief.is_edited_by_staff,
        )
    else:
        brief_out = CaseBriefOut(
            summary=f"Hồ sơ sự cố xe {case.vehicle_model or 'VF8'}",
            captured_fields={"vehicle_model": case.vehicle_model or "VF8"},
            suggested_action="Kiểm tra thông tin chi tiết và điều phối kỹ thuật.",
            confidence_score=0.90,
            is_edited_by_staff=False,
        )

    # Lịch sử hội thoại
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

    # Danh sách ảnh đính kèm (private storage + OCR signals)
    attachment_items: list[AttachmentOut] = []
    if case.attachments:
        for att in case.attachments:
            attachment_items.append(
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

    return ApiResponse(
        success=True,
        data=TicketDetailData(
            case=TicketDetailCase(
                id=case.id,
                mock_customer_id=case.mock_customer_id or f"CUST_{case.id}",
                vehicle_code_mock=case.vehicle_code_mock,
                vehicle_model=case.vehicle_model or "VF8",
                intent=case.intent,
                priority=case.priority,
                status=case.status,
            ),
            case_brief=brief_out,
            conversation_history=conv_items,
            attachments=attachment_items,
        ),
        error=None,
    )


@router.post("/tickets/{case_id}/actions", response_model=ApiResponse[StaffActionResponseData])
def handle_staff_action(
    case_id: str,
    payload: StaffActionPayload,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Thực hiện hành động HITL của nhân viên theo api-contract.md Mục 3.3:
    - APPROVE: Duyệt tóm tắt và chuyển sang 'In Progress'
    - EDIT_BRIEF: Hiệu chỉnh nội dung tóm tắt sự cố
    - REROUTE: Điều chuyển tuyến xử lý
    - REQUEST_INFO: Yêu cầu khách hàng bổ sung dữ kiện (chuyển 'Needs Information')
    - RESOLVE: Hoàn tất xử lý sự cố (chuyển 'Resolved')
    - CLOSE: Đóng hồ sơ ('Closed')
    - REOPEN: Mở lại hồ sơ ('Reopened')
    Tự động ghi nhận vết thay đổi vào bảng staff_audit_logs.
    """
    case = db.query(Case).options(joinedload(Case.brief)).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")

    previous_state = {
        "status": case.status,
        "priority": case.priority,
        "intent": case.intent,
        "brief_summary": case.brief.summary if case.brief else None,
    }

    new_status = case.status

    if payload.action == StaffAction.APPROVE.value:
        new_status = TicketStatus.IN_PROGRESS.value
    elif payload.action == StaffAction.RESOLVE.value:
        new_status = TicketStatus.RESOLVED.value
    elif payload.action == StaffAction.CLOSE.value:
        new_status = TicketStatus.CLOSED.value
    elif payload.action == StaffAction.REOPEN.value:
        new_status = TicketStatus.REOPENED.value
    elif payload.action == StaffAction.REQUEST_INFO.value:
        new_status = TicketStatus.NEEDS_INFORMATION.value
    elif payload.action == StaffAction.REROUTE.value:
        new_status = TicketStatus.STAFF_REVIEWING.value
    elif payload.action == StaffAction.EDIT_BRIEF.value:
        if payload.edited_brief:
            if not case.brief:
                case.brief = CaseBrief(
                    id=str(uuid.uuid4()),
                    case_id=case.id,
                    summary=payload.edited_brief.get("summary", ""),
                    captured_fields=payload.edited_brief.get("captured_fields", {}),
                    suggested_action=payload.edited_brief.get("suggested_action"),
                    confidence_score=1.0,
                    is_edited_by_staff=True,
                )
                db.add(case.brief)
            else:
                if "summary" in payload.edited_brief:
                    case.brief.summary = payload.edited_brief["summary"]
                if "captured_fields" in payload.edited_brief and isinstance(
                    payload.edited_brief["captured_fields"], dict
                ):
                    curr = dict(case.brief.captured_fields or {})
                    curr.update(payload.edited_brief["captured_fields"])
                    case.brief.captured_fields = curr
                if "suggested_action" in payload.edited_brief:
                    case.brief.suggested_action = payload.edited_brief["suggested_action"]
                case.brief.is_edited_by_staff = True

    if payload.updated_status:
        new_status = payload.updated_status

    case.status = new_status
    case.updated_at = utcnow()

    new_state = {
        "status": case.status,
        "priority": case.priority,
        "intent": case.intent,
        "brief_summary": case.brief.summary if case.brief else None,
    }

    # Ghi nhận Audit Log
    audit_entry = StaffAuditLog(
        id=str(uuid.uuid4()),
        case_id=case.id,
        staff_id=payload.staff_id or current_user.username,
        action=payload.action,
        previous_state=previous_state,
        new_state=new_state,
        notes=payload.notes,
        created_at=utcnow(),
    )
    db.add(audit_entry)
    db.commit()

    return ApiResponse(
        success=True,
        data=StaffActionResponseData(
            success=True,
            case_id=case.id,
        ),
        error=None,
    )
