from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.db_models import Case, ReviewerFeedback, Ticket, TicketStatus, utcnow

router = APIRouter(prefix="/staff", tags=["staff"])

STATUS_TO_FE = {
    "OPEN": "New",
    "WAITING_USER": "Needs Information",
    "PENDING_REVIEW": "Staff Reviewing",
    "ROUTED": "In Progress",
    "CLOSED": "Closed",
}

FE_TO_STATUS = {
    "New": "OPEN",
    "Needs Information": "WAITING_USER",
    "Staff Reviewing": "PENDING_REVIEW",
    "In Progress": "ROUTED",
    "Resolved": "ROUTED",
    "Closed": "CLOSED",
    "Reopened": "OPEN",
}

INTENT_TO_FE = {
    "charging": "Charging/Battery",
    "service_incident": "Service/Incident",
    "sales": "Sales",
    "complaint": "Complaint",
    "out_of_scope": "Complaint",
}

PRIORITY_TO_FE = {
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "critical": "CRITICAL",
}


def parse_case_id(case_str: str | None) -> int | None:
    if not case_str:
        return None
    digits = "".join(ch for ch in str(case_str) if ch.isdigit())
    return int(digits) if digits else None


class StaffActionPayload(BaseModel):
    action: Literal["APPROVE", "EDIT_BRIEF", "REROUTE", "CLOSE", "REOPEN", "REQUEST_INFO"]
    staff_id: str = "STAFF_DEMO"
    updated_status: str | None = None
    edited_brief: dict[str, Any] | None = None
    notes: str | None = None


class ApiResponse(BaseModel):
    success: bool
    data: Any
    error: str | None = None


@router.get("/tickets", response_model=ApiResponse)
def get_ticket_queue(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Lấy danh sách ticket cho bảng điều khiển Console của nhân viên."""
    query = db.query(Case)

    if status and status != "ALL":
        mapped_status = FE_TO_STATUS.get(status, status)
        query = query.filter(Case.ticket_status == mapped_status)

    if priority and priority != "ALL":
        lower_prio = priority.lower()
        query = query.filter(Case.priority == lower_prio)

    cases = query.order_by(Case.created_at.desc()).all()

    items = []
    for c in cases:
        b_data = c.brief_data or {}
        model = b_data.get("vehicle_model") or "VF8"
        code = (
            b_data.get("captured_fields", {}).get("vehicle_code_mock")
            if isinstance(b_data, dict)
            else None
        ) or f"VF-SF-{c.id:04d}"

        items.append({
            "id": f"CASE-{c.id:04d}",
            "mock_customer_id": c.customer_ref or f"CUST_{c.id}",
            "vehicle_model": model,
            "vehicle_code_mock": code,
            "intent": INTENT_TO_FE.get(c.intent, "Service/Incident"),
            "priority": PRIORITY_TO_FE.get(c.priority, "MEDIUM"),
            "status": STATUS_TO_FE.get(c.ticket_status, "Staff Reviewing"),
            "missing_info_flag": c.ticket_status == "WAITING_USER",
            "created_at": c.created_at.isoformat() if c.created_at else utcnow().isoformat(),
            "confidence_score": c.confidence if c.confidence is not None else 0.9,
        })

    return ApiResponse(
        success=True,
        data={"items": items, "total": len(items)},
        error=None,
    )


@router.get("/tickets/{case_id}", response_model=ApiResponse)
def get_ticket_detail(case_id: str, db: Session = Depends(get_db)):
    """Lấy chi tiết Case, Brief do AI tóm tắt và Lịch sử hội thoại."""
    parsed_id = parse_case_id(case_id)
    if not parsed_id:
        raise HTTPException(status_code=400, detail="Mã Case không hợp lệ")

    case = db.get(Case, parsed_id)
    if not case:
        raise HTTPException(status_code=404, detail="Không tìm thấy Case trong cơ sở dữ liệu")

    b_data = case.brief_data or {}
    model = b_data.get("vehicle_model") or "VF8"
    captured = b_data.get("captured_fields") or {}
    code = captured.get("vehicle_code_mock") or f"VF-SF-{case.id:04d}"

    summary = b_data.get("summary") or f"Yêu cầu hỗ trợ xe {model}."
    suggested_action = b_data.get("suggested_action") or "Kiểm tra thông tin và điều phối kỹ thuật."

    conversation = []
    for msg in case.messages:
        sender_map = {
            "customer": "CUSTOMER",
            "agent": "AGENT",
            "reviewer": "STAFF",
        }
        conversation.append({
            "sender": sender_map.get(msg.sender, "SYSTEM"),
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else utcnow().isoformat(),
        })

    detail_data = {
        "case": {
            "id": f"CASE-{case.id:04d}",
            "mock_customer_id": case.customer_ref or f"CUST_{case.id}",
            "vehicle_code_mock": code,
            "vehicle_model": model,
            "intent": INTENT_TO_FE.get(case.intent, "Service/Incident"),
            "priority": PRIORITY_TO_FE.get(case.priority, "MEDIUM"),
            "status": STATUS_TO_FE.get(case.ticket_status, "Staff Reviewing"),
        },
        "case_brief": {
            "summary": summary,
            "captured_fields": captured,
            "suggested_action": suggested_action,
            "confidence_score": case.confidence if case.confidence is not None else 0.92,
            "is_edited_by_staff": any(f.action == "edit" for f in case.feedbacks),
        },
        "conversation_history": conversation,
    }

    return ApiResponse(
        success=True,
        data=detail_data,
        error=None,
    )


@router.post("/tickets/{case_id}/actions", response_model=ApiResponse)
def submit_staff_action(case_id: str, payload: StaffActionPayload, db: Session = Depends(get_db)):
    """Ghi nhận hành động của nhân viên HITL (Approve, Edit Brief, Reroute, Close...)."""
    parsed_id = parse_case_id(case_id)
    if not parsed_id:
        raise HTTPException(status_code=400, detail="Mã Case không hợp lệ")

    case = db.get(Case, parsed_id)
    if not case:
        raise HTTPException(status_code=404, detail="Không tìm thấy Case trong cơ sở dữ liệu")

    action = payload.action
    action_lower = action.lower()

    if action == "APPROVE":
        case.ticket_status = TicketStatus.ROUTED.value
        routing = case.suggested_routing or "Service"
        case.tickets.append(Ticket(assigned_department=routing, dispatched_at=utcnow()))
    elif action == "EDIT_BRIEF":
        if payload.edited_brief:
            curr_brief = case.brief_data or {}
            curr_brief.update(payload.edited_brief)
            case.brief_data = curr_brief
    elif action == "REROUTE":
        routing = payload.notes or "Service"
        case.suggested_routing = routing
        case.tickets.append(Ticket(assigned_department=routing, dispatched_at=utcnow()))
        case.ticket_status = TicketStatus.ROUTED.value
    elif action == "CLOSE":
        case.ticket_status = TicketStatus.CLOSED.value
    elif action == "REOPEN":
        case.ticket_status = TicketStatus.OPEN.value
    elif action == "REQUEST_INFO":
        case.ticket_status = TicketStatus.WAITING_USER.value

    feedback = ReviewerFeedback(
        case_id=case.id,
        reviewer_name=payload.staff_id,
        action=action_lower,
        edited_brief=payload.edited_brief,
        final_routing=case.suggested_routing,
        comment=payload.notes,
    )
    case.feedbacks.append(feedback)

    db.commit()
    db.refresh(case)

    return ApiResponse(
        success=True,
        data={"success": True, "case_id": f"CASE-{case.id:04d}"},
        error=None,
    )
