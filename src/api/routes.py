from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from src.agents.chatbot_agent import process_chat_message
from src.agents.guardrails import EMERGENCY_SAFE_GUIDANCE, evaluate_hard_safety
from src.api.auth import Principal, optional_principal
from src.models.schemas import ChatRequest, ChatResponse
from src.services.session_store import SessionConflictError, decode_state, get_store

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    response: Response,
    principal: Principal | None = Depends(optional_principal),
) -> ChatResponse:
    """Chat với AI agent."""
    try:
        if principal:
            sid = request.session_id or uuid4().hex
            owner, role = principal.id, principal.role
        else:
            # The server-issued cookie is the quota/session identifier, not a role supplied by the client.
            sid = http_request.cookies.get("vf_guest_session") or uuid4().hex
            owner, role = f"guest:{sid}", "guest"
            response.set_cookie(
                "vf_guest_session", sid, httponly=True, samesite="lax", secure=http_request.url.scheme == "https"
            )
        if request.case_id:
            if role != "customer":
                raise HTTPException(status_code=401, detail="Customer authentication required")
            case = get_store().case(request.case_id, owner)
            if case["session_id"] != sid:
                raise HTTPException(status_code=409, detail="Case and session do not match")
            with get_store().connect() as db:
                row = db.execute("SELECT state FROM agent_sessions WHERE id=?", (sid,)).fetchone()
            if case["status"] in {"Closed", "Resolved"} or (
                row and decode_state(row["state"]).get("case_id") != request.case_id
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Requested case is not the active case; use confirmation to reopen or start a new session",
                )
        result = await process_chat_message(
            request.message,
            session_id=sid,
            user_role=role,
            owner=owner,
            client_context={
                k: v for k, v in request.client_context.items() if k in {"vehicle_model", "vehicle_code_mock"}
            },
        )
        return ChatResponse(**result)
    except PermissionError as exc:
        raise HTTPException(status_code=429 if "quota" in str(exc) else 403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc
    except SessionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        if evaluate_hard_safety(request.message)[0]:
            return ChatResponse(
                response=EMERGENCY_SAFE_GUIDANCE
                + "\n\nHiện chưa lưu được hồ sơ hỗ trợ. Vui lòng gọi hotline để được tiếp nhận trực tiếp.",
                session_id=sid,
                response_type="EMERGENCY_ALERT",
                intent="Service/Incident",
                priority="CRITICAL",
                is_safety_trigger=True,
                needs_staff_review=True,
            )
        raise HTTPException(status_code=503, detail="Agent service temporarily unavailable") from exc


@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái agent."""
    return {"status": "ready", "agent": "VinFast ServiceFlow StateGraph v1.0"}


router.add_api_route("/public/chat", chat, methods=["POST"], response_model=ChatResponse)
