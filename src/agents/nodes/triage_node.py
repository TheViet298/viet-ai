from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.agents.context_manager import apply_fact_recency_and_invalidation
from src.agents.routing import decide_routing
from src.agents.state import AgentState, IntentType, PriorityLevel
from src.services.agent_llm import structured_call
from src.services.tracer import sanitized_snapshot


class TriageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: IntentType
    priority: PriorityLevel
    confidence_score: float = Field(ge=0, le=1)
    captured_fields: dict[str, str] = Field(default_factory=dict)
    is_faq: bool = False


def classify_request_kind(text: str) -> Literal["faq", "incident", "complaint", "oos", "uncertain"]:
    lower = text.lower()
    if any(k in lower for k in ["bí mật", "nội bộ", "không công khai", "tháng sau"]):
        return "faq"
    if any(k in lower for k in ["khiếu nại", "bức xúc", "thái độ", "không hài lòng", "phản ánh", "hoàn tiền", "thu sai", "khen ngợi", "crash", "bị văng"]):
        return "complaint"
    if re.search(
        r"(?:bị|đang|báo)\s+(?:hỏng|kẹt|gãy|vỡ|lỗi|rùa|đơ|đen|mờ đen)|không mở được (?:cửa|khóa)|"
        r"không\s+(?:nhận\s*sạc|sạc được|khởi động|đi được|vào điện|lên nguồn|mở (?:cửa|khóa) được)|"
        r"bật nguồn không lên|màn hình tối|rùa vàng|nháy đỏ|nhấp nháy|va chạm|"
        r"(?:pin|phanh|lốp|điều hòa|xe).{0,30}(?:hỏng|kẹt|xì|rò|rung|kêu)|"
        r"(?:chìa khóa|smart key).{0,20}hết pin|lỗi\s+(?:[a-z]*\d+|0x)", lower
    ):
        return "incident"
    if any(k in lower for k in ["bao lâu", "bao nhiêu", "chính sách", "bảo hành", "thông số", "giá xe", "đặt lịch", "cách ", "làm thế nào", "như thế nào", "hình thức", "tính năng", "khác nhau", "xem ở đâu", "có bị", "mốc nào", "quãng đường", "dung lượng", "chu kỳ", "khuyến mãi"]):
        return "faq"
    return "uncertain"


def extract_fields(text: str) -> dict[str, str]:
    fields = {}
    patterns = {
        "vehicle_model": r"\b(?:VF\s*(?:[356789]|e34)|e34)\b",
        "charger_id": r"\b(?:VN-CS-[A-Z0-9]+-[A-Z0-9]+|P\d{2})\b",
        "error_code": r"\b(?:CC\d{2}|E\d{3}|P\d{4}|BMS_\d{3}|0x[0-9a-f]+)\b",
        "station_location": r"(?:tại|ở)\s+(?:trạm\s*(?:sạc\s*)?)?([^,.!?]{2,80})",
        "warning_symbol": r"(?:rùa vàng|con rùa|đèn đỏ|nháy đỏ|nhấp nháy đỏ|đèn cổng sạc[^,.!?]{0,30})",
        "operational_status": r"(?:không khởi động|không đi được|vẫn (?:đi|chạy)[^,.!?]{0,30}|không sạc được|không nhận sạc)",
    }
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1) if field == "station_location" else match.group(0)
            fields[field] = value.strip()
    if "vehicle_model" in fields:
        fields["vehicle_model"] = re.sub(r"\s+", "", fields["vehicle_model"]).upper()
        if fields["vehicle_model"] in ("E34", "VFE34"):
            fields["vehicle_model"] = "e34"
    if "warning_symbol" in fields and any(k in text.lower() for k in ["sạc", "trụ"]):
        fields.setdefault("error_code", fields["warning_symbol"])
    if any(k in text.lower() for k in ["tại nhà", "ở nhà", "sạc ac tại nhà"]):
        fields["station_location"] = "Tại nhà"
    return fields


async def triage_node(state: AgentState) -> dict:
    text = state.get("latest_user_message", "")
    lower = text.lower()
    extracted = extract_fields(text)
    previous_intent = state.get("intent")
    request_kind = classify_request_kind(text)
    faq = any(
        k in lower
        for k in [
            "bao lâu",
            "bao nhiêu",
            "chính sách",
            "bảo hành",
            "thông số",
            "giá xe",
            "đặt lịch",
            "cách sử dụng",
            "khuyến mãi",
        ]
    )
    complaint = any(
        k in lower
        for k in ["khiếu nại", "bức xúc", "thái độ", "không hài lòng", "phản ánh", "hoàn tiền", "thu sai", "khen ngợi"]
    )
    complaint = complaint or request_kind == "complaint"
    charging = any(k in lower for k in ["sạc", "pin", "trụ", "súng"]) and not any(k in lower for k in ["chìa khóa", "smart key"])
    incident = any(
        k in lower
        for k in ["hỏng", "lỗi", "rùa", "phanh", "lốp", "không khởi động", "sự cố", "điều hòa", "kêu", "đèn cảnh báo"]
    )
    incident = incident or request_kind == "incident" or any(k in lower for k in ["smart key", "chìa khóa", "bảo dưỡng"])
    faq = request_kind == "faq"
    scoped = any(k in lower for k in ["vinfast", "xe", "vf", "showroom", "bảo dưỡng", "bảo hành"])
    continuation = bool(
        previous_intent
        and state.get("clarification_turn", 0)
        and not faq
        and not complaint
        and not charging
        and not incident
    )
    foreign_domain = any(
        k in lower for k in ["máy bay", "vietnam airlines", "hyundai", "tesla", "thời tiết", "pin mặt trời", "hòa lưới"]
    )
    if foreign_domain and "vinfast" not in lower:
        intent, faq = "Out_of_Scope", False
    elif complaint:
        intent = "Complaint/Feedback"
        extracted["complaint_summary"] = text
        dealer = re.search(r"(?:showroom|đại lý)\s+([^,.!?]{2,60})", text, re.I)
        if dealer:
            extracted["showroom_dealer"] = dealer.group(1)
    elif continuation:
        intent = previous_intent
    elif charging:
        intent = "Charging/Battery"
    elif incident:
        intent = "Service/Incident"
    elif scoped or faq:
        intent = "Sales/General Info"
        faq = True
    else:
        intent = "Out_of_Scope"
    priority = (
        "HIGH"
        if complaint or any(k in lower for k in ["kẹt", "không đi được", "chết máy"])
        else "LOW"
        if faq or intent == "Out_of_Scope"
        else "MEDIUM"
    )
    confidence = 0.90 if (charging or complaint or incident or faq or continuation) else 0.55
    llm = await structured_call(state, "triage", TriageResult) if confidence < 0.60 and not foreign_domain else None
    if llm and not foreign_domain:
        intent, priority, confidence, faq = llm.intent, llm.priority, llm.confidence_score, llm.is_faq
        # Only accept known slots; keep explicitly extracted facts authoritative.
        allowed = {
            "vehicle_model",
            "charger_id",
            "error_code",
            "station_location",
            "warning_symbol",
            "operational_status",
            "showroom_dealer",
            "complaint_summary",
            "topic",
        }
        extracted = {**{k: v for k, v in sanitized_snapshot(llm.captured_fields).items() if k in allowed}, **extracted}
    if complaint and not foreign_domain:
        intent, faq, priority = "Complaint/Feedback", False, "HIGH"
    actual_failure = request_kind == "incident" or bool(
        re.search(
            r"không\s+(?:nhận\s*sạc|sạc được|khởi động|đi được|vào điện)|"
            r"(?:bị|báo|đang)\s+(?:hỏng|kẹt|lỗi|rùa)|lỗi\s+(?:[a-z]*\d+|0x)|"
            r"(?:xe|pin|phanh|lốp|điều hòa).{0,30}(?:hỏng|kẹt|xì|rò|rung|kêu)|"
            r"rùa vàng|nháy đỏ|nhấp nháy đỏ",
            lower,
        )
    )
    if actual_failure and not foreign_domain:
        faq = False
        if intent == "Sales/General Info":
            intent = "Service/Incident"
        if priority == "LOW":
            priority = "MEDIUM"
    # Contract changes and personalized totals require staff confirmation,
    # even when phrased as an informational question.
    if any(term in lower for term in ["đổi gói thuê", "chuyển gói thuê", "giá lăn bánh", "tạm tính", "sau khi trừ ưu đãi"]):
        faq = False
        if priority == "LOW":
            priority = "MEDIUM"
    if state.get("priority") == "HIGH":
        priority = "HIGH"
    if "rùa" in lower and actual_failure:
        priority = "HIGH"
    facts = dict(state.get("captured_fields", {}))
    history = state.get("fact_history", [])
    for field, value in extracted.items():
        facts, history = apply_fact_recency_and_invalidation(
            facts, history, field, value, f"user:turn:{state.get('turn', 0)}"
        )
    flags = dict(state.get("guardrails", {}))
    flags.update(out_of_scope_detected=intent == "Out_of_Scope", sentiment_sensitive_escalated=complaint)
    reply = (
        "Tôi hỗ trợ thông tin xe điện và dịch vụ VinFast. Quý khách vui lòng cho biết yêu cầu liên quan đến VinFast."
    )
    return {
        "intent": intent,
        "priority": priority,
        "confidence_score": confidence,
        "routing": decide_routing({**state, "intent": intent, "is_rag_query": faq}).target,
        "vehicle_model": facts.get("vehicle_model", state.get("vehicle_model")),
        "captured_fields": facts,
        "fact_history": history,
        "is_rag_query": faq,
        "guardrails": flags,
        **(
            {"response_type": "OUT_OF_SCOPE", "response": reply, "final_response": reply}
            if intent == "Out_of_Scope"
            else {}
        ),
    }
