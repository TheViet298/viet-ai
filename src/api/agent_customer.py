from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import Principal, customer, staff
from src.api.routes import chat
from src.models.schemas import ChatResponse, ConfirmationRequest, LocationRequest, StaffActionRequest
from src.services.location_service import save_location, suggest_service_points
from src.services.session_store import get_store

router = APIRouter()
router.add_api_route(
    "/customer/chat", chat, methods=["POST"], response_model=ChatResponse, dependencies=[Depends(customer)]
)


def translate_error(exc):
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail="Case not found")
    return HTTPException(status_code=409, detail=str(exc))


@router.get("/customer/cases")
async def cases(principal: Principal = Depends(customer)):
    return {"success": True, "data": get_store().list_cases(principal.id)}


@router.get("/customer/cases/{case_id}")
async def case(case_id: str, principal: Principal = Depends(customer)):
    try:
        return {"success": True, "data": get_store().case(case_id, principal.id)}
    except (PermissionError, KeyError) as exc:
        raise translate_error(exc) from exc


@router.post("/customer/cases/{case_id}/confirmation")
async def confirmation(case_id: str, request: ConfirmationRequest, principal: Principal = Depends(customer)):
    status = "Closed" if request.action == "RESOLVED_CONFIRMED" else "Reopened"
    try:
        return {"success": True, "data": get_store().change_status(case_id, status, principal.id, owner=principal.id)}
    except (PermissionError, KeyError, ValueError) as exc:
        raise translate_error(exc) from exc


@router.post("/customer/location")
async def location(request: LocationRequest, principal: Principal = Depends(customer)):
    try:
        return {"success": True, "data": save_location(request.model_dump(), principal.id)}
    except (PermissionError, KeyError, ValueError) as exc:
        raise translate_error(exc) from exc


@router.get("/customer/cases/{case_id}/service-points")
async def service_points(case_id: str, principal: Principal = Depends(customer)):
    try:
        return {"success": True, "data": suggest_service_points(case_id, principal.id)}
    except (PermissionError, KeyError, ValueError) as exc:
        raise translate_error(exc) from exc


@router.get("/staff/tickets")
async def tickets(principal: Principal = Depends(staff)):
    return {"success": True, "data": get_store().list_cases()}


@router.get("/staff/tickets/{case_id}")
async def ticket(case_id: str, principal: Principal = Depends(staff)):
    try:
        return {"success": True, "data": get_store().case(case_id)}
    except KeyError as exc:
        raise translate_error(exc) from exc


@router.post("/staff/tickets/{case_id}/actions")
async def ticket_action(case_id: str, request: StaffActionRequest, principal: Principal = Depends(staff)):
    statuses = {
        "APPROVE": "In Progress",
        "REQUEST_INFO": "Needs Information",
        "RESOLVE": "Resolved",
        "CLOSE": "Closed",
        "REOPEN": "Reopened",
    }
    try:
        return {"success": True, "data": get_store().change_status(case_id, statuses[request.action], principal.id)}
    except (KeyError, ValueError) as exc:
        raise translate_error(exc) from exc
