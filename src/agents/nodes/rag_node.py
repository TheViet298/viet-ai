from __future__ import annotations

import asyncio
import time

from pydantic import BaseModel, Field

from src.agents.context_manager import build_7_layer_context, load_prompt, resolve_policy_conflict, trim_context_layers
from src.agents.guardrails import sanitize_pii
from src.agents.state import AgentState
from src.agents.tools.vinfast_tools import vinfast_manual_search
from src.config import get_settings
from src.services.agent_llm import structured_call
from src.services.answer_evidence import is_turtle_question
from src.services.rag_service import RAGService, select_supported_evidence, valid_citation


class GroundedAnswer(BaseModel):
    answer: str = Field(max_length=3000)
    source_ids: list[str]
    supported: bool


async def rag_node(state: AgentState) -> dict:
    query = state.get("resolved_query") or state.get("latest_user_message", "")
    unsupported = any(term in query.lower() for term in ("bí mật", "nội bộ", "tháng sau", "không công khai", "chưa công khai"))
    remaining = state.get("llm_budget", {}).get("deadline", time.monotonic() + get_settings().agent_turn_timeout_s) - time.monotonic()
    retrieval = RAGService.failure("NO_SOURCE", "unsupported_request") if unsupported else RAGService.failure("TIMEOUT", "deadline_exhausted")
    if not unsupported and remaining > 0:
        try:
            search_query = query + " chỉ báo giới hạn công suất" if is_turtle_question(query) else query
            retrieval = await asyncio.wait_for(vinfast_manual_search(search_query, vehicle_model=state.get("vehicle_model")),
                                               timeout=min(remaining, get_settings().rag_retrieval_timeout_s))
        except TimeoutError:
            retrieval = RAGService.failure("TIMEOUT", "timeout")
        except Exception:
            retrieval = RAGService.failure("ERROR", "retrieval_tool_error")
    citations = [c for c in retrieval.get("citations", []) if valid_citation(c, state.get("vehicle_model"))]
    citations = select_supported_evidence(query, citations)
    if citations:
        layers = build_7_layer_context({**state, "rag_citations": citations}, load_prompt("rag_qa"))
        try:
            messages = trim_context_layers(layers, max_bytes=get_settings().agent_context_max_bytes)
            if not any(layers.retrieval_context in str(m.content) for m in messages):
                raise ValueError("Evidence cannot fit prompt budget")
        except ValueError:
            citations = []
            retrieval = {**retrieval, "status": "NO_SOURCE", "citations": [], "diagnostics": {
                **retrieval.get("diagnostics", {}), "category": "context_budget_exceeded", "stage": "prompt",
                "selected_parent_ids": [], "prompt_max_bytes": get_settings().agent_context_max_bytes}}
    reply = "Hiện chưa có tài liệu chính thức đã xác thực đủ để trả lời yêu cầu này. Tôi sẽ ghi nhận để chuyên viên kiểm tra."
    if "điều kiện" in query.casefold() and "bảo hành" in query.casefold():
        reply = "Anh/chị đang hỏi điều kiện bảo hành của xe vừa trao đổi. Hiện tôi chưa có đoạn tài liệu xác thực đủ để giải thích điều kiện này; tôi sẽ chuyển chuyên viên kiểm tra, tránh nhầm với điều kiện bảo hành pin hoặc từng hạng mục."
    if retrieval.get("status") in {"UNAVAILABLE", "ERROR", "TIMEOUT"}:
        reply = "Hệ thống tra cứu hiện chưa hoàn tất được yêu cầu. Tôi sẽ chuyển chuyên viên kiểm tra."
    elif retrieval.get("diagnostics", {}).get("category") == "context_budget_exceeded":
        reply = "Tài liệu cần thiết vượt giới hạn xử lý hiện tại. Tôi sẽ chuyển chuyên viên kiểm tra đầy đủ điều kiện."
    generated = None
    if citations and state.get("confidence_score", 0) >= 0.60:
        generated = await structured_call({**state, "rag_citations": citations}, "rag_qa", GroundedAnswer)
        if generated is None and get_settings().agent_llm_enabled:
            citations = []
            reply = "Tôi chưa hoàn tất được việc tạo câu trả lời từ tài liệu đã tìm thấy. Anh/chị vui lòng thử lại; tôi không thể xác nhận nội dung lúc này."
            retrieval = {**retrieval, "status": "ERROR", "diagnostics": {
                **retrieval.get("diagnostics", {}), "stage": "generation", "category": "generation_unavailable"}}
        if generated and (
            not generated.supported
            or not generated.answer.strip()
            or not generated.source_ids
            or not set(generated.source_ids).issubset({c["source_id"] for c in citations})
            or resolve_policy_conflict(generated.answer)
        ):
            citations = []
            retrieval = {**retrieval, "status": "NO_SOURCE", "diagnostics": {
                **retrieval.get("diagnostics", {}), "stage": "generation", "category": "unsupported_answer"}}
    else:
        citations = []
    if not citations:
        if retrieval.get("status") == "SUCCESS":
            retrieval = {**retrieval, "status": "NO_SOURCE", "diagnostics": {
                **retrieval.get("diagnostics", {}), "category": "missing_answer_evidence"}}
        if is_turtle_question(query) and retrieval.get("status") == "NO_SOURCE":
            reply = "Tôi chưa tìm được đoạn tài liệu xác thực giải thích biểu tượng con rùa vàng cho mẫu xe này. Anh/chị vui lòng cho biết mẫu xe, đời xe hoặc gửi ảnh biểu tượng để đối chiếu đúng cảnh báo."
        return {
            "is_no_source": True,
            "retrieval_status": retrieval.get("status", "NO_SOURCE"),
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
    if generated:
        citations = [c for c in citations if c["source_id"] in generated.source_ids]
    for citation in citations:
        citation["relevant_snippet"] = sanitize_pii(citation["relevant_snippet"])[0]
    answer = sanitize_pii(generated.answer if generated else "\n\n".join(c["relevant_snippet"] for c in citations))[0]
    reply = f"Theo tài liệu VinFast:\n\n{answer}"
    return {
        "is_no_source": False,
        "retrieval_status": "SUCCESS",
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
