from __future__ import annotations

from src.agents.cardd_evidence import missing_fields_for_state
from src.agents.context_manager import load_prompt
from src.agents.state import AgentState

FIELD_SPECIFIC_QUESTIONS: dict[str, str] = {
    "vehicle_model": "Anh/chị vui lòng cho biết mình đang sử dụng dòng xe VinFast nào (ví dụ: VF3, VF5, VF8) ạ?",
    "station_location": "Anh/chị đang ở vị trí trạm sạc nào hoặc trụ số mấy ạ?",
    "error_code": "Trên màn hình táp-lô hoặc trụ sạc có báo mã lỗi cụ thể nào (ví dụ: CC01, 0x41) hay đèn nháy đỏ không ạ?",
    "warning_symbol": "Trên màn hình táp-lô đang sáng biểu tượng hay đèn cảnh báo nào ạ?",
    "operational_status": "Hiện tại xe có còn di chuyển hoặc khởi động được không ạ?",
    "showroom_dealer": "Anh/chị đang liên hệ showroom hoặc xưởng dịch vụ nào của VinFast ạ?",
    "complaint_summary": "Anh/chị vui lòng chia sẻ thêm chi tiết nội dung cần phản ánh để em hỗ trợ nhé ạ.",
    "topic": "Anh/chị đang quan tâm đến chủ đề hoặc dịch vụ cụ thể nào ạ?",
}

FIELD_DESCRIPTIONS: dict[str, str] = {
    "vehicle_model": "dòng xe đang sử dụng",
    "station_location": "vị trí trạm sạc",
    "error_code": "mã lỗi hoặc đèn báo",
    "warning_symbol": "biểu tượng cảnh báo",
    "operational_status": "tình trạng di chuyển của xe",
    "showroom_dealer": "đại lý hoặc xưởng dịch vụ",
    "complaint_summary": "chi tiết phản ánh",
    "topic": "chủ đề cần hỗ trợ",
}

SUGGESTED_BY_FIELD: dict[str, list[str]] = {
    "vehicle_model": ["VF3", "VF5", "VF8", "VF9"],
    "station_location": ["Trạm Vincom Landmark 81", "Trạm cao tốc", "Sạc AC tại nhà"],
    "error_code": ["Mã lỗi CC01", "Đèn trụ nháy đỏ", "Không hiện mã lỗi"],
    "operational_status": ["Xe vẫn đi chậm được", "Xe không di chuyển được", "Chưa thử khởi động"],
}


async def clarify_node(state: AgentState) -> dict:
    load_prompt("clarify")
    missing = missing_fields_for_state(state)
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

    if len(missing) == 1 and missing[0] in FIELD_SPECIFIC_QUESTIONS:
        question = FIELD_SPECIFIC_QUESTIONS[missing[0]]
        suggested = SUGGESTED_BY_FIELD.get(missing[0], ["VF3", "VF5", "VF8", "Bỏ qua"])
    elif len(missing) > 1:
        items = [FIELD_DESCRIPTIONS.get(f, f) for f in missing]
        question = f"Anh/chị vui lòng cho em biết thêm {', '.join(items[:-1])} và {items[-1]} để em hỗ trợ xử lý nhé ạ."
        suggested = SUGGESTED_BY_FIELD.get(missing[0], ["VF3", "VF5", "VF8", "Bỏ qua"])
    else:
        question = "Anh/chị vui lòng cho em biết thêm thông tin chi tiết về tình trạng xe để em hỗ trợ nhé ạ."
        suggested = ["VF3", "VF5", "VF8", "Bỏ qua"]

    return {
        "missing_fields": missing,
        "clarification_turn": turn + 1,
        "response_type": "CLARIFICATION",
        "response": question,
        "final_response": question,
        "suggested_replies": suggested,
        "needs_staff_review": True,
        "guardrails": flags,
    }
