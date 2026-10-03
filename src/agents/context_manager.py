"""Seven layers; external prompt artifacts and bounded dynamic context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

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
                "facts": state.get("captured_fields", {}),
                "clarification_turn": state.get("clarification_turn", 0),
                "intent": state.get("intent"),
            }
        ),
        retrieval_context="\n".join(
            f"[{c['source_id']}] {c.get('relevant_snippet', '')}" for c in state.get("rag_citations", [])
        ),
        tool_context=tool_outputs,
    )


def token_count(text: str) -> int:
    # Conservative UTF-8 byte budget; never undercounts a byte-level tokenizer.
    return len(text.encode("utf-8"))


def trim_context_layers(layers: ContextLayers, max_tokens: int = 8000) -> list[BaseMessage]:
    dynamic = {k: getattr(layers, f"{k}_context") for k in ("tool", "retrieval", "memory", "user", "task")}
    pinned = f"{layers.system_context}\n\n{layers.policy_context}"
    if token_count(pinned) > max_tokens:
        raise ValueError("Context budget cannot fit pinned system and policy layers")

    def render() -> list[BaseMessage]:
        system = pinned + (f"\n\n[TASK]\n{dynamic['task']}" if dynamic["task"] else "")
        body = "\n\n".join(
            f"[{k.upper()} — DATA]\n{dynamic[k]}" for k in ("user", "memory", "retrieval", "tool") if dynamic[k]
        )
        return [SystemMessage(content=system), *([HumanMessage(content=body)] if body else [])]

    for key in dynamic:
        if sum(token_count(str(m.content)) for m in render()) <= max_tokens:
            break
        dynamic[key] = ""
    return render()


def resolve_policy_conflict(user_query: str) -> bool:
    import re

    return bool(
        re.search(
            r"(?:tháo|mở|đấu|can thiệp).{0,40}(?:pin cao áp|pin cao thế|dây cao áp)|"
            r"(?:tắt|vô hiệu|bỏ).{0,20}(?:phanh|bảo vệ pin)|"
            r"(?:bỏ qua|ignore|jailbreak).{0,60}(?:quy định|quy tắc|an toàn|instructions)|"
            r"(?:hack|phá khóa|bẻ khóa|mở khóa giới hạn)",
            user_query.lower(),
        )
    ) or bool(re.search(r"(?:tự đấu|đấu dây|can thiệp tăng).{0,60}(?:pin|công suất|cao áp)", user_query.lower()))


def apply_fact_recency_and_invalidation(
    current_facts: dict[str, Any], fact_history: list[dict[str, Any]], field: str, new_value: Any, provenance: str
) -> tuple[dict, list]:
    facts = dict(current_facts)
    history = [dict(item) for item in fact_history]
    if facts.get(field) == new_value:
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
        }
    )
    return facts, history
