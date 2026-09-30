from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.agents.chatbot_agent import process_chat_message
from src.models.schemas import ChatRequest, ChatResponse

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
# 2. Status Check Endpoint
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
