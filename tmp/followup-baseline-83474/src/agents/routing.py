from __future__ import annotations

from dataclasses import dataclass

from src.agents.state import AgentState


@dataclass(frozen=True)
class RoutingDecision:
    target: str
    reason_code: str


def decide_routing(state: AgentState) -> RoutingDecision:
    text = state.get("latest_user_message", state.get("query", "")).lower()
    if state.get("is_critical"):
        return RoutingDecision("emergency_rescue", "critical")
    if state.get("policy_blocked"):
        return RoutingDecision("customer_relations", "policy_refusal")
    if not state.get("is_rag_query") and (
        any(term in text for term in ["kéo xe", "cần cứu hộ", "cứu tôi", "hết pin trên cao tốc"])
        or ("cao tốc" in text and any(term in text for term in ["sắp hết", "4%", "hết pin"]))
        or ("trên cầu" in text and any(term in text for term in ["xì lốp", "không có lốp dự phòng"]))
        or ("vô lăng" in text and "không quay được" in text)
    ):
        return RoutingDecision("emergency_rescue", "rescue_requested")
    if state.get("intent") == "Service/Incident" and not state.get("is_rag_query") and any(
        term in text for term in ["bật nguồn không lên", "không lên nguồn", "tối thui", "tối đen", "tại nhà", "mưa to", "mobile service"]
    ):
        return RoutingDecision("mobile_service", "onsite_support")
    if state.get("intent") == "Charging/Battery" and any(term in text for term in ["gãy", "vỡ", "hỏng nắp"]):
        return RoutingDecision("service_center", "charging_hardware_damage")
    targets = {
        "Charging/Battery": "charging_support",
        "Service/Incident": "service_center",
        "Complaint/Feedback": "customer_relations",
        "Sales/General Info": "sales_support",
        "Out_of_Scope": "sales_support" if any(term in text for term in ["tesla", "hyundai"]) else "customer_relations",
    }
    return RoutingDecision(targets.get(state.get("intent"), "customer_relations"), "intent_default")
