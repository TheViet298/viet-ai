from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from src.agents.context_manager import apply_fact_recency_and_invalidation
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
    charging = any(k in lower for k in ["sạc", "pin", "trụ", "súng"])
    incident = any(
        k in lower
        for k in ["hỏng", "lỗi", "rùa", "phanh", "lốp", "không khởi động", "sự cố", "điều hòa", "kêu", "đèn cảnh báo"]
    )
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
    llm = await structured_call(state, "triage", TriageResult)
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
    actual_failure = bool(
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
    if state.get("priority") == "HIGH":
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
        "routing": {
            "Charging/Battery": "charging_support",
            "Service/Incident": "service_center",
            "Complaint/Feedback": "customer_relations",
            "Sales/General Info": "sales_support",
            "Out_of_Scope": "customer_relations",
        }[intent],
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
