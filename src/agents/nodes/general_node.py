from pydantic import BaseModel, Field

from src.agents.context_manager import resolve_policy_conflict
from src.agents.guardrails import sanitize_pii
from src.agents.state import AgentState
from src.services.agent_llm import structured_call


class ConversationalAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=3000)


async def general_node(state: AgentState) -> dict:
    recent = "\n".join(f"{message.type}: {str(message.content)[:400]}"
                       for message in state.get("messages", [])[-4:])
    generated = await structured_call(
        {**state, "memory_summary": state.get("memory_summary", "") + "\n" + recent},
        "general", ConversationalAnswer,
    )
    text = state.get("latest_user_message", "").casefold()
    fallback = (
        "Anh/chị muốn tìm hiểu cách sạc, nguyên lý hoạt động, tuổi thọ pin hay đang gặp vấn đề gì với pin xe ạ?"
        if any(term in text for term in ["pin", "sạc"])
        else "Anh/chị muốn tìm hiểu điều gì về xe hoặc dịch vụ VinFast ạ?"
    )
    answer = generated.answer.strip() if generated else ""
    if not answer or resolve_policy_conflict(answer):
        answer = fallback
    answer = sanitize_pii(answer)[0]
    return {
        "response": answer, "final_response": answer, "response_type": "FAQ_ANSWER",
        "needs_staff_review": False, "is_no_source": False, "is_rag_query": False,
        "rag_citations": [], "rag_context": [], "case_brief": None,
        "suggested_replies": ["Cách sạc pin", "Nguyên lý hoạt động", "Tuổi thọ pin"]
        if any(term in text for term in ["pin", "sạc"]) else [],
    }
