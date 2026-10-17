"""Seven layers; external prompt artifacts and bounded dynamic context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from src.agents.cardd_evidence import confirmed_cardd_context
from src.agents.state import AgentState

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_prompt(name: str) -> str:
    text = (PROMPT_DIR / f"{name}_prompt.md").read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip()


@dataclass
class ContextLayers:
    system_context: str
    policy_context: str
    task_context: str = ""
    user_context: str = ""
    memory_context: str = ""
    retrieval_context: str = ""
    tool_context: str = ""
    required_memory_context: str = ""


def build_7_layer_context(state: AgentState, task_objective: str, tool_outputs: str = "") -> ContextLayers:
    return ContextLayers(
        system_context=load_prompt("system"),
        policy_context=load_prompt("policy"),
        task_context=task_objective,
        user_context=str(
            {
                "role": state.get("user_role", "guest"),
                "model": state.get("vehicle_model"),
                "message": state.get("latest_user_message", state.get("query", "")),
            }
        ),
        memory_context=str(
            {
                "summary": state.get("memory_summary", ""),
                "summary_evidence": state.get('summary_evidence', []),
                "facts": state.get("captured_fields", {}),
                "clarification_turn": state.get("clarification_turn", 0),
                "intent": state.get("intent"),
                'conversation': state.get('conversation_context', {}),
                'reply_constraints': state.get('reply_constraints', {}),
            }
        ),
        retrieval_context="\n".join(
            f"[{c['source_id']}] {c.get('relevant_snippet', '')}" for c in state.get("rag_citations", [])
        ),
        tool_context='\n'.join(value for value in (tool_outputs,confirmed_cardd_context(state)) if value),
        required_memory_context=str({'facts': state.get('captured_fields', {}),
                                    'clarification_turn': state.get('clarification_turn', 0),
                                    'intent': state.get('intent'),
                                    'priority': state.get('priority'), 'case_id': state.get('case_id')}),
    )


def utf8_size(text: str) -> int:
    """Prompt storage budget in bytes, independent of provider token usage."""
    return len(text.encode("utf-8"))


def token_count(text: str) -> int:
    """Legacy alias: returns UTF-8 bytes, not LLM tokens."""
    return utf8_size(text)


def trim_context_layers(layers: ContextLayers, max_bytes: int = 8000, *, max_tokens: int | None = None) -> list[BaseMessage]:
    if max_tokens is not None:
        max_bytes = max_tokens  # Backward-compatible byte budget alias.
    dynamic = {k: getattr(layers, f"{k}_context") for k in ("tool", "retrieval", "memory", "task", "user")}
    pinned = f"{layers.system_context}\n\n{layers.policy_context}"
    if utf8_size(pinned) > max_bytes:
        raise ValueError("Context budget cannot fit pinned system and policy layers")

    def render() -> list[BaseMessage]:
        system = pinned + (f"\n\n[TASK]\n{dynamic['task']}" if dynamic["task"] else "")
        body = "\n\n".join(
            f"[{k.upper()} — DATA]\n{dynamic[k]}" for k in ("user", "memory", "retrieval", "tool") if dynamic[k]
        )
        if layers.required_memory_context:
            body += f'\n\n[REQUIRED MEMORY — DATA]\n{layers.required_memory_context}'
        return [SystemMessage(content=system), *([HumanMessage(content=body)] if body else [])]

    # Optional history must not evict the complete evidence used for grounding.
    for key in ("tool", "memory", "retrieval"):
        if sum(utf8_size(str(m.content)) for m in render()) <= max_bytes:
            break
        dynamic[key] = ""
    if sum(utf8_size(str(m.content)) for m in render()) > max_bytes:
        raise ValueError("Context budget cannot fit pinned layers and user question")
    return render()


def resolve_policy_conflict(user_query: str) -> bool:
    import re

    return bool(
        re.search(
            r"(?:tháo|mở|đấu|can thiệp).{0,40}(?:pin cao áp|pin cao thế|dây cao áp)|"
            r"(?:tắt|vô hiệu|bỏ).{0,20}(?:phanh|bảo vệ pin)|"
            r"(?:bỏ qua|ignore|jailbreak).{0,60}(?:quy định|quy tắc|chỉ dẫn|an toàn|instructions)|"
            r"(?:hack|phá khóa|bẻ khóa|mở khóa giới hạn)",
            user_query.lower(),
        )
    ) or bool(re.search(r"(?:tự đấu|đấu dây|can thiệp tăng).{0,60}(?:pin|công suất|cao áp)", user_query.lower()))


def apply_fact_recency_and_invalidation(
    current_facts: dict[str, Any], fact_history: list[dict[str, Any]], field: str, new_value: Any, provenance: str
) -> tuple[dict, list]:
    facts = dict(current_facts)
    history = [dict(item) for item in fact_history]
    timestamp = datetime.now(UTC).isoformat()
    if facts.get(field) == new_value:
        for item in history:
            if item['field'] == field and item['status'] == 'valid':
                item.update(last_seen_at=timestamp, last_seen_provenance=provenance)
        return facts, history
    now = datetime.now(UTC).isoformat()
    for item in history:
        if item["field"] == field and item["status"] == "valid":
            item.update(status="invalidated", valid_to=now)
    facts[field] = new_value
    history.append(
        {
            "field": field,
            "value": new_value,
            "provenance": provenance,
            "status": "valid",
            "valid_from": now,
            "valid_to": None,
            "last_seen_at": timestamp,
            "last_seen_provenance": provenance,
        }
    )
    return facts, history


def expire_dynamic_facts(facts: dict, history: list[dict], at: datetime | None = None) -> tuple[dict, list]:
    """Dynamic observations cannot be treated as current indefinitely."""
    at = at or datetime.now(UTC)
    facts, history = dict(facts), [dict(item) for item in history]
    for field, seconds in {'current_soc': 300, 'current_location': 900}.items():
        if field not in facts:
            continue
        observation = next((item for item in reversed(history) if item['field'] == field and item['status'] == 'valid'), None)
        try:
            seen = datetime.fromisoformat(observation.get('last_seen_at') or observation['valid_from']) if observation else None
            fresh = seen is not None and 0 <= (at - seen).total_seconds() < seconds
        except (ValueError, TypeError):
            fresh = False
        if not fresh:
            facts.pop(field, None)
            if observation:
                observation.update(status='expired', valid_to=at.isoformat())
    return facts, history
