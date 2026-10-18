from __future__ import annotations

import re

from pydantic import BaseModel, Field

from src.agents.cardd_evidence import evidence_for_turn, evidence_summary, missing_fields_for_state
from src.agents.guardrails import STANDARD_SAFE_GUIDANCE, sanitize_pii
from src.agents.routing import decide_routing
from src.agents.state import AgentState

ROUTING_TARGETS = {
    "Charging/Battery": "charging_support",
    "Service/Incident": "service_center",
    "Complaint/Feedback": "customer_relations",
    "Sales/General Info": "sales_support",
}


class BriefSummary(BaseModel):
    summary: str = Field(min_length=1, max_length=1000)


async def case_brief_node(state: AgentState) -> dict:
    facts = state.get("captured_fields", {})
    intent = state.get("intent") or "Service/Incident"
    routing = decide_routing(state).target
    summary = state.get("latest_user_message", "")
    visual = evidence_for_turn(state) if intent == 'Service/Incident' else None
    if visual and visual['status']!='not_requested':
        summary += '\n' + evidence_summary(visual)
    # Factual template brief keeps the only foreground model call for uncertain
    # classification or grounded answering, and never delays emergency output.
    brief = {
        "summary": summary,
        "vehicle_model": facts.get("vehicle_model", state.get("vehicle_model")),
        "station_location": facts.get("station_location"),
        "charger_id": facts.get("charger_id"),
        "error_code": facts.get("error_code"),
        "warning_symbol": facts.get("warning_symbol"),
        "captured_fields": facts,
        "suggested_action": f"Nhân viên kiểm tra và tiếp nhận tại {routing}.",
        "confidence_score": state.get("confidence_score", 0.0),
        "is_edited_by_staff": False,
    }
    brief["summary"] = sanitize_pii(brief["summary"])[0]
    if visual:
        brief['visual_evidence'] = visual
    missing = missing_fields_for_state({**state,'intent':intent})
    status = "Needs Information" if missing and state.get("clarification_turn", 0) >= 2 else "Staff Reviewing"
    guest = state.get("user_role", "guest") != "customer"
    # Only the bridge can claim successful case creation after its DB transaction.
    if state.get("is_rag_query"):
        faq_note = 'Quý khách có thể liên hệ chuyên viên để đối chiếu; chat chưa xác nhận yêu cầu đã được chuyển hay có lịch phản hồi.'
        body = state.get('response', '')
        has_contact_guidance = re.search(r'quý khách (?:có thể|vui lòng) liên hệ (?:với )?chuyên viên', body.casefold())
        promises_handoff = re.search(r'\b(?:đã|sẽ)\s+(?:chuyển|gửi|điều phối|ghi nhận)', body.casefold())
        reply = body if has_contact_guidance and not promises_handoff else body + ('\n\n' + faq_note if body else faq_note)
    else:
        reply = "Đã ghi nhận yêu cầu để chuyên viên dịch vụ tiếp nhận. " + STANDARD_SAFE_GUIDANCE
        if guest:
            reply = "Đã ghi nhận sơ bộ yêu cầu. Quý khách vui lòng đăng nhập tài khoản Customer để lưu hồ sơ và theo dõi tiến độ."
        if state.get("is_critical") or state.get("policy_blocked"):
            reply = state.get("response", "") + ("\n\nVui lòng đăng nhập để lưu hồ sơ hỗ trợ." if guest else "")
        elif state.get("is_no_source"):
            reply = state.get("response", "") + "\n\n" + reply

    return {
        "case_brief": brief,
        "ticket_status": status,
        "needs_staff_review": True,
        "routing": routing,
        "login_required": guest,
        "response_type": "FAQ_ANSWER"
        if state.get("is_rag_query") and not state.get("is_no_source")
        else state["response_type"]
        if state.get("is_critical") or state.get("policy_blocked")
        else "LOGIN_REQUIRED"
        if guest
        else "CASE_CREATED",
        "response": reply,
        "final_response": reply,
        "safe_guidance": state.get("safe_guidance") if state.get("is_critical") else None if state.get("is_rag_query") else STANDARD_SAFE_GUIDANCE,
    }
