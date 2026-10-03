from __future__ import annotations

from src.agents.context_manager import load_prompt
from src.agents.guardrails import check_missing_fields
from src.agents.state import AgentState

LABELS = {
    "vehicle_model": "dòng xe",
    "station_location": "vị trí trạm hoặc khu vực (có thể bỏ qua)",
    "error_code": "mã lỗi hoặc đèn báo",
    "warning_symbol": "đèn hoặc biểu tượng cảnh báo",
    "operational_status": "xe còn di chuyển/khởi động được không",
    "showroom_dealer": "đại lý hoặc điểm dịch vụ",
    "complaint_summary": "nội dung phản ánh",
    "topic": "chủ đề cần hỗ trợ",
}


async def clarify_node(state: AgentState) -> dict:
    load_prompt("clarify")
    missing = check_missing_fields(state.get("intent"), state.get("captured_fields", {}))
    turn = state.get("clarification_turn", 0)
    flags = dict(state.get("guardrails", {}))
    if turn >= 2:
        flags["clarification_limit_reached"] = True
        return {
            "missing_fields": missing,
            "ticket_status": "Needs Information",
            "needs_staff_review": True,
            "guardrails": flags,
        }
    question = "Quý khách cho biết thêm " + ", ".join(LABELS.get(f, f) for f in missing) + " được không?"
    return {
        "missing_fields": missing,
        "clarification_turn": turn + 1,
        "response_type": "CLARIFICATION",
        "response": question,
        "final_response": question,
        "suggested_replies": ["VF3", "VF5", "VF8", "Không biết / bỏ qua"],
        "needs_staff_review": True,
        "guardrails": flags,
    }
