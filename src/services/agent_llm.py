from __future__ import annotations

import asyncio
import time
from hashlib import sha256
from typing import TypeVar

from pydantic import BaseModel

from src.agents.context_manager import build_7_layer_context, load_prompt, trim_context_layers
from src.agents.state import AgentState
from src.config import get_settings
from src.services.tracer import record_trace_step, sanitized_snapshot
from src.services.observability import observation, current_trace_id

T = TypeVar("T", bound=BaseModel)
_circuits: dict[str, dict] = {}


def circuit_key() -> str:
    s = get_settings()
    key = s.openai_api_key if (s.model_name.startswith("gpt") or s.openai_api_key) else s.google_api_key
    return sha256((str(key) + str(getattr(s, "model_name", "model"))).encode()).hexdigest()


def open_circuit() -> None:
    _circuits[circuit_key()] = {"until": time.monotonic() + get_settings().agent_circuit_cooldown_s, "probe": False}


def reset_circuits() -> None:
    _circuits.clear()


def classify_provider_error(error: Exception) -> str:
    # Only the category leaves this function; never persist exception payloads.
    if isinstance(error, TimeoutError):
        return "timeout"
    text = str(error).casefold()
    if any(term in text for term in ["429", "quota", "resource_exhausted", "rate limit"]):
        return "rate_limited"
    if any(term in text for term in ["api_key_invalid", "api key not valid", "unauthenticated", "401", "403"]):
        return "auth_error"
    return "provider_error"


def record_outcome(state: AgentState, prompt: str, decision: str, usage: dict | None = None, parsed=None) -> None:
    usage = usage or {}
    state["last_llm_outcome"] = decision
    with observation('llm.outcome', metadata={'outcome': decision, 'prompt_name': prompt}):
        pass
    try:
        record_trace_step(
            state.get("session_id", "unspecified"), state.get("turn", 0), "llm", prompt, decision,
            tokens_in=usage.get("input_tokens"), tokens_out=usage.get("output_tokens"),
            metadata={"model": getattr(get_settings(), "model_name", "gemini"), "output": sanitized_snapshot(parsed.model_dump()) if isinstance(parsed, BaseModel) else None},
        )
    except Exception:
        pass


async def structured_call(state: AgentState, prompt: str, schema: type[T], *, callbacks=None) -> T | None:
    """Optional online generation; deterministic, safe fallback when unavailable."""
    settings = get_settings()
    is_openai = bool(settings.model_name and settings.model_name.lower().startswith("gpt")) or bool(settings.openai_api_key)
    has_api_key = bool(settings.openai_api_key) if is_openai else bool(settings.google_api_key)
    if not has_api_key or not settings.agent_llm_enabled:
        return None
    budget = state.setdefault("llm_budget", {"deadline": time.monotonic() + settings.agent_turn_timeout_s, "attempts": 0})
    remaining = budget["deadline"] - time.monotonic()
    if budget["attempts"] >= 1 or remaining <= 0:
        record_outcome(state, prompt, "budget_exhausted")
        return None
    key = circuit_key()
    circuit = _circuits.get(key)
    if circuit and (time.monotonic() < circuit["until"] or circuit["probe"]):
        record_outcome(state, prompt, "circuit_open")
        return None
    if circuit:
        circuit["probe"] = True
    budget["attempts"] += 1
    from src.services.llm import get_llm

    try:
        layers = build_7_layer_context(state, load_prompt(prompt))
        try:
            messages = trim_context_layers(layers, max_bytes=settings.agent_context_max_bytes)
        except ValueError:
            record_outcome(state, prompt, "context_budget_exceeded")
            return None
        if layers.retrieval_context and not any(layers.retrieval_context in str(m.content) for m in messages):
            record_outcome(state, prompt, "context_budget_exceeded")
            return None
        result = await asyncio.wait_for(
            get_llm().with_structured_output(schema, include_raw=True).ainvoke(
                messages, **({'config': {'callbacks': callbacks}} if callbacks is not None else {})
            ), timeout=min(remaining, settings.agent_llm_timeout_s)
        )
        raw = result.get("raw")
        usage = getattr(raw, "usage_metadata", None) or {}
        parsed = result.get("parsed")
        if circuit and _circuits.get(key) is circuit:
            _circuits.pop(key, None)
        record_outcome(state, prompt, "parsed" if isinstance(parsed, schema) else "parse_error", usage, parsed)
        return parsed if isinstance(parsed, schema) else None
    except asyncio.CancelledError:
        if circuit and _circuits.get(key) is circuit:
            open_circuit()
        record_outcome(state, prompt, "cancelled")
        raise
    except Exception as error:
        decision = classify_provider_error(error)
        if decision in {"rate_limited", "auth_error"} or circuit:
            open_circuit()
        record_outcome(state, prompt, decision)
        # Do not log exception payloads that may contain user data or API credentials.
        return None
