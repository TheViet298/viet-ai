from __future__ import annotations

import asyncio
from typing import TypeVar

from pydantic import BaseModel

from src.agents.context_manager import build_7_layer_context, load_prompt, trim_context_layers
from src.agents.state import AgentState
from src.config import get_settings
from src.services.tracer import record_trace_step, sanitized_snapshot

T = TypeVar("T", bound=BaseModel)


async def structured_call(state: AgentState, prompt: str, schema: type[T]) -> T | None:
    """Optional online generation; deterministic, safe fallback when unavailable."""
    settings = get_settings()
    if not settings.google_api_key or not settings.agent_llm_enabled:
        return None
    from src.services.llm import get_llm

    messages = trim_context_layers(build_7_layer_context(state, load_prompt(prompt)))
    try:
        result = await asyncio.wait_for(
            get_llm().with_structured_output(schema, include_raw=True).ainvoke(messages), timeout=8
        )
        raw = result.get("raw")
        usage = getattr(raw, "usage_metadata", None) or {}
        parsed = result.get("parsed")
        try:
            record_trace_step(
                state.get("session_id", "unspecified"),
                state.get("turn", 0),
                "llm",
                prompt,
                "parsed" if parsed else "fallback",
                tokens_in=usage.get("input_tokens"),
                tokens_out=usage.get("output_tokens"),
                metadata={
                    "model": settings.model_name,
                    "output": sanitized_snapshot(parsed.model_dump()) if isinstance(parsed, BaseModel) else None,
                },
            )
        except Exception:
            pass
        return parsed if isinstance(parsed, schema) else None
    except Exception:
        # Do not log exception payloads that may contain user data or API credentials.
        return None
