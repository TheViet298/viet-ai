"""Accepted web turns share one snapshot and transaction with their messages."""
import json
from datetime import UTC, datetime

from langchain_core.messages import AIMessage, HumanMessage

from src.agents.context_manager import apply_fact_recency_and_invalidation, expire_dynamic_facts
from src.services.memory_buffer import compact_memory
from src.services.session_store import decode_state, encode_state


def accept_application_memory(session, session_id: str, text: str, data, context: dict, before_turn: int) -> None:
    from src.agents.nodes.triage_node import extract_fields
    from src.services.chat_classification import denied_reports

    state = decode_state(json.dumps((session.memory_states or {}).get(session_id, {})))
    if context.get('scope_changed'):
        state['messages'] = state['messages'][-2:] if state.get('turn', 0) > before_turn else []
    if state.get('turn', 0) == before_turn:
        state['messages'] += [HumanMessage(content=text), AIMessage(content=data.message)]
        state['turn'] = before_turn + 1
    else:
        # Persist the response actually delivered, including web normalization.
        state['messages'][-1] = AIMessage(content=data.message)
    facts, history = expire_dynamic_facts(state.get('captured_fields', {}), state.get('fact_history', []))
    invalidated = set(facts) if context.get('scope_changed') else set()
    for denied in denied_reports(text):
        for field, value in extract_fields(denied, asserted_only=False).items():
            if str(facts.get(field, '')).casefold() == value.casefold():
                invalidated.add(field)
    if invalidated:
        facts = {k: v for k, v in facts.items() if k not in invalidated}
        for item in history:
            if item['field'] in invalidated and item['status'] == 'valid':
                item.update(status='invalidated', valid_to=datetime.now(UTC).isoformat())
    observed = extract_fields(text)
    observed.pop('vehicle_model', None)
    model = context.get('incident_model') if context.get('is_incident') else context.get('owned_model')
    if model:
        observed['vehicle_model'] = model
    for field, value in observed.items():
        facts, history = apply_fact_recency_and_invalidation(facts, history, field, value, f"user:turn:{state['turn']}")
    state.update(schema_version=2, session_id=session_id, latest_user_message=text, response=data.message,
                 vehicle_context=context, captured_fields=facts, fact_history=history,
                 case_id=data.case_id, priority=data.priority, clarification_turn=data.clarification_turn or 0)
    if context.get('scope_changed'):
        state['memory_summary'] = ''
        state['summary_evidence'] = []
    compact_memory(state)
    session.memory_states = {**(session.memory_states or {}), session_id: json.loads(encode_state(state))}
