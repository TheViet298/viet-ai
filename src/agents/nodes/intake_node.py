from __future__ import annotations

import time

from langchain_core.messages import HumanMessage, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from src.agents.cardd_evidence import consume_cardd_signal
from src.agents.context_manager import apply_fact_recency_and_invalidation, expire_dynamic_facts
from src.agents.guardrails import sanitize_pii
from src.agents.nodes.triage_node import extract_fields
from src.agents.state import AgentState
from src.config import get_settings
from src.services.agent_llm import new_turn_budget
from src.services.chat_classification import denied_reports
from src.services.chat_normalization import normalize_chat_text
from src.services.followup_context import resolve_faq_followup
from src.services.tracer import sanitized_snapshot
from src.services.vehicle_context import resolve_vehicle_context


async def intake_node(state: AgentState) -> dict:
    text, detected, types = sanitize_pii((state.get("latest_user_message") or state.get("query") or "").strip())
    text = normalize_chat_text(text)
    observed_text = '' if state.get('normalization_needs_confirmation') else text
    facts = sanitized_snapshot(state.get("captured_fields", {}))
    context = dict(state.get('pending_vehicle_context') or resolve_vehicle_context(observed_text, state.get("vehicle_context")))
    previous_scope = (state.get('vehicle_context') or {}).get('incident_scope', 1)
    if context.get('incident_scope', 1) != previous_scope:
        context['scope_changed'] = True
    if context["is_incident"] and not context["incident_model"]:
        facts.pop("vehicle_model", None)
    history = sanitized_snapshot(state.get("fact_history", []))
    facts, history = expire_dynamic_facts(facts, history)
    invalidated = set(facts) if context.get('scope_changed') else set()
    for denied in denied_reports(observed_text):
        for field, value in extract_fields(denied, asserted_only=False).items():
            if str(facts.get(field, '')).casefold() == value.casefold():
                invalidated.add(field)
    if invalidated:
        from datetime import UTC, datetime
        timestamp = datetime.now(UTC).isoformat()
        facts = {k: v for k, v in facts.items() if k not in invalidated}
        for item in history:
            if item['field'] in invalidated and item['status'] == 'valid':
                item.update(status='invalidated', valid_to=timestamp)
    extracted = extract_fields(observed_text)
    extracted.pop("vehicle_model", None)
    confirmed_model = context["incident_model"] if context["is_incident"] else context["owned_model"]
    if confirmed_model:
        extracted["vehicle_model"] = confirmed_model
    for field, value in extracted.items():
        facts, history = apply_fact_recency_and_invalidation(
            facts, history, field, value, f"user:turn:{state.get('turn', 0) + 1}"
        )
    faq_query = resolve_faq_followup(text, state)
    return {
        **({'case_id': None, 'clarification_turn': 0, 'memory_summary': ''} if context.get('scope_changed') else {}),
        **consume_cardd_signal({**state, 'cardd_evidence': None} if context.get('scope_changed') else state, state.get('turn',0)+1, text),
        "llm_budget": state.get('llm_budget') if state.get('llm_budget') is not None else new_turn_budget(time.monotonic() + get_settings().agent_turn_timeout_s),
        "retrieval_diagnostics": {},
        "answer_status": None,
        "query": text,
        "resolved_query": (state.get('turn_understanding') or {}).get('resolved_query') or (faq_query if faq_query != text else context["resolved_query"]),
        "vehicle_context": context,
        'pending_vehicle_context': None,
        "latest_user_message": text,
        "messages": [*([RemoveMessage(id=REMOVE_ALL_MESSAGES)] if context.get('scope_changed') else []),
                     HumanMessage(content=state.get('original_user_message') or text)],
        "captured_fields": facts,
        "vehicle_model": context["models"][0] if len(context["models"]) == 1 else None,
        "fact_history": history,
        "memory_summary": '' if context.get('scope_changed') else sanitize_pii(state.get("memory_summary", ""))[0],
        'summary_evidence': [] if context.get('scope_changed') else state.get('summary_evidence', []),
        "turn": state.get("turn", 0) + 1,
        "clarification_turn": 0 if context.get('scope_changed') else max(0, min(state.get("clarification_turn", 0), 2)),
        "max_clarification_turns": 2,
        "suggested_replies": [],
        "case_brief": None,
        "response": "",
        "final_response": "",
        "is_no_source": False,
        "rag_citations": [],
        "rag_context": [],
        "answer_claims": [],
        "is_rag_query": False,
        "policy_blocked": False,
        "login_required": False,
        "needs_staff_review": False,
        "guardrails": {"pii_detected_and_masked": detected, "masked_pii_types": types},
        "user_role": state.get("user_role", "guest"),
        "remaining_guest_messages": max(0, 5 - state.get("guest_turn_count", 0)),
    }
