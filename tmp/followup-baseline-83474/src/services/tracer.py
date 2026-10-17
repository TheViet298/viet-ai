from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import BaseMessage

from src.agents.guardrails import sanitize_pii
from src.services.session_store import get_store


def sanitized_snapshot(value: Any) -> Any:
    if isinstance(value, BaseMessage):
        return {"type": value.type, "content": sanitize_pii(str(value.content))[0]}
    if isinstance(value, str):
        return sanitize_pii(value)[0]
    if isinstance(value, dict):
        return {k: sanitized_snapshot(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitized_snapshot(v) for v in value]
    return value


def record_trace_step(
    session_id: str,
    turn: int,
    kind: str,
    node: str,
    decision: str,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    cost: float | None = None,
    metadata: dict | None = None,
) -> dict:
    from src.services.observability import current_trace_id
    trace_id = current_trace_id()
    event = {
        "timestamp_ms": int(time.time() * 1000),
        "session_id": session_id,
        "turn": turn,
        "kind": kind,
        "node": node,
        "gate_decision": decision,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": cost,
        "metadata": sanitized_snapshot({**(metadata or {}), **({'correlation_id': trace_id} if trace_id else {})}),
    }
    get_store().record_trace(event)
    return event


def replay_session(session_id: str) -> list[dict]:
    """Recorded playback of node inputs/outputs, without calling live LLM/tools."""
    return get_store().replay(session_id)


def clear_traces() -> None:
    with get_store().connect() as db:
        db.execute("DELETE FROM agent_traces")
