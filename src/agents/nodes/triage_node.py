from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.agents.context_manager import apply_fact_recency_and_invalidation
from src.agents.guardrails import evaluate_hard_safety, strip_accents, without_negated_hazards
from src.agents.routing import decide_routing
from src.agents.state import AgentState, IntentType, PriorityLevel
from src.services.agent_llm import structured_call
from src.services.chat_classification import current_clause, denied_reports, temporal_context, without_denied_reports
from src.services.chat_normalization import normalize_chat_text
from src.services.followup_context import FAQ_FOLLOWUPS
from src.services.location_extraction import extract_locations
from src.services.tracer import sanitized_snapshot
from src.services.vehicle_knowledge import is_general_vehicle_question, is_vehicle_comparison


class TriageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: IntentType
    priority: PriorityLevel
    confidence_score: float = Field(ge=0, le=1)
    captured_fields: dict[str, str] = Field(default_factory=dict)
    is_faq: bool = False


def classify_request_kind(text: str) -> Literal["faq", "incident", "complaint", "oos", "uncertain"]:
    text = normalize_chat_text(text)
    if temporal_context(text) in {'resolved_past', 'hypothetical', 'knowledge'}:
        return 'faq'
    reports_denied = bool(denied_reports(text))
    text = without_denied_reports(without_negated_hazards(current_clause(text)))
    lower = text.lower()
    if any(k in lower for k in ["bí mật", "nội bộ", "không công khai", "tháng sau"]):
        return "faq"
    if any(k in lower for k in ["khiếu nại", "bức xúc", "thái độ", "không hài lòng", "phản ánh", "hoàn tiền", "thu sai", "khen ngợi", "crash", "bị văng"]):
        return "complaint"

    lower_unaccented = strip_accents(lower)

    # 1. Từ khóa nguy hiểm cứng (cháy, khói, mất phanh, tai nạn...) -> Luôn là Incident
    hard_safety_keywords = [
        "cháy", "bốc khói", "mùi khét", "mất phanh", "liệt phanh", "không phanh được",
        "kẹt chân ga", "nổ lốp", "tai nạn", "lật xe", "ngập nước đến sàn"
    ]
    if any(k in lower for k in hard_safety_keywords):
        return "incident"

    # 2. Dấu hiệu tình trạng thực tế / sự cố hiện tại của xe (has_current_failure)
    # Phải kiểm tra trước câu hỏi giải thích ("tại sao", "khi nào") để không bị lọt sự cố (e.g. "Tại sao xe tôi không sạc được?")
    current_failure_regex = (
        r"(?:gặp\s+sự\s+cố|sự\s+cố\s+về|sạc\s+không\s+vào|không\s+vào\s+điện)|"
        r"(?:xe\s*(?:vf\s*(?:[356789]|e34)|e34)?\s*(?:của\s*(?:tôi|mình|em|nhà\s+tôi))?\s*(?:đang|bị|vừa|báo|hiện|gặp)|bây giờ|đang\s*(?:ở|bị|kẹt|dừng|chạy))|"
        r"(?:không\s+(?:nhận\s*sạc|sạc được|khởi động|đi được|chạy được|chạy nổi|di chuyển được|vào điện|lên nguồn|mở (?:cửa|khóa) được|mở được (?:cửa|khóa)))|"
        r"(?:bị|đang|báo)\s+(?:hỏng|kẹt|gãy|vỡ|lỗi|đơ|đen|mờ đen|mã|ma)|"
        r"(?:báo|hiện|nổi)\s+(?:(?:mã|lỗi|code)\s*[a-z0-9_-]{2,10}|(?=[a-z0-9_-]*\d)[a-z0-9_-]{3,10})|"
        r"(?:vô lăng|tay lái)\s+(?:rung|lắc|lệch|giật|nặng)|"
        r"(?:xe tôi|vừa bị|đang bị|xe đang|đang hiện)\s+.*rùa|"
        r"(?:chết máy|nháy đỏ|nhấp nháy|sập nguồn|mất lái|chảy dầu|xì lốp)|"
        r"(?:chân phanh|phanh|chân ga|ắc quy|pin).{0,25}\b(?:hỏng|kẹt|hẫng|chai|tụt nhanh|không ăn)\b|"
        r"cứu tôi|cần cứu hộ|gọi cứu hộ|^cứu hộ[.!? ]*$|không chạy nổi|không thể tăng tốc|lỗi\s+(?:[a-z]*\d+|0x)"
    )
    current_failure_unaccented_regex = (
        r"(?:gap\s+su\s+co|su\s+co\s+ve|sac\s+khong\s+vao|khong\s+vao\s+dien)|"
        r"(?:xe\s*(?:vf\s*(?:[356789]|e34)|e34)?\s*(?:cua\s*(?:toi|minh|em|nha\s+toi))?\s*(?:dang|bi|vua|bao|hien|gap)|bay gio|dang\s*(?:o|bi|ket|dung|chay))|"
        r"(?:khong\s+(?:nhan\s*sac|sac duoc|khoi dong|di duoc|chay duoc|chay noi|di chuyen duoc|vao dien|len nguon|mo (?:cua|khoa) duoc))|"
        r"(?:bi|dang|bao)\s+(?:hong|ket|gay|vo|loi|do|den|mo den|ma)|"
        r"(?:bao|hien)\s+(?:(?:ma|loi|code)\s*[a-z0-9_-]{2,10}|(?=[a-z0-9_-]*\d)[a-z0-9_-]{3,10})|"
        r"(?:vo lang|tay lai)\s+(?:rung|lac|lech|giat|nang)|"
        r"(?:xe toi|vua bi|dang bi|xe dang|dang hien)\s+.*rua|"
        r"(?:chet may|nhay do|nhap nhay|sap nguon|mat lai|chay dau|xi lop)|"
        r"(?:chan phanh|phanh|chan ga|ac quy|pin).{0,25}\b(?:hong|ket|hang|chai|tut nhanh|khong an)\b|"
        r"cuu toi|can cuu ho|goi cuu ho|^cuu ho[.!? ]*$|khong chay noi|khong the tang toc|loi\s+(?:[a-z]*\d+|0x)"
    )
    has_current_failure = bool(
        re.search(current_failure_regex, lower)
        or re.search(current_failure_unaccented_regex, lower_unaccented)
    )
    if has_current_failure:
        return "incident"

    if is_vehicle_comparison(text):
        return "faq"

    if is_general_vehicle_question(text):
        return "faq"

    # 3. Câu hỏi kiến thức / cẩm nang / giải thích thuần túy (FAQ)
    is_explanation_query = any(
        k in lower
        for k in [
            "nghĩa là gì",
            "là gì",
            "ý nghĩa",
            "nghĩa là sao",
            "giải thích",
            "tại sao",
            "khi nào",
            "như thế nào",
            "cách ",
            "làm thế nào",
            "bao lâu",
            "bao nhiêu",
            "chính sách",
            "bảo dưỡng",
            "bảo hành",
            "thông số",
            "giá xe",
            "đặt lịch",
            "hình thức",
            "tính năng",
            "khác nhau",
            "xem ở đâu",
            "có bị",
            "mốc nào",
            "quãng đường",
            "dung lượng",
            "chu kỳ",
            "khuyến mãi",
            "tìm hiểu",
            "hỏi về",
            "cho tôi hỏi",
            "tính phí",
            "bao tiền",
        ]
    )
    if is_explanation_query:
        return "faq"

    if re.search(
        r"(?:hỏng|kẹt|gãy|vỡ|lỗi)|không mở được (?:cửa|khóa)|"
        r"bật nguồn không lên|màn hình tối|va chạm|"
        r"(?:chìa khóa|smart key).{0,20}hết pin", lower
    ):
        return "incident"
    return "faq" if reports_denied else "uncertain"


def extract_fields(text: str, *, asserted_only: bool = True) -> dict[str, str]:
    text = normalize_chat_text(text)
    if asserted_only:
        if temporal_context(text) in {'hypothetical', 'resolved_past', 'knowledge'}:
            return {}
        text = without_denied_reports(current_clause(text))
    fields = {}
    patterns = {
        "vehicle_model": r"\b(?:VF\s*(?:[356789]|e34)|e34)\b",
        "charger_id": r"\b(?:VN-CS-[A-Z0-9]+-[A-Z0-9]+|P\d{2})\b",
        "error_code": r"\b(?!(?:VF\d|VFE34)\b)(?:[A-Z]{2,4}\d{2,4}|[A-Z]{1,4}[_\-]\d{2,4}|CC\d{2}|E\d{3}|P\d{4}|BMS_\d{3}|0x[0-9a-f]+)\b",
        "warning_symbol": r"(?:rùa vàng|con rùa|đèn đỏ|nháy đỏ|nhấp nháy đỏ|đèn cổng sạc[^,.!?]{0,30})",
        "operational_status": r"(?:không khởi động|không đi được|không chạy được|không di chuyển được|vẫn (?:đi|chạy)[^,.!?]{0,30}|không sạc được|không nhận sạc)",
    }
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(0)
            fields[field] = value.strip()
    if "vehicle_model" in fields:
        fields["vehicle_model"] = re.sub(r"\s+", "", fields["vehicle_model"]).upper()
        if fields["vehicle_model"] in ("E34", "VFE34"):
            fields["vehicle_model"] = "e34"
    if "warning_symbol" in fields and any(k in text.lower() for k in ["sạc", "trụ"]):
        fields.setdefault("error_code", fields["warning_symbol"])
    fields.update(extract_locations(text))
    return fields


async def triage_node(state: AgentState) -> dict:
    text = normalize_chat_text(state.get("resolved_query") or state.get("latest_user_message", ""))
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
    incident = incident or request_kind == "incident" or any(k in lower for k in ["smart key", "chìa khóa", "bảo dưỡng", "hết pin", "tụt pin"])
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
    is_crit, rule_name, crit_prio = evaluate_hard_safety(text)

    if foreign_domain and "vinfast" not in lower:
        intent, faq = "Out_of_Scope", False
    elif is_crit:
        intent, faq, priority = "Service/Incident", False, "CRITICAL"
    elif complaint:
        intent = "Complaint/Feedback"
        extracted["complaint_summary"] = text
        dealer = re.search(r"(?:showroom|đại lý)\s+([^,.!?]{2,60})", text, re.I)
        if dealer:
            extracted["showroom_dealer"] = dealer.group(1)
    elif continuation:
        intent = previous_intent
    elif rule_name == "TURTLE_DEFINITION":
        intent = "Sales/General Info"
        faq = True
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
        "CRITICAL"
        if is_crit
        else "HIGH"
        if complaint or any(k in lower for k in ["kẹt", "không đi được", "chết máy"])
        else "LOW"
        if (faq or intent == "Out_of_Scope" or rule_name == "TURTLE_DEFINITION")
        else "MEDIUM"
    )
    confidence = 0.90 if (is_crit or charging or complaint or incident or faq or continuation) else 0.55
    # Ordinary conversation needs no official evidence; product commitments,
    # technical details and repair requests still use the existing grounded flow.
    specialist = is_vehicle_comparison(text) or any(term in lower for term in [
        "bảo hành", "chính sách", "thông số", "dung lượng", "điện áp", "cell", "bms",
        "chu kỳ", "kwh", "bao nhiêu", "bao lâu", "quãng đường", "giá", "phí",
        "khuyến mãi", "ưu đãi", "đổi gói", "chuyển gói", "đặt lịch", "điều kiện",
        "bí mật", "nội bộ", "không công khai", "chưa công khai", "tháng sau",
        "sửa chữa", "tháo", "đấu dây", "chẩn đoán", "hiệu chỉnh", "đo kiểm",
        "cứu hộ",
    ])
    general = (
        not is_crit and not foreign_domain and not complaint and request_kind != "incident"
        and not incident and not specialist
        and not continuation
        and (scoped or charging or state.get("is_general_query")
             or lower.strip(" .!?") in ["xin chào", "chào", "hello", "cảm ơn"])
    )
    common_knowledge = (is_general_vehicle_question(text) and request_kind == "faq"
                        and not is_crit and not foreign_domain and not complaint)
    general = general or common_knowledge
    llm = await structured_call(state, "triage", TriageResult) if confidence < 0.60 and not foreign_domain and not is_crit and not general else None
    if llm and not foreign_domain and not is_crit:
        intent, priority, confidence, faq = llm.intent, llm.priority, llm.confidence_score, llm.is_faq
        # Only accept known slots; keep explicitly extracted facts authoritative.
        allowed = {
            "vehicle_model",
            "charger_id",
            "error_code",
            "warning_symbol",
            "operational_status",
            "showroom_dealer",
            "complaint_summary",
            "topic",
        }
        extracted = {**{k: v for k, v in sanitized_snapshot(llm.captured_fields).items() if k in allowed}, **extracted}
    if complaint and not foreign_domain and not is_crit:
        intent, faq, priority = "Complaint/Feedback", False, "HIGH"
    actual_failure = (request_kind == "incident") or (
        request_kind != "faq"
        and bool(
            re.search(
                r"không\s+(?:nhận\s*sạc|sạc được|khởi động|đi được|chạy nổi|vào điện)|"
                r"(?:bị|báo|đang)\s+(?:hỏng|kẹt|lỗi)|lỗi\s+(?:[a-z]*\d+|0x)|"
                r"(?:xe|pin|phanh|lốp|điều hòa).{0,30}(?:hỏng|kẹt|xì|rò|rung|kêu)|"
                r"(?:xe tôi|đang bị|vừa bị|đang hiện)\s+.*(?:rùa vàng|con rùa)|nháy đỏ|nhấp nháy đỏ",
                lower,
            )
        )
    )
    if is_crit:
        faq = False
        intent = "Service/Incident"
        priority = "CRITICAL"
    elif actual_failure and not foreign_domain and request_kind != "faq":
        faq = False
        if intent == "Sales/General Info":
            intent = "Service/Incident"
        if priority == "LOW":
            priority = "MEDIUM"
    if general:
        faq, priority, confidence = False, "LOW", 0.90
        if intent == "Out_of_Scope":
            intent = "Sales/General Info"
    elif specialist and not is_crit and not actual_failure and not complaint and not foreign_domain:
        faq = True
    # Contract changes and personalized totals require staff confirmation,
    # even when phrased as an informational question.
    if any(term in lower for term in ["đổi gói thuê", "chuyển gói thuê", "giá lăn bánh", "tạm tính", "sau khi trừ ưu đãi"]):
        faq = False
        if priority == "LOW":
            priority = "MEDIUM"
    if is_crit:
        priority = "CRITICAL"
    elif state.get("priority") == "HIGH":
        priority = "HIGH"
    elif "rùa" in lower and actual_failure:
        priority = "HIGH"
    if lower.strip(" .?!") in FAQ_FOLLOWUPS:
        # A short reference without a resolved topic needs clarification first.
        intent, faq, general, confidence = "Sales/General Info", False, False, 0.90
    facts = dict(state.get("captured_fields", {}))
    understood = state.get('turn_understanding') or {}
    if understood.get('goal') and understood.get('move') != 'new_incident' and not is_crit and not foreign_domain and not complaint:
        intent, confidence = 'Sales/General Info', .9
        general = understood['goal'] == 'concept'
        faq = not general
    history = state.get("fact_history", [])
    if "vehicle_context" in state:
        context = state["vehicle_context"]
        # Only observations from the original input can become facts. A resolved
        # topic or an LLM extraction is not customer evidence.
        extracted = extract_fields(state.get('latest_user_message', text))
        extracted.pop("vehicle_model", None)
        if context.get("is_incident") and context.get("incident_model"):
            extracted["vehicle_model"] = context["incident_model"]
    for field, value in extracted.items():
        facts, history = apply_fact_recency_and_invalidation(
            facts, history, field, value, f"user:turn:{state.get('turn', 0)}"
        )
    flags = dict(state.get("guardrails", {}))
    flags.update(out_of_scope_detected=intent == "Out_of_Scope", sentiment_sensitive_escalated=complaint)
    reply = (
        "Dạ em chuyên hỗ trợ thông tin xe điện và dịch vụ VinFast. Quý khách vui lòng cho biết yêu cầu liên quan đến VinFast ạ."
    )
    return {
        "intent": intent,
        "priority": priority,
        "confidence_score": confidence,
        "routing": decide_routing({**state, "intent": intent, "is_rag_query": faq}).target,
        "vehicle_model": state.get("vehicle_model") if "vehicle_context" in state else facts.get("vehicle_model", state.get("vehicle_model")),
        "captured_fields": facts,
        "fact_history": history,
        "is_rag_query": faq,
        "is_general_query": general,
        "guardrails": flags,
        **(
            {"response_type": "OUT_OF_SCOPE", "response": reply, "final_response": reply}
            if intent == "Out_of_Scope"
            else {}
        ),
    }
