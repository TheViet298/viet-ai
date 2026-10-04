"""Deterministic photo review, downstream of hard safety and outside model inference."""

from src.agents.cardd_evidence import CONFIRM, REJECT, evidence_for_turn, evidence_summary, missing_fields_for_state
from src.agents.state import AgentState


async def cardd_review_node(state: AgentState) -> dict:
    record = evidence_for_turn(state)
    if not record:
        return {"cardd_review_action": "triage"}
    output = {
        "intent": "Service/Incident",
        "priority": state.get("priority", "MEDIUM"),
        "confidence_score": 0.90,
        "is_rag_query": False,
        "is_general_query": False,
        "needs_staff_review": True,
        "cardd_review_action": "done",
    }
    if record["confirmation"] == "confirmed":
        combined = {**state, **output}
        missing = missing_fields_for_state(combined)
        output.update(missing_fields=missing, cardd_review_action="clarify" if missing else "case_brief")
        return output
    if record["confirmation"] == "rejected":
        reply = (
            "Đã ghi nhận quý khách không xác nhận kết quả AI. Nếu cần hỗ trợ, vui lòng mô tả hư hại hoặc gửi ảnh khác."
        )
    elif state.get("clarification_turn", 0) >= 2:
        output.update(cardd_review_action="case_brief", ticket_status="Needs Information")
        output["guardrails"] = {**state.get("guardrails", {}), "clarification_limit_reached": True}
        return output
    else:
        reply = (
            evidence_summary(record)
            + " Quý khách vui lòng xác nhận ảnh có hư hại, hoặc mô tả tình trạng và chụp thêm ảnh cận cảnh."
        )
        output["clarification_turn"] = state.get("clarification_turn", 0) + 1
        output["suggested_replies"] = [CONFIRM, REJECT]
    output.update(response_type="CLARIFICATION", response=reply, final_response=reply)
    return output
