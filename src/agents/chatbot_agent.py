from __future__ import annotations

import asyncio
import json
from uuid import uuid4
from weakref import WeakValueDictionary

from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from src.agents.cardd_evidence import make_cardd_signal
from src.agents.graph import agent
from src.agents.guardrails import evaluate_hard_safety, sanitize_pii
from src.services.agent_llm import structured_call
from src.services.memory_buffer import compact_memory
from src.services.observability import get_tracer_callbacks
from src.services.session_store import decode_state, encode_state, get_store, prepare_application_turn
from src.services.tracer import sanitized_snapshot

_LOCKS: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()


class MemorySummary(BaseModel):
    summary: str = Field(max_length=600)


async def process_chat_message(
    user_message: str,
    conversation_history: list[dict[str, str]] | None = None,
    clarification_turn: int = 0,
    captured_fields: dict | None = None,
    *,
    session_id: str | None = None,
    user_role: str = "guest",
    owner: str | None = None,
    client_context: dict | None = None,
    damage_evidence: dict | None = None,
    persist_business_case: bool = True,
    application_db=None,
    application_session_id: str | None = None,
) -> dict:
    if user_role not in {"guest", "customer", "staff"}:
        raise ValueError("Invalid role")
    if user_role != "guest" and not owner:
        raise PermissionError("Authenticated owner required")
    session_id = session_id or uuid4().hex
    owner = owner or f"guest:{session_id}"
    lock = _LOCKS.setdefault(session_id, asyncio.Lock())
    async with lock:
        if application_db is not None:
            from src.models.db_models import ChatSession
            if persist_business_case:
                raise ValueError('Application owns business case persistence')
            app_session = application_db.get(ChatSession, application_session_id or session_id)
            expected_owner = f'user:{owner}' if user_role != 'guest' else owner
            if not app_session or app_session.owner != expected_owner:
                raise PermissionError('Application session belongs to another principal')
            state = decode_state(json.dumps((app_session.memory_states or {}).get(session_id, {})))
            if not state.get('turn'):
                from src.config import get_settings
                if get_settings().database_url.startswith('sqlite:///'):
                    state = get_store().read_existing_state(session_id, owner, user_role) or state
            state.update(session_id=session_id, user_role=user_role)
            store, version = None, None
        else:
            store = get_store()
            critical = evaluate_hard_safety(user_message)[0]
            state, version = store.claim(session_id, owner, user_role, emergency=critical)
        if not state.get("turn"):
            state.update(
                clarification_turn=min(clarification_turn, 2), captured_fields=sanitized_snapshot(captured_fields or {})
            )
            state["messages"] = [
                HumanMessage(content=sanitize_pii(m.get("content", ""))[0])
                if m.get("role") == "user"
                else AIMessage(content=sanitize_pii(m.get("content", ""))[0])
                for m in (conversation_history or [])
            ]
        context = sanitized_snapshot(client_context or {})
        if context.get("reset_faq_context"):
            state["is_rag_query"] = False
        if context.get("vehicle_model"):
            state["vehicle_model"] = context["vehicle_model"]
        if context.get("vehicle_context"):
            state['pending_vehicle_context'] = context['vehicle_context']
        original_message = context.get("original_user_message") or user_message
        state.update(query=sanitize_pii(original_message)[0], latest_user_message=sanitize_pii(original_message)[0])
        # Server-side AI evidence only; never read this from arbitrary client_context.
        state['pending_cardd_signal'] = make_cardd_signal(damage_evidence,state.get('turn',0)+1) if damage_evidence is not None else None
        result = await agent.ainvoke(
            state,
            config={
                "callbacks": get_tracer_callbacks(session_id=session_id, user_id=owner),
                "metadata": {"session_id": session_id},
            },
        )
        if not persist_business_case:
            prepare_application_turn(result)
        result["messages"].append(AIMessage(content=result.get("response", "")))
        if compact_memory(result):
            buffer_summary = result['memory_summary']
            summary = (
                None
                if result.get("is_critical")
                else await structured_call({**result, "memory_summary": buffer_summary}, "memory", MemorySummary)
            )
            result["memory_summary"] = sanitize_pii(summary.summary if summary else buffer_summary)[0]
        if application_db is not None:
            # No commit here: messages, memory and request cache share the
            # transaction owned by run_chat_turn, including failure rollback.
            saved = result
            app_session.memory_states = {**(app_session.memory_states or {}), session_id: json.loads(encode_state(saved))}
            application_db.flush()
        else:
            saved = store.save_turn(session_id, owner, version, result, persist_business_case=persist_business_case)
        reply = saved.get("response", "")
        if saved.get("case_id") and saved.get("response_type") == "CASE_CREATED":
            reply += f"\n\nMã hồ sơ: {saved['case_id']}."
        return {
            "session_id": session_id,
            "reply": reply,
            "response": reply,
            "intent": saved.get("intent"),
            "priority": saved.get("priority", "MEDIUM"),
            "confidence_score": saved.get("confidence_score", 0),
            "needs_staff_review": saved.get("needs_staff_review", False),
            "is_safety_trigger": saved.get("is_critical", False),
            "is_no_source": saved.get("is_no_source", False),
            "retrieval_diagnostics": saved.get("retrieval_diagnostics", {}),
            "retrieval_status": saved.get("retrieval_status"),
            "citations": saved.get("rag_citations", []),
            "suggested_replies": saved.get("suggested_replies", []),
            "case_brief": saved.get("case_brief"),
            'visual_evidence':saved.get('cardd_evidence'),
            "case_id": saved.get("case_id"),
            "ticket_status": saved.get("ticket_status"),
            "response_type": saved.get("response_type"),
            "clarification_turn": saved.get("clarification_turn", 0),
            "max_clarification_turns": 2,
            "remaining_guest_messages": saved.get("remaining_guest_messages", 0),
            "login_required": saved.get("login_required", False),
            "routing": saved.get("routing"),
        }
