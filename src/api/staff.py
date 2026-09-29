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
    utcnow,
)
from src.models.schemas import (
    ApiResponse,
    CaseBriefOut,
    ConversationItem,
    StaffActionPayload,
    StaffActionResponseData,
    TicketDetailCase,
    TicketDetailData,
    TicketItem,
    TicketQueueData,
)

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/tickets", response_model=ApiResponse[TicketQueueData])
def get_ticket_queue(
    status: str | None = Query(None, description="Lọc theo trạng thái Ticket"),
    priority: str | None = Query(None, description="Lọc theo mức ưu tiên: LOW/MEDIUM/HIGH/CRITICAL"),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách Ticket trong hàng đợi Service Agent Console theo api-contract.md Mục 3.1.
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
def get_ticket_detail(case_id: str, db: Session = Depends(get_db)):
    """
    Lấy chi tiết Ticket, Case Brief và Lịch sử hội thoại theo api-contract.md Mục 3.2.
    """
    case = db.query(Case).options(joinedload(Case.brief), joinedload(Case.messages)).filter(Case.id == case_id).first()

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

    # Conversation History
    conversation: list[ConversationItem] = []
    for msg in case.messages:
        conversation.append(
            ConversationItem(
                sender=msg.sender_type,
                content=msg.content,
                created_at=msg.created_at.isoformat() if msg.created_at else utcnow().isoformat(),
            )
        )

    detail_data = TicketDetailData(
        case=TicketDetailCase(
            id=case.id,
            mock_customer_id=case.mock_customer_id or f"CUST_{case.id}",
            vehicle_code_mock=case.vehicle_code_mock or "VF-SF-00231",
            vehicle_model=case.vehicle_model or "VF8",
            intent=case.intent,
            priority=case.priority,
            status=case.status,
        ),
        case_brief=brief_out,
        conversation_history=conversation,
    )

    return ApiResponse(
        success=True,
        data=detail_data,
        error=None,
    )


@router.post("/tickets/{case_id}/actions", response_model=ApiResponse[StaffActionResponseData])
def submit_staff_action(
    case_id: str,
    payload: StaffActionPayload,
    db: Session = Depends(get_db),
):
    """
    Thực hiện hành động xử lý Ticket (HITL Action) và lưu audit log theo api-contract.md Mục 3.3.
    """
    case = db.query(Case).options(joinedload(Case.brief)).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")

    action = payload.action
    previous_state = {
        "status": case.status,
        "brief_summary": case.brief.summary if case.brief else None,
        "assigned_staff_id": case.assigned_staff_id,
    }

    # Gán nhân viên thao tác
    case.assigned_staff_id = payload.staff_id

    # Áp dụng logic hành động
    if action == StaffAction.APPROVE.value:
        case.status = payload.updated_status or TicketStatus.IN_PROGRESS.value

    elif action == StaffAction.EDIT_BRIEF.value:
        if payload.edited_brief:
            if not case.brief:
                case.brief = CaseBrief(
                    id=str(uuid.uuid4()),
                    case_id=case.id,
                    summary=payload.edited_brief.get("summary", ""),
                    captured_fields=payload.edited_brief.get("captured_fields", {}),
                    suggested_action=payload.edited_brief.get("suggested_action"),
                    confidence_score=0.95,
                    is_edited_by_staff=True,
                )
                db.add(case.brief)
            else:
                if "summary" in payload.edited_brief and payload.edited_brief["summary"]:
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

    elif action == StaffAction.REROUTE.value:
        case.status = payload.updated_status or TicketStatus.IN_PROGRESS.value

    elif action == StaffAction.CLOSE.value:
        case.status = TicketStatus.CLOSED.value

    elif action == StaffAction.REOPEN.value:
        case.status = TicketStatus.REOPENED.value

    elif action == StaffAction.REQUEST_INFO.value:
        case.status = TicketStatus.NEEDS_INFORMATION.value

    new_state = {
        "status": case.status,
        "brief_summary": case.brief.summary if case.brief else None,
        "assigned_staff_id": case.assigned_staff_id,
    }

    # Ghi nhận vào bảng staff_audit_logs theo chuẩn data-model.md
    audit_log = StaffAuditLog(
        id=str(uuid.uuid4()),
        case_id=case.id,
        staff_id=payload.staff_id,
        action=action,
        previous_state=previous_state,
        new_state=new_state,
        notes=payload.notes,
        created_at=utcnow(),
    )
    db.add(audit_log)

    db.commit()
    db.refresh(case)

    return ApiResponse(
        success=True,
        data=StaffActionResponseData(success=True, case_id=case.id),
        error=None,
    )
