"""Resolve bounded FAQ references without changing the user's original text."""
import re

FAQ_FOLLOWUPS = {
    "điều kiện là gì", "điều kiện gì", "điều kiện thế nào", "điều kiện là gì vậy",
    "ở đâu", "làm ở đâu", "đặt ở đâu", "cần gì", "cần những gì", "làm thế nào",
}


def resolve_faq_followup(text: str, state: dict) -> str:
    normalized = text.casefold().strip(" .?!")
    # Explicit new topics, incidents and unsafe requests never match this list.
    if normalized not in FAQ_FOLLOWUPS or not state.get("is_rag_query") or state.get("response_type") != "FAQ_ANSWER":
        return text
    prior_human = next((str(message.content) for message in reversed(state.get("messages", [])) if getattr(message, "type", "") == "human"), "")
    previous = state.get("resolved_query") or prior_human or state.get("latest_user_message") or ""
    lower = previous.casefold()
    model = re.search(r"\bvf\s*(?:e34|[356789])\b", previous, re.I)
    vehicle = model.group() if model else state.get("vehicle_model", "")
    if "bảo hành" in lower and normalized.startswith("điều kiện"):
        qualifier = " sử dụng tiêu chuẩn" if "sử dụng tiêu chuẩn" in state.get("response", "").casefold() else ""
        return f"Điều kiện{qualifier} trong chính sách bảo hành xe {vehicle} VinFast là gì?"
    if "đặt lịch" in lower:
        subject = "bảo dưỡng" if "bảo dưỡng" in lower else "dịch vụ"
        return f"Đặt lịch {subject} xe {vehicle} trên ứng dụng VinFast: {text}?"
    return text
