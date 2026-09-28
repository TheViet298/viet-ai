from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Case,
    Intent,
    Message,
    Priority,
    ReviewAction,
    ReviewerFeedback,
    Ticket,
    TicketStatus,
    utcnow,
)
from app.schemas import (
    CaseCreate,
    CaseDetail,
    CaseSummary,
    CaseUpdate,
    MessageCreate,
    MessageOut,
    ReviewCreate,
)

router = APIRouter(prefix="/cases", tags=["cases"])


def get_case_or_404(db: Session, case_id: int) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case không tồn tại")
    return case


@router.post("", response_model=CaseDetail, status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    """Tạo case mới từ tin nhắn đầu tiên của khách."""
    case = Case(
        source_channel=payload.source_channel.value,
        customer_ref=payload.customer_ref,
        ticket_status=TicketStatus.OPEN.value,
    )
    case.messages.append(
        Message(sender="customer", channel=payload.source_channel.value, content=payload.content)
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("", response_model=list[CaseSummary])
def list_cases(
    ticket_status: TicketStatus | None = None,
    intent: Intent | None = None,
    priority: Priority | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Danh sách case (cho Service Agent Console), lọc theo trạng thái/intent/priority."""
    q = db.query(Case)
    if ticket_status:
        q = q.filter(Case.ticket_status == ticket_status.value)
    if intent:
        q = q.filter(Case.intent == intent.value)
    if priority:
        q = q.filter(Case.priority == priority.value)
    return q.order_by(Case.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: int, db: Session = Depends(get_db)):
    return get_case_or_404(db, case_id)


@router.patch("/{case_id}", response_model=CaseDetail)
def update_case(case_id: int, payload: CaseUpdate, db: Session = Depends(get_db)):
    """Agent ghi kết quả triage/brief. Chỉ cập nhật các field được gửi lên."""
    case = get_case_or_404(db, case_id)
    for field, value in payload.model_dump(exclude_unset=True, mode="json").items():
        setattr(case, field, value)
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/messages", response_model=MessageOut, status_code=201)
def add_message(case_id: int, payload: MessageCreate, db: Session = Depends(get_db)):
    """Thêm tin nhắn (khách/agent/reviewer). Khách trả lời khi case đang WAITING_USER thì case về OPEN."""
    case = get_case_or_404(db, case_id)
    message = Message(
        case_id=case.id,
        sender=payload.sender,
        channel=payload.channel.value if payload.channel else case.source_channel,
        content=payload.content,
    )
    db.add(message)
    if payload.sender == "customer" and case.ticket_status == TicketStatus.WAITING_USER.value:
        case.ticket_status = TicketStatus.OPEN.value
    db.commit()
    db.refresh(message)
    return message


@router.post("/{case_id}/review", response_model=CaseDetail)
def review_case(case_id: int, payload: ReviewCreate, db: Session = Depends(get_db)):
    """Reviewer approve / edit / escalate, sau đó dispatch (tạo ticket, case -> ROUTED)."""
    case = get_case_or_404(db, case_id)

    if case.ticket_status != TicketStatus.PENDING_REVIEW.value:
        raise HTTPException(
            status_code=409,
            detail=f"Chỉ review được case đang PENDING_REVIEW (hiện tại: {case.ticket_status})",
        )
    if payload.action == ReviewAction.edit and payload.edited_brief is None:
        raise HTTPException(status_code=422, detail="action=edit cần có edited_brief")

    routing = payload.final_routing or case.suggested_routing
    if not routing:
        raise HTTPException(
            status_code=422, detail="Thiếu final_routing (case chưa có suggested_routing)"
        )

    if payload.action == ReviewAction.edit:
        case.brief_data = payload.edited_brief

    case.feedbacks.append(
        ReviewerFeedback(
            reviewer_name=payload.reviewer_name,
            action=payload.action.value,
            edited_brief=payload.edited_brief,
            final_routing=routing,
            comment=payload.comment,
        )
    )
    case.tickets.append(Ticket(assigned_department=routing, dispatched_at=utcnow()))
    case.ticket_status = TicketStatus.ROUTED.value

    db.commit()
    db.refresh(case)
    return case