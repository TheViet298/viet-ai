from __future__ import annotations

import re
import unicodedata
from typing import Any

from src.agents.state import PriorityLevel
from src.services.chat_classification import analyze_report_clauses, current_clause, temporal_context
from src.services.chat_normalization import normalize_chat_text

# =====================================================================
# Constants & Hotline
# =====================================================================

VINFAST_HOTLINE = "1900-232389"

EMERGENCY_SAFE_GUIDANCE = (
    "Quý khách vui lòng giữ bình tĩnh, tấp xe vào lề an toàn nếu có thể, "
    "bật đèn cảnh báo khẩn cấp (hazard), di chuyển ra khỏi xe đến khu vực an toàn "
    f"và gọi ngay Hotline Cứu hộ VinFast {VINFAST_HOTLINE} để được hỗ trợ khẩn cấp."
)

HYPOTHETICAL_SAFE_GUIDANCE = (
    'Đây là hướng dẫn an toàn chung cho tình huống giả định, chưa phải báo cáo sự cố đang xảy ra. '
    + EMERGENCY_SAFE_GUIDANCE +
    ' Nếu có khói hoặc lửa, giữ khoảng cách với xe và không chạm vào pin, dây cao áp hoặc đầu nối sạc. '
    'Không tiếp tục sử dụng xe cho đến khi nhân viên chuyên môn đã đánh giá an toàn.'
)

STANDARD_SAFE_GUIDANCE = (
    "Quý khách vui lòng giữ xe ở vị trí đỗ an toàn và theo dõi cập nhật trạng thái xử lý trực tiếp trên giao diện này."
)

# =====================================================================
# Layer 1: Privacy & PII Sanitizer Guardrail
# =====================================================================

PII_PATTERNS: dict[str, str] = {
    "phone": r"(\+?84|0)(3[2-9]|5[6|8|9]|7[0|6-9]|8[1-5]|9[0-9])[0-9]{7}",
    "national_id": r"\b\d{9}\b|\b\d{12}\b",  # CMND 9 số hoặc CCCD 12 số
    "license_plate": r"\b\d{2}[A-Z\d]-?\d{4,5}(\.\d{2})?\b",  # Biển số xe VN
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
}


def sanitize_pii(text: str) -> tuple[str, bool, list[str]]:
    """Phát hiện và ẩn danh hóa thông tin PII thật (SĐT, CCCD, Biển số, Email).

    Returns:
        (sanitized_text, is_pii_detected, list_of_detected_types)
    """
    sanitized = text
    detected_types: list[str] = []

    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, sanitized, flags=re.IGNORECASE):
            detected_types.append(pii_type)
            sanitized = re.sub(
                pattern,
                f"[REDACTED_{pii_type.upper()}]",
                sanitized,
                flags=re.IGNORECASE,
            )

    return sanitized, len(detected_types) > 0, detected_types


def strip_accents(s: str) -> str:
    """Loại bỏ dấu tiếng Việt để đối chiếu từ khóa gõ không dấu."""
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")


# =====================================================================
# Layer 2: Hard Safety Rules Guardrail (Deterministic Code/Regex)
# =====================================================================

CRITICAL_STANDALONE_RULES: dict[str, str] = {
    "SMOKE_OR_FIRE": (
        r"\b(cháy|cháy xe|xe bốc lửa|bốc lửa|có (?:ngọn )?lửa|ngọn lửa|bốc khói|khói từ (?:xe|pin)|xe.{0,15}(?:có|ra|xì) khói|mùi khét|xì khói|chập điện|"
        r"chay|chay xe|xe boc lua|boc lua|boc khoi|khoi tu (?:xe|pin)|xe.{0,15}(?:co|ra|xi) khoi|mui khet|chap dien)\b"
    ),
    "BRAKE_FAILURE": (
        r"\bphanh\s+(?:VF\s*[356789]\s+)?(?:đang\s+)?không\s+ăn\b|"
        r"\bphanh\s+(?:vf\s*[356789]\s+)?(?:dang\s+)?khong\s+an\b|"
        r"\b(mất phanh|liệt phanh|phanh không ăn|không phanh được|không ăn phanh|"
        r"hẫng phanh|đạp phanh không ăn|(chân phanh|phanh)\s*(bị\s*)?(hẫng|mất|kẹt|sát sàn)|"
        r"(hẫng|mất|kẹt)\s*(chân phanh|phanh)|"
        r"mat phanh|liet phanh|phanh khong an|khong phanh duoc|hang phanh)\b"
    ),
    "ACCELERATOR_JAM": r"\b(kẹt chân ga|kẹt ga|dính ga|chân ga bị kẹt|ket chan ga|ket ga)\b",
    "TIRE_BURST": r"\b(nổ lốp|rách lốp|nổ vỏ|bể bánh|no lop|rach lop|be banh)\b",
    "ACCIDENT": r"\b(tai nạn|lật xe|đâm va mạnh|va chạm mạnh|tai nan|lat xe)\b",
    "FLOODED_CABIN": r"\b(ngập nước đến sàn|nước tràn vào sàn|ngập sàn xe|ngập đến sàn|ngap nuoc den san|ngap san xe)\b",
}

TURTLE_PATTERN = r"\b(rùa vàng|con rùa|biểu tượng con rùa|báo rùa|rua vang|con rua)\b"
TURTLE_DANGER_CONDITIONS = (
    r"\b(cao tốc|mất kiểm soát|giảm công suất|dừng giữa đường|"
    r"không thể tăng tốc|giật mạnh|mất lái|đang chạy|trên cầu|"
    r"cao toc|mat kiem soat|giam cong suat|dung giua duong|giat manh|mat lai|dang chay|tren cau)\b"
)


def evaluate_hard_safety(text: str) -> tuple[bool, str | None, PriorityLevel]:
    """Kiểm tra Hard Safety Rules trước khi gọi LLM.

    Returns:
        (is_critical, trigger_rule_name, priority)
    """
    text = normalize_chat_text(text)
    temporal = temporal_context(text)
    if temporal in {'resolved_past', 'hypothetical', 'knowledge'}:
        return False, 'TURTLE_DEFINITION' if re.search(TURTLE_PATTERN, text.lower()) else None, 'LOW'
    text_lower = analyze_report_clauses(text).current_affirmed_text.lower()
    # Negated symptom mentions do not establish that symptom. Other actual
    # hazards in the same message remain eligible for hard safety.
    text_lower = without_negated_hazards(text_lower)
    text_unaccented = strip_accents(text_lower)

    # 1. Kiểm tra các rủi ro độc lập (cháy, mất phanh, kẹt ga...)
    # Bỏ qua nếu là câu hỏi kiến thức thuần túy phủ định (e.g. "tại sao xe điện không có khói?")
    is_pure_inquiry = bool(re.search(r"\b(nghĩa là gì|là gì|ý nghĩa|tại sao lại không có|có khói không)\b", text_lower))
    has_emergency_presence = bool(re.search(r"\b(xe tôi|xe của tôi|đang bị|vừa bị|đang|vừa|thấy|bốc|khét|cứu)\b", text_lower))

    for rule_name, pattern in CRITICAL_STANDALONE_RULES.items():
        rule_text = text_lower
        normalized_text = text_unaccented
        if rule_name == "SMOKE_OR_FIRE":
            # Do not turn accented "chạy" (driving) into "cháy" (fire).
            # For unaccented input, only suppress the explicit driving phrase.
            rule_text = re.sub(r"\b(?:đang|vẫn|dang|van)\s+(?:chạy|chay)\b|\bchạy\b", "di chuyển", text_lower)
            # Bare ASCII "chay" needs confirmation (driving vs. fire).
            # Explicit "bi chay" has already become "bị cháy" above.
            rule_text = re.sub(r'\bchay\b', 'chưa rõ hiện tượng', rule_text)
            normalized_text = rule_text
        if re.search(pattern, rule_text) or re.search(pattern, normalized_text):
            if is_pure_inquiry and not has_emergency_presence and rule_name == "SMOKE_OR_FIRE":
                continue
            return True, rule_name, "CRITICAL"

    # 2. Kiểm tra tổ hợp rủi ro: "rùa vàng" + điều kiện nguy hiểm / cao tốc
    has_turtle = bool(re.search(TURTLE_PATTERN, text_lower) or re.search(TURTLE_PATTERN, text_unaccented))
    if has_turtle:
        has_danger_context = bool(
            re.search(TURTLE_DANGER_CONDITIONS, text_lower) or re.search(TURTLE_DANGER_CONDITIONS, text_unaccented)
        )
        if has_danger_context:
            return True, "TURTLE_ON_HIGHWAY", "CRITICAL"
        is_inquiry = bool(re.search(r"\b(nghĩa là gì|là gì|ý nghĩa|nghĩa là sao|tại sao lại có|giải thích|tìm hiểu)\b", text_lower))
        has_current_state = bool(re.search(r"\b(xe tôi|xe của tôi|đang bị|đang hiện|vừa bị|bị hiện|xe đang|vừa hiện)\b", text_lower))
        if is_inquiry and not has_current_state:
            return False, "TURTLE_DEFINITION", "LOW"
        # Rùa vàng ở điều kiện bình thường (bãi xe, ngõ nhà) -> HIGH, không gắn CRITICAL
        return False, "TURTLE_NORMAL", "HIGH"

    return False, None, "MEDIUM"


def without_negated_hazards(text: str) -> str:
    """Mask denied hazards while keeping affirmative hazards in other clauses."""
    text = normalize_chat_text(text)
    hazard_terms = (
        r"(?:khói|khoi(?!\s+dong)|mùi khét|mui khet|bốc khói|boc khoi|cháy xe|chay xe|cháy|chay|"
        r"chập điện|chap dien|xì khói|xi khoi|bốc lửa|boc lua|mất phanh|mat phanh|"
        r"liệt phanh|liet phanh|kẹt chân ga|ket chan ga|nổ lốp|no lop|tai nạn|tai nan)"
    )
    conjunction_pattern = (
        rf"\b(?:không|khong|chưa|chua)\s+(?:(?:còn|con|có|co|thấy|thay|bị|bi|hề|he|phát hiện)\s+)*"
        rf"{hazard_terms}(?:\s+(?:hay|hoặc|hoac|lẫn|lan|và|va)\s+(?:(?:có|co|thấy|thay|bị|bi)\s+)*{hazard_terms})*"
    )
    text = re.sub(conjunction_pattern, "[phủ định]", text, flags=re.I)

    prefix = r"\b(?:không|khong|chưa|chua)\s+(?:(?:còn|con|có|co|thấy|thay|bị|bi|hề|he|bao giờ|bao gio)\s+)*"
    for pattern in [*CRITICAL_STANDALONE_RULES.values(), TURTLE_PATTERN]:
        text = re.sub(prefix + '(?:' + pattern + ')', "[phủ định]", text, flags=re.I)
    return text


HAZARDOUS_INTERVENTION_PATTERN = (
    r"\b(?:tháo|mở|can thiệp|đấu nối|chạm vào|tự sửa|đo điện)\s+(?:bộ\s+)?(?:pin|cọc pin|dây cam|dây cao áp|hệ thống cao áp|pack pin|cell pin)\b|"
    r"\b(?:thao|mo|can thiep|dau noi|cham vao|tu sua|do dien)\s+(?:bo\s+)?(?:pin|coc pin|day cam|day cao ap|cao ap)\b|"
    r"\b(?:tháo|thao)\s+(?:bộ\s+|bo\s+)?pin\s+(?:ra|để|de)\b"
)


def evaluate_hazardous_intervention(text: str) -> tuple[bool, str | None]:
    """Phát hiện yêu cầu hoặc câu hỏi về việc tự ý can thiệp phần cứng/hệ thống pin cao áp nguy hiểm."""
    lower = text.lower()
    lower_unaccented = strip_accents(lower)
    if (re.search(HAZARDOUS_INTERVENTION_PATTERN, lower)
            or re.search(HAZARDOUS_INTERVENTION_PATTERN, lower_unaccented)
            or re.search(r'\b(?:vo hieu hoa|bo qua|bypass|tat)\b.{0,35}\b(?:bao ve|an toan)\b.{0,25}\b(?:pin|cao ap|bms)\b', lower_unaccented)):
        warning = (
            "CẢNH BÁO AN TOÀN CAO ÁP: Quý khách tuyệt đối không tự ý tháo mở, can thiệp hoặc chạm vào bộ pin và hệ thống dây điện cao áp. "
            "Hệ thống pin ô tô điện hoạt động ở điện áp rất cao và tiềm ẩn nguy cơ giật điện hoặc cháy nổ nguy hiểm đến tính mạng. "
            "Vui lòng giữ khoảng cách an toàn với xe và chờ kỹ thuật viên chuyên trách của VinFast tiếp nhận xử lý."
        )
        return True, warning
    return False, None


# =====================================================================
# Layer 3: Boundary Guardrails (Clarification & Out-of-Scope)
# =====================================================================

REQUIRED_FIELDS_BY_INTENT: dict[str, list[str]] = {
    "Charging/Battery": ["vehicle_model", "station_location", "error_code"],
    "Service/Incident": ["vehicle_model", "warning_symbol", "operational_status"],
    "Complaint/Feedback": ["showroom_dealer", "complaint_summary"],
    "Sales/General Info": ["topic"],
}


def check_missing_fields(
    intent: str | None,
    captured_fields: dict[str, Any],
) -> list[str]:
    """Kiểm tra các trường bắt buộc còn thiếu theo từng Intent."""
    if not intent or intent not in REQUIRED_FIELDS_BY_INTENT:
        return []

    required = REQUIRED_FIELDS_BY_INTENT[intent]
    missing = [field for field in required if field not in captured_fields or not captured_fields[field]]
    return missing


def check_clarification_boundary(clarification_turn: int, max_turns: int = 2) -> bool:
    """Xác định xem Agent có được phép tiếp tục gửi câu hỏi làm rõ không.

    Quy tắc: Tối đa 2 lượt hỏi làm rõ chủ động.
    Returns:
        True nếu turn < max_turns (cho phép hỏi tiếp).
        False nếu đã đạt giới hạn (chuyển sang tạo Case Needs Information).
    """
    return clarification_turn < max_turns


# =====================================================================
# Layer 4: HITL Decision & Confidence Threshold Guardrails
# =====================================================================


def is_hitl_mandatory(
    intent: str | None,
    priority: PriorityLevel,
    confidence_score: float,
    is_critical: bool,
    rag_score: float = 1.0,
) -> bool:
    """Xác định xem yêu cầu có bắt buộc phải qua Service Agent Console (HITL) không.

    Bắt buộc 100% khi:
    1. Toàn bộ ticket thuộc Charging/Battery, Service/Incident, Complaint/Feedback.
    2. Priority là CRITICAL hoặc HIGH.
    3. is_critical là True.
    4. Confidence score < 0.60.
    5. FAQ nhưng RAG similarity score < 0.70.
    """
    if is_critical or priority in ("CRITICAL", "HIGH"):
        return True

    if intent in ("Charging/Battery", "Service/Incident", "Complaint/Feedback"):
        return True

    if confidence_score < 0.60:
        return True

    if intent == "Sales/General Info" and rag_score < 0.70:
        return True

    return False
