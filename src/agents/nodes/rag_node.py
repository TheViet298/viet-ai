from __future__ import annotations

import asyncio
import time

from pydantic import BaseModel, Field

from src.agents.context_manager import resolve_policy_conflict
from src.agents.guardrails import sanitize_pii
from src.agents.state import AgentState
from src.agents.tools.vinfast_tools import vinfast_manual_search
from src.config import get_settings
from src.services.agent_llm import structured_call
from src.services.rag_service import select_supported_evidence, valid_citation


class GroundedAnswer(BaseModel):
    answer: str = Field(max_length=3000)
    source_ids: list[str]
    supported: bool


async def rag_node(state: AgentState) -> dict:
    query = state.get("latest_user_message", "")
    unsupported = any(term in query.lower() for term in ("bí mật", "nội bộ", "tháng sau", "không công khai", "chưa công khai"))
    remaining = state.get("llm_budget", {}).get("deadline", time.monotonic() + get_settings().agent_turn_timeout_s) - time.monotonic()
    retrieval = {"status": "NO_SOURCE", "citations": []}
    if not unsupported and remaining > 0:
        try:
            retrieval = await asyncio.wait_for(vinfast_manual_search(query, vehicle_model=state.get("vehicle_model")), timeout=remaining)
        except TimeoutError:
            retrieval["diagnostics"] = {"status": "timeout"}
    citations = [c for c in retrieval.get("citations", []) if valid_citation(c, state.get("vehicle_model"))]
    citations = select_supported_evidence(query, citations)
    reply = "Hiện chưa có tài liệu chính thức đã xác thực đủ để trả lời yêu cầu này. Tôi sẽ ghi nhận để chuyên viên kiểm tra."
    generated = None
    if citations and state.get("confidence_score", 0) >= 0.60:
        generated = await structured_call({**state, "rag_citations": citations}, "rag_qa", GroundedAnswer)
        if generated and (
            not generated.supported
            or not generated.source_ids
            or not set(generated.source_ids).issubset({c["source_id"] for c in citations})
            or resolve_policy_conflict(generated.answer)
        ):
            citations = []
    else:
        citations = []
    if not citations:
        return {
            "is_no_source": True,
            "retrieval_diagnostics": retrieval.get("diagnostics", {}),
            "rag_citations": [],
            "rag_context": [],
            "is_rag_query": True,
            "needs_staff_review": True,
            "rag_distance": retrieval.get("best_distance"),
            "response": reply,
            "final_response": reply,
            "guardrails": {**state.get("guardrails", {}), "low_confidence_escalated": True},
        }
    for citation in citations:
        citation["relevant_snippet"] = sanitize_pii(citation["relevant_snippet"])[0]
    answer = sanitize_pii(generated.answer if generated else "\n\n".join(c["relevant_snippet"] for c in citations))[0]
    links = "\n".join(f"[{c['source_id']}: {c['title']}]({c['url']})" for c in citations)
    reply = f"Theo tài liệu VinFast:\n\n{answer}\n\n{links}"
    return {
        "is_no_source": False,
        "retrieval_diagnostics": retrieval.get("diagnostics", {}),
        "is_rag_query": True,
        "rag_citations": citations,
        "rag_context": [c["relevant_snippet"] for c in citations],
        "rag_distance": min(c["distance"] for c in citations),
        "needs_staff_review": False,
        "response_type": "FAQ_ANSWER",
        "response": reply,
        "final_response": reply,
    }
