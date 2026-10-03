from __future__ import annotations

from pydantic import BaseModel, Field

from src.agents.guardrails import STANDARD_SAFE_GUIDANCE, check_missing_fields, sanitize_pii
from src.agents.state import AgentState
from src.services.agent_llm import structured_call

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
    routing = "emergency_rescue" if state.get("is_critical") else ROUTING_TARGETS.get(intent, "customer_relations")
    summary = state.get("latest_user_message", "")
    if not state.get("is_critical") and not state.get("policy_blocked"):
        generated = await structured_call(state, "case_brief", BriefSummary)
        if generated:
            summary = generated.summary
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
    missing = check_missing_fields(intent, facts)
    status = "Needs Information" if missing and state.get("clarification_turn", 0) >= 2 else "Staff Reviewing"
    guest = state.get("user_role", "guest") != "customer"
    # Only the bridge can claim successful case creation after its DB transaction.
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
        "response_type": state["response_type"]
        if state.get("is_critical") or state.get("policy_blocked")
        else "LOGIN_REQUIRED"
        if guest
        else "CASE_CREATED",
        "response": reply,
        "final_response": reply,
        "safe_guidance": state.get("safe_guidance") if state.get("is_critical") else STANDARD_SAFE_GUIDANCE,
    }
