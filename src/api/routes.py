"""Customer and reviewer endpoints for the Flow 1 case lifecycle."""

import re
from datetime import datetime, timezone
from functools import lru_cache
from hmac import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException

from src.config import get_settings
from src.models.schemas import (
    CaseBrief,
    CaseStatus,
    CustomerActionRequest,
    CustomerChatRequest,
    StaffActionRequest,
)
from src.services.case_store import CaseStore

router = APIRouter()


def envelope(data):
    return {"success": True, "data": data, "error": None,
            "meta": {"timestamp": datetime.now(timezone.utc).isoformat()}}


@lru_cache
def _cached_case_store():
    return CaseStore(get_settings().database_url)


async def get_case_store():
    return _cached_case_store()


async def staff_identity(authorization: str | None = Header(default=None)) -> str:
    settings = get_settings()
    if not settings.staff_api_token:
        raise HTTPException(status_code=503, detail={"code": "UNAVAILABLE", "message": "Staff access is not configured"})
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Staff authentication required"})
    token = authorization.removeprefix("Bearer ")
    if not compare_digest(token, settings.staff_api_token):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Invalid staff credentials"})
    return settings.staff_id


async def customer_session(x_session_id: str | None = Header(default=None)) -> str:
    if not x_session_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Session ID required"})
    return x_session_id


def no_pii(value: str):
    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value) or re.search(r"(?<!\d)(?:\+?84|0)\d{9,10}(?!\d)", value):
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Remove personal contact information"})


def describe(messages, context):
    text = " ".join(messages)
    lower = text.lower()
    emergency = any(word in lower for word in ("cháy", "bốc khói", "mất phanh")) or (
        "rùa vàng" in lower and any(word in lower for word in ("cao tốc", "mất kiểm soát", "giảm công suất"))
    )
    charging = any(word in lower for word in ("sạc", "pin", "bms", "charger"))
    if charging:
        intent, priority, routing = "Charging/Battery", "HIGH", "Charging Support"
    elif any(word in lower for word in ("khiếu nại", "phàn nàn")):
        intent, priority, routing = "Complaint/Feedback", "MEDIUM", "Customer Support"
    elif any(word in lower for word in ("sự cố", "lỗi", "hỏng", "phanh")):
        intent, priority, routing = "Service/Incident", "HIGH", "Service Support"
    else:
        intent, priority, routing = "Sales/General Info", "LOW", "Customer Support"
    if emergency:
        priority = "CRITICAL"
    vehicle = context.vehicle_model or next((match.upper() for match in re.findall(r"\b(?:VF\s*[3-9]|e34)\b", text, re.I)), None)
    location_match = re.search(r"\btrạm\s+([^,.!?]+)", text, re.I)
    location = location_match.group(1).strip() if location_match else None
    captured = {"vehicle_model": vehicle, "symptom": text}
    if location:
        captured["station_location"] = location
    missing = []
    if charging and not vehicle:
        missing.append("vehicle_model")
    if charging and not location:
        missing.append("station_location")
    brief = CaseBrief(
        summary=text[:5000], captured_fields=captured, missing_fields=missing,
        suggested_action="Reviewer to assess and route this case",
        suggested_routing=routing, confidence_score=0.6 if charging else 0.0,
        safety_flags=["EMERGENCY"] if emergency else [],
    )
    return intent, priority, brief, emergency


@router.post("/customer/chat")
async def customer_chat(request: CustomerChatRequest, store: CaseStore = Depends(get_case_store)):
    no_pii(request.message)
    for value in request.client_context.model_dump().values():
        if value:
            no_pii(value)
    if request.case_id:
        case, _ = store.add_case_message(request.case_id, request.session_id, request.message)
        return envelope({"response_type": "CASE_UPDATED", "case_id": case["id"],
                         "status": case["status"], "customer_message": "Thông tin đã được ghi nhận để nhân viên xem xét."})
    turn, messages = store.prepare_chat(request.session_id, request.message)
    intent, priority, brief, emergency = describe(messages, request.client_context)
    if brief.missing_fields and not emergency and turn < 2:
        prompt = "Vui lòng bổ sung: " + ", ".join(brief.missing_fields) + "."
        next_turn = store.clarify(request.session_id, prompt)
        return envelope({"response_type": "CLARIFICATION", "case_id": None,
                         "clarification_turn": next_turn, "max_clarification_turns": 2,
                         "message": prompt, "suggested_replies": []})
    status = CaseStatus.NEEDS_INFORMATION.value if brief.missing_fields and not emergency else CaseStatus.STAFF_REVIEWING.value
    customer_message = "Hồ sơ đã được tạo để nhân viên xem xét. Vui lòng theo dõi trạng thái tại đây."
    if emergency:
        customer_message = "Hãy dừng xe ở nơi an toàn và liên hệ dịch vụ khẩn cấp phù hợp. Hồ sơ đã được chuyển để nhân viên xem xét."
    case = store.create_case(request.session_id, request.client_context, intent, priority,
                             status, brief.model_dump(), customer_message)
    return envelope({"response_type": "CASE_CREATED", "case_id": case["id"],
                     "status": case["status"], "intent": intent, "priority": priority,
                     "customer_message": customer_message})


@router.get("/customer/cases/{case_id}/status")
async def customer_status(case_id: str, session_id: str = Depends(customer_session),
                    store: CaseStore = Depends(get_case_store)):
    case = store.require_case(case_id, session_id)
    store.record_read(case_id, f"CUSTOMER:{session_id}", "READ_STATUS")
    return envelope({"case_id": case_id, "status": case["status"],
                     "updated_at": case["updated_at"],
                     "customer_message": "Hồ sơ đang ở trạng thái " + case["status"] + "."})


@router.post("/customer/cases/{case_id}/actions")
async def customer_action(case_id: str, request: CustomerActionRequest,
                    session_id: str = Depends(customer_session), store: CaseStore = Depends(get_case_store)):
    store.require_case(case_id, session_id)
    if request.reason:
        no_pii(request.reason)
    allowed, target = ({"Resolved"}, "Closed") if request.action == "CONFIRM_RESOLUTION" else ({"Resolved", "Closed"}, "Reopened")
    case, _ = store.transition(case_id, allowed, target, f"CUSTOMER:{session_id}",
                               request.action, request.reason)
    if target == "Reopened":
        case, _ = store.transition(case_id, {"Reopened"}, "Staff Reviewing", "SYSTEM", "QUEUE_REOPENED")
    return envelope({"case_id": case_id, "status": case["status"], "updated_at": case["updated_at"]})


@router.get("/staff/tickets")
async def staff_queue(status: CaseStatus | None = None, priority: str | None = None,
                staff_id: str = Depends(staff_identity), store: CaseStore = Depends(get_case_store)):
    if priority and priority not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Invalid priority"})
    cases = store.list_cases(status.value if status else None, priority)
    for case in cases:
        store.record_read(case["id"], f"STAFF:{staff_id}", "READ_QUEUE")
    return envelope({"items": cases, "total": len(cases)})


@router.get("/staff/tickets/{case_id}")
async def staff_detail(case_id: str, staff_id: str = Depends(staff_identity),
                 store: CaseStore = Depends(get_case_store)):
    store.record_read(store.require_case(case_id)["id"], f"STAFF:{staff_id}", "READ_DETAIL")
    return envelope(store.detail(case_id))


@router.post("/staff/tickets/{case_id}/actions")
async def staff_action(case_id: str, request: StaffActionRequest,
                 staff_id: str = Depends(staff_identity), store: CaseStore = Depends(get_case_store)):
    store.require_case(case_id)
    if request.notes:
        no_pii(request.notes)
    if request.target_team:
        no_pii(request.target_team)
    action_map = {
        "APPROVE": ({"Staff Reviewing"}, "In Progress"),
        "EDIT_BRIEF": ({"Staff Reviewing"}, "Staff Reviewing"),
        "REROUTE": ({"Staff Reviewing"}, "In Progress"),
        "REQUEST_INFO": ({"Staff Reviewing"}, "Needs Information"),
        "RESOLVE": ({"In Progress"}, "Resolved"),
        "CLOSE": ({"Resolved"}, "Closed"),
        "REOPEN": ({"Resolved", "Closed"}, "Reopened"),
    }
    allowed, target = action_map[request.action]
    brief = request.edited_brief.model_dump() if request.edited_brief else None
    if brief:
        brief["is_edited_by_staff"] = True
        if any(key.lower() in {"name", "phone", "email"} for key in brief["captured_fields"]):
            raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Personal fields are not allowed"})
        no_pii(str(brief))
    if request.action in {"APPROVE", "REROUTE"} and not (request.target_team or store.get_brief(case_id).get("suggested_routing")):
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Routing team required"})
    if request.target_team and request.action in {"APPROVE", "REROUTE"}:
        brief = brief or store.get_brief(case_id)
        brief["suggested_routing"] = request.target_team
        brief["is_edited_by_staff"] = True
    reason = request.notes or request.target_team
    case, event_id = store.transition(case_id, allowed, target, f"STAFF:{staff_id}",
                                      request.action, reason, brief)
    if target == "Reopened":
        case, _ = store.transition(case_id, {"Reopened"}, "Staff Reviewing", "SYSTEM", "QUEUE_REOPENED")
    return envelope({"case_id": case_id, "status": case["status"],
                     "brief": store.get_brief(case_id), "updated_at": case["updated_at"],
                     "audit_event_id": event_id})


@router.get("/status")
async def agent_status():
    return {"status": "ready", "agent": "Case API v1.0"}
