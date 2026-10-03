from __future__ import annotations

import logging
from hashlib import sha256
from uuid import uuid4

from langgraph.graph import END, StateGraph

from src.agents.context_manager import PROMPT_DIR
from src.agents.guardrails import check_missing_fields, is_hitl_mandatory
from src.agents.nodes.case_brief_node import case_brief_node
from src.agents.nodes.clarify_node import clarify_node
from src.agents.nodes.intake_node import intake_node
from src.agents.nodes.rag_node import rag_node
from src.agents.nodes.safety_node import safety_node
from src.agents.nodes.triage_node import triage_node
from src.agents.state import AgentState
from src.services.tracer import record_trace_step, sanitized_snapshot

logger = logging.getLogger(__name__)


def route_after_safety(state: AgentState) -> str:
    if state.get("is_critical") or state.get("policy_blocked"):
        return "case_brief"
    if state.get("login_required"):
        return END
    return "triage"


def route_after_triage(state: AgentState) -> str:
    if state.get("intent") == "Out_of_Scope":
        return END
    if state.get("is_rag_query"):
        return "rag"
    if state.get("confidence_score", 0) < 0.60:
        return "case_brief"
    if check_missing_fields(state.get("intent"), state.get("captured_fields", {})):
        return "clarify"
    return "case_brief"


def traced(name, node):
    async def wrapped(state: AgentState):
        output = await node(state)
        if name == "intake":
            output.setdefault("session_id", state.get("session_id") or f"ephemeral-{uuid4().hex}")
        if name == "triage" and not output.get("is_rag_query") and output.get("intent") != "Out_of_Scope":
            output["needs_staff_review"] = is_hitl_mandatory(
                intent=output.get("intent"),
                priority=output.get("priority", "MEDIUM"),
                confidence_score=output.get("confidence_score", 0),
                is_critical=state.get("is_critical", False),
            )
        combined = {**state, **output}
        try:
            record_trace_step(
                combined["session_id"],
                combined.get("turn", 0),
                "node",
                name,
                combined.get("response_type", name),
                metadata={
                    "input": sanitized_snapshot(state),
                    "output": sanitized_snapshot(output),
                    "tool_call": "vinfast_manual_search" if name == "rag" else None,
                    "prompt_versions": {p.name: sha256(p.read_bytes()).hexdigest() for p in PROMPT_DIR.glob("*.md")},
                },
            )
        except Exception:
            logger.warning("Local trace write failed for node %s", name)
        return output

    return wrapped


def build_graph():
    workflow = StateGraph(AgentState)
    for name, node in (
        ("intake", intake_node),
        ("safety", safety_node),
        ("triage", triage_node),
        ("clarify", clarify_node),
        ("rag", rag_node),
        ("case_brief", case_brief_node),
    ):
        workflow.add_node(name, traced(name, node))
    workflow.set_entry_point("intake")
    workflow.add_edge("intake", "safety")
    workflow.add_conditional_edges(
        "safety", route_after_safety, {"triage": "triage", "case_brief": "case_brief", END: END}
    )
    workflow.add_conditional_edges(
        "triage", route_after_triage, {"rag": "rag", "clarify": "clarify", "case_brief": "case_brief", END: END}
    )
    workflow.add_conditional_edges(
        "clarify",
        lambda s: "case_brief" if s.get("ticket_status") == "Needs Information" else END,
        {"case_brief": "case_brief", END: END},
    )
    workflow.add_conditional_edges(
        "rag", lambda s: "case_brief" if s.get("is_no_source") else END, {"case_brief": "case_brief", END: END}
    )
    workflow.add_edge("case_brief", END)
    return workflow.compile()


agent = build_graph()
