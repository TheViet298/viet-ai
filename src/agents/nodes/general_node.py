import re

from pydantic import BaseModel, Field

from src.agents.context_manager import resolve_policy_conflict
from src.agents.guardrails import sanitize_pii
from src.agents.state import AgentState
from src.services.agent_llm import structured_call
from src.services.vehicle_knowledge import KNOWLEDGE_NOTE, common_vehicle_explanation, is_general_vehicle_question


class ConversationalAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=3000)


async def general_node(state: AgentState) -> dict:
    text = state.get("latest_user_message", "").casefold()
    # Resolve only short conceptual references; never inherit a repair request.
    if (re.match(r"^(?:nó|cái đó|hệ thống đó)\b", text) and len(text) < 120
            and re.search(r"là gì|nghĩa|tác dụng|khác|hoạt động|dùng để", text)):
        previous = next((str(m.content) for m in reversed(state.get("messages", []))
                         if m.type == "human" and str(m.content).casefold() != text), "")
        if is_general_vehicle_question(previous):
            text = previous.casefold() + "\n" + text
    common = is_general_vehicle_question(text)
    explanation = common_vehicle_explanation(text) if common else None
    recent = "\n".join(f"{message.type}: {str(message.content)[:400]}"
                       for message in state.get("messages", [])[-4:])
    generated = None if explanation else await structured_call(
        {**state, "memory_summary": state.get("memory_summary", "") + "\n" + recent},
        "general", ConversationalAnswer,
    )
    fallback = (
        "Tôi chưa hoàn tất được phần giải thích khái niệm này do dịch vụ trả lời đang không sẵn sàng. Anh/chị vui lòng thử lại."
        if common else
        "Anh/chị muốn tìm hiểu cách sạc, nguyên lý hoạt động, tuổi thọ pin hay đang gặp vấn đề gì với pin xe ạ?"
        if any(term in text for term in ["pin", "sạc"])
        else "Anh/chị muốn tìm hiểu điều gì về xe hoặc dịch vụ VinFast ạ?"
    )
    answer = explanation or (generated.answer.strip() if generated else "")
    if not answer or resolve_policy_conflict(answer):
        answer = fallback
    answer = sanitize_pii(answer)[0]
    if common:
        answer += "\n\n" + KNOWLEDGE_NOTE
    return {
        "response": answer, "final_response": answer, "response_type": "FAQ_ANSWER",
        "needs_staff_review": False, "is_no_source": False, "is_rag_query": False,
        "rag_citations": [], "rag_context": [], "case_brief": None,
        "suggested_replies": ["Cách sạc pin", "Nguyên lý hoạt động", "Tuổi thọ pin"]
        if any(term in text for term in ["pin", "sạc"]) else [],
    }
