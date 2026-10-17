from __future__ import annotations

from src.agents.context_manager import resolve_policy_conflict
from src.agents.guardrails import EMERGENCY_SAFE_GUIDANCE, evaluate_hard_safety, evaluate_hazardous_intervention
from src.agents.state import AgentState
from src.services.chat_normalization import clarification_for


async def safety_node(state: AgentState) -> dict:
    text = state.get("latest_user_message", state.get("query", ""))
    critical, trigger, priority = evaluate_hard_safety(text)
    flags = dict(state.get("guardrails", {}))
    if critical:
        flags.update(hard_safety_triggered=True, safety_rule_name=trigger)
        return {
            "is_critical": True,
            "safety_trigger": trigger,
            "priority": "CRITICAL",
            "intent": "Service/Incident",
            "response_type": "EMERGENCY_ALERT",
            "response": EMERGENCY_SAFE_GUIDANCE,
            "final_response": EMERGENCY_SAFE_GUIDANCE,
            "safe_guidance": EMERGENCY_SAFE_GUIDANCE,
            "routing": "emergency_rescue",
            "needs_staff_review": True,
            "guardrails": flags,
        }
    if resolve_policy_conflict(text) or evaluate_hazardous_intervention(text)[0]:
        reply = "Tôi không thể hướng dẫn can thiệp pin cao áp, vô hiệu hóa an toàn hoặc vượt rào bảo mật. Quý khách vui lòng liên hệ chuyên viên VinFast."
        return {
            "is_critical": False,
            "safety_trigger": None,
            "priority": "HIGH",
            "policy_blocked": True,
            "response_type": "SAFETY_REFUSAL",
            "intent": "Service/Incident",
            "response": reply,
            "final_response": reply,
            "needs_staff_review": True,
            "routing": "customer_relations",
            "guardrails": flags,
        }
    if state.get("user_role") == "guest" and state.get("guest_turn_count", 0) > 5:
        reply = "Quý khách đã dùng hết 5 lượt trải nghiệm. Vui lòng đăng nhập để tiếp tục."
        return {
            "is_critical": False,
            "priority": priority,
            "safety_trigger": None,
            "login_required": True,
            "response_type": "LOGIN_REQUIRED",
            "response": reply,
            "final_response": reply,
        }
    if state.get('normalization_needs_confirmation'):
        reply = clarification_for(text)
        return {'is_critical': False, 'safety_trigger': None, 'priority': priority,
                'response_type': 'CLARIFICATION', 'response': reply, 'final_response': reply,
                'needs_staff_review': False, 'case_brief': None, 'case_id': None, 'guardrails': flags}
    return {"is_critical": False, "safety_trigger": trigger, "priority": priority, "guardrails": flags}
