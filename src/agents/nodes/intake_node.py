from __future__ import annotations

import time

from langchain_core.messages import HumanMessage

from src.agents.context_manager import apply_fact_recency_and_invalidation
from src.agents.guardrails import sanitize_pii
from src.agents.nodes.triage_node import extract_fields
from src.agents.state import AgentState
from src.config import get_settings
from src.services.tracer import sanitized_snapshot


async def intake_node(state: AgentState) -> dict:
    text, detected, types = sanitize_pii((state.get("latest_user_message") or state.get("query") or "").strip())
    facts = sanitized_snapshot(state.get("captured_fields", {}))
    history = sanitized_snapshot(state.get("fact_history", []))
    for field, value in extract_fields(text).items():
        facts, history = apply_fact_recency_and_invalidation(
            facts, history, field, value, f"user:turn:{state.get('turn', 0) + 1}"
        )
    return {
        "llm_budget": {"deadline": time.monotonic() + get_settings().agent_turn_timeout_s, "attempts": 0},
        "retrieval_diagnostics": {},
        "query": text,
        "latest_user_message": text,
        "messages": [HumanMessage(content=text)],
        "captured_fields": facts,
        "vehicle_model": facts.get("vehicle_model", state.get("vehicle_model")),
        "fact_history": history,
        "memory_summary": sanitize_pii(state.get("memory_summary", ""))[0],
        "turn": state.get("turn", 0) + 1,
        "clarification_turn": max(0, min(state.get("clarification_turn", 0), 2)),
        "max_clarification_turns": 2,
        "suggested_replies": [],
        "case_brief": None,
        "response": "",
        "final_response": "",
        "is_no_source": False,
        "rag_citations": [],
        "rag_context": [],
        "is_rag_query": False,
        "policy_blocked": False,
        "login_required": False,
        "needs_staff_review": False,
        "guardrails": {"pii_detected_and_masked": detected, "masked_pii_types": types},
        "user_role": state.get("user_role", "guest"),
        "remaining_guest_messages": max(0, 5 - state.get("guest_turn_count", 0)),
    }
