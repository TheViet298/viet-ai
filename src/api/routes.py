from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from src.agents.chatbot_agent import process_chat_message
from src.models.schemas import (
    ChatRequest,
    ChatResponse,
    CustomerChatRequest,
    ApiResponseEnvelope,
)

router = APIRouter()


# =====================================================================
# 1. Simplified Chat Endpoint (Phục vụ Demo Chatbot)
# =====================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat với AI agent tích hợp RAG VinFast & Guardrails (Dạng phản hồi phẳng)."""
    try:
        result = await process_chat_message(request.message)
        analysis_summary = (
            f"Intent: {result.get('intent')} | "
            f"Priority: {result.get('priority')} | "
            f"Needs Review: {result.get('needs_staff_review')} | "
            f"Citations: {len(result.get('citations', []))}"
        )
        return ChatResponse(
            response=result["reply"],
            analysis=analysis_summary,
            intent=result.get("intent"),
            priority=result.get("priority"),
            needs_staff_review=result.get("needs_staff_review", False),
            is_safety_trigger=result.get("is_safety_trigger", False),
            citations=result.get("citations", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# 2. Official Customer Chat Endpoint (Chuẩn API Contract Envelope)
# =====================================================================

@router.post("/customer/chat", response_model=ApiResponseEnvelope)
async def customer_chat(request: CustomerChatRequest) -> ApiResponseEnvelope:
    """Endpoint khách hàng chính thức theo chuẩn docs/architecture/api-contract.md."""
    try:
        result = await process_chat_message(request.message)

        # Map response_type theo chuẩn Section 2.1 của api-contract.md
        if result.get("is_safety_trigger"):
            response_type = "SAFETY_ALERT"
        elif result.get("citations"):
            response_type = "FAQ_ANSWER"
        elif result.get("intent") in ("charging_battery", "service_incident") and result.get("priority") in ("high", "critical"):
            response_type = "CLARIFICATION"
        else:
            response_type = "NO_SOURCE" if result.get("needs_staff_review") else "FAQ_ANSWER"

        data_payload = {
            "response_type": response_type,
            "message": result["reply"],
            "intent": result.get("intent"),
            "priority": result.get("priority"),
            "is_safety_trigger": result.get("is_safety_trigger", False),
            "needs_staff_review": result.get("needs_staff_review", False),
            "citations": result.get("citations", []),
            "case_id": request.case_id,
            "session_id": request.session_id,
        }

        return ApiResponseEnvelope(
            success=True,
            data=data_payload,
            error=None,
            meta={"timestamp": datetime.now(timezone.utc).isoformat()}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# 3. Status Check Endpoint
# =====================================================================

@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái sẵn sàng của AI agent và Vector Knowledge Base."""
    return {
        "status": "ready",
        "agent": "VinFast RAG Chatbot Agent v1.0",
        "knowledge_base": "vinfast_knowledge_base",
        "safety_guardrails": "enabled"
    }
