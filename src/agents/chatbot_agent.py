from __future__ import annotations

import asyncio
from uuid import uuid4
from weakref import WeakValueDictionary

from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from src.agents.context_manager import token_count
from src.agents.graph import agent
from src.agents.guardrails import evaluate_hard_safety, sanitize_pii
from src.services.agent_llm import structured_call
from src.services.observability import get_tracer_callbacks
from src.services.session_store import get_store
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
) -> dict:
    if user_role not in {"guest", "customer", "staff"}:
        raise ValueError("Invalid role")
    if user_role != "guest" and not owner:
        raise PermissionError("Authenticated owner required")
    session_id = session_id or uuid4().hex
    owner = owner or f"guest:{session_id}"
    lock = _LOCKS.setdefault(session_id, asyncio.Lock())
    async with lock:
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
            state.setdefault("captured_fields", {}).setdefault("vehicle_model", context["vehicle_model"])
        state.update(query=sanitize_pii(user_message)[0], latest_user_message=sanitize_pii(user_message)[0])
        result = await agent.ainvoke(
            state,
            config={
                "callbacks": get_tracer_callbacks(session_id=session_id, user_id=owner),
                "metadata": {"session_id": session_id},
            },
        )
        result["messages"].append(AIMessage(content=result.get("response", "")))
        if len(result["messages"]) > 10 or sum(token_count(str(m.content)) for m in result["messages"]) > 8000:
            old = result["messages"][:-6]
            buffer_summary = (result.get("memory_summary", "") + "\n" + "\n".join(str(m.content)[:200] for m in old))[
                -1800:
            ]
            summary = (
                None
                if result.get("is_critical")
                else await structured_call({**result, "memory_summary": buffer_summary}, "memory", MemorySummary)
            )
            result["memory_summary"] = sanitize_pii(summary.summary if summary else buffer_summary)[0]
            result["messages"] = result["messages"][-6:]
        saved = store.save_turn(session_id, owner, version, result)
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
            "citations": saved.get("rag_citations", []),
            "suggested_replies": saved.get("suggested_replies", []),
            "case_brief": saved.get("case_brief"),
            "case_id": saved.get("case_id"),
            "ticket_status": saved.get("ticket_status"),
            "response_type": saved.get("response_type"),
            "clarification_turn": saved.get("clarification_turn", 0),
            "max_clarification_turns": 2,
            "remaining_guest_messages": saved.get("remaining_guest_messages", 0),
            "login_required": saved.get("login_required", False),
            "routing": saved.get("routing"),
        }
