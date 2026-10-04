from __future__ import annotations

import logging
import time
from hashlib import sha256
from uuid import uuid4

from langgraph.graph import END, StateGraph

from src.agents.cardd_evidence import missing_fields_for_state
from src.agents.context_manager import PROMPT_DIR
from src.agents.guardrails import is_hitl_mandatory
from src.agents.nodes.cardd_review_node import cardd_review_node
from src.agents.nodes.case_brief_node import case_brief_node
from src.agents.nodes.clarify_node import clarify_node
from src.agents.nodes.general_node import general_node
from src.agents.nodes.intake_node import intake_node
from src.agents.nodes.rag_node import rag_node
from src.agents.nodes.safety_node import safety_node
from src.agents.nodes.triage_node import classify_request_kind, triage_node
from src.agents.state import AgentState
from src.services.tracer import record_trace_step, sanitized_snapshot

logger = logging.getLogger(__name__)


def route_after_safety(state: AgentState) -> str:
    if state.get("is_critical") or state.get("policy_blocked"):
        return "case_brief"
    if state.get("login_required"):
        return END
    text = state.get('latest_user_message','')
    fresh = state.get('cardd_new_input') or state.get('cardd_confirmation_changed')
    foreign = any(word in text.casefold() for word in ('hyundai','tesla','máy bay','thời tiết'))
    if fresh and classify_request_kind(text) not in ('faq','complaint') and not foreign:
        return 'cardd_review'
    return "triage"


def route_after_triage(state: AgentState) -> str:
    if state.get("intent") == "Out_of_Scope":
        return END
    if state.get("is_general_query"):
        return "general"
    if state.get("is_rag_query"):
        return "rag"
    if state.get("confidence_score", 0) < 0.60:
        return "case_brief"
    if missing_fields_for_state(state):
        return "clarify"
    return "case_brief"


def traced(name, node):
    async def wrapped(state: AgentState):
        started = time.perf_counter()
        output = await node(state)
        if name == "intake":
            output.setdefault("session_id", state.get("session_id") or f"ephemeral-{uuid4().hex}")
        if name == "triage" and not output.get("is_rag_query") and not output.get("is_general_query") and output.get("intent") != "Out_of_Scope":
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
                    "latency_s": time.perf_counter() - started,
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
        ("cardd_review", cardd_review_node),
        ("triage", triage_node),
        ("clarify", clarify_node),
        ("rag", rag_node),
        ("general", general_node),
        ("case_brief", case_brief_node),
    ):
        workflow.add_node(name, traced(name, node))
    workflow.set_entry_point("intake")
    workflow.add_edge("intake", "safety")
    workflow.add_conditional_edges(
        "safety", route_after_safety, {"triage": "triage", 'cardd_review':'cardd_review', "case_brief": "case_brief", END: END}
    )
    workflow.add_conditional_edges('cardd_review',lambda s:s.get('cardd_review_action','done'),
        {'done':END,'triage':'triage','clarify':'clarify','case_brief':'case_brief'})
    workflow.add_conditional_edges(
        "triage", route_after_triage, {"general": "general", "rag": "rag", "clarify": "clarify", "case_brief": "case_brief", END: END}
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
    workflow.add_edge("general", END)
    return workflow.compile()


agent = build_graph()
