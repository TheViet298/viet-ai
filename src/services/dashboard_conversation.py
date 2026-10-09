"""Customer-selected dashboard image help, separate from incident triage."""

import re

from src.services.dashboard_warning_service import ALIASES, VISIBLE_WARNING_LABELS, normalize

INCIDENT_CHOICE = "Xe đang gặp sự cố"
EXPLANATION_CHOICE = "Giải thích về lỗi được nhận diện"
DASHBOARD_CHOICES = [INCIDENT_CHOICE, EXPLANATION_CHOICE]
DASHBOARD_SAFE_GUIDANCE = "Nếu xe có dấu hiệu nguy hiểm, hãy dừng tại nơi an toàn và liên hệ cứu hộ."

EXPLANATIONS = {
    "brake_system_fault": "**Lỗi hệ thống trợ lực phanh thủy lực:** màn hình đang báo bất thường ở chức năng hỗ trợ lực phanh. Khi trợ lực giảm, lực đạp bàn đạp phanh cần thiết có thể tăng. Ảnh chưa cho biết nguyên nhân hoặc mức độ hoạt động thực tế của phanh; cần kiểm tra tại xưởng, không thể kết luận hỏng bơm hay mất dầu chỉ từ ảnh.",
    "turtle": "**Biểu tượng rùa vàng:** cảnh báo xe đang hạn chế công suất (chế độ vận hành giới hạn). Xe có thể tăng tốc chậm hoặc giảm khả năng vận hành. Ảnh chưa đủ để xác định do pin yếu, nhiệt độ hay lỗi hệ thống; cần đọc thông báo đi kèm và kiểm tra đúng mẫu xe.",
    "abs": "**Đèn ABS:** cảnh báo liên quan đến hệ thống chống bó cứng phanh. Khi có bất thường, chức năng chống bó cứng có thể bị hạn chế; đèn này không tự chứng minh hệ thống phanh chính đã mất tác dụng.",
    "brake": "**Đèn cảnh báo hệ thống phanh:** yêu cầu chú ý thông báo của hệ thống phanh. Cần đối chiếu chữ trên màn hình và trạng thái phanh đỗ để xác định cảnh báo cụ thể.",
    "esc": "**Biểu tượng xe trượt:** liên quan đến cân bằng điện tử/chống trượt. Đèn nhấp nháy có thể biểu thị hệ thống đang can thiệp; sáng liên tục có thể biểu thị hệ thống tắt hoặc có bất thường. Một ảnh tĩnh chưa phân biệt được hai trạng thái này.",
    "general_warning": "**Tam giác chấm than:** cảnh báo chung, cần đọc thông báo đi kèm trên màn hình để biết hệ thống nào cần chú ý.",
    "low_pressure": "**Áp suất lốp thấp:** cảnh báo áp suất một hoặc nhiều lốp thấp hơn mức yêu cầu. Kiểm tra khi lốp nguội và đối chiếu tem áp suất trên khung cửa lái hoặc sổ tay đúng phiên bản xe.",
    "sensor_fault": "**Lỗi cảm biến áp suất lốp:** hệ thống chưa nhận được thông tin áp suất đáng tin cậy từ cảm biến. Cần kiểm tra áp suất thực tế và cảm biến, chưa thể xác định bộ phận hỏng từ ảnh.",
    "eps": "**Đèn trợ lực lái (EPS):** cảnh báo liên quan đến chức năng hỗ trợ lực đánh lái. Cần đối chiếu thông báo đi kèm và kiểm tra thực tế; ảnh chưa xác định nguyên nhân.",
    "airbag": "**Đèn túi khí:** cảnh báo liên quan đến hệ thống túi khí/an toàn thụ động. Cần kiểm tra tại xưởng; ảnh không xác nhận bộ phận nào hỏng.",
    "tpms": "**Đèn TPMS:** cảnh báo liên quan đến áp suất lốp hoặc hệ thống giám sát áp suất. Cần đọc chữ đi kèm và kiểm tra áp suất thực tế để phân biệt.",
    "battery": "**Đèn pin/ắc quy:** cảnh báo liên quan đến hệ thống điện/pin. Cần đọc thông báo chi tiết để xác định hệ thống nào đang được cảnh báo; ảnh chưa xác nhận hỏng pin cao áp.",
    "seatbelt": "**Đèn dây an toàn:** nhắc kiểm tra và cài dây an toàn của người ngồi trên xe.",
    "parking_brake": "**Đèn phanh đỗ:** thể hiện trạng thái hoặc cảnh báo liên quan đến phanh đỗ. Cần đối chiếu trạng thái kích hoạt và thông báo đi kèm.",
}


def dashboard_question(text: str) -> bool:
    value = normalize(text)
    if any(term in value for term in ("gia ", "bao nhieu", "tieu chuan", "trang bi", "bao hanh", "bao duong")):
        return False
    reference = any(term in value for term in ("loi", "den ", "canh bao", "la gi", "giai thich", "bieu tuong", "trong anh"))
    topic = bool(re.search(r"\b(rua|turtle|phanh|abs|esc|tpms|eps|tui khi)\b", value))
    return (topic and reference) or any(term in value for term in (
        "bieu tuong", "loi duoc nhan dien", "canh bao trong anh", "loi trong anh", "tam giac",
    ))


def explain_dashboard(signals: list[dict], text: str) -> str:
    """Explain only identified warnings; a focused question selects its topic."""
    keys = {key for signal in signals for key in signal.get("symptom_keys", []) if key in ALIASES}
    keys |= {icon.get("kind") for signal in signals for icon in signal.get("visible_warnings", [])
             if icon.get("confidence", 0) >= .8}
    if "turtle_mode_power_limited" in keys:
        keys.add("turtle")
    for symptom, icon in {"abs_fault": "abs", "esc_fault": "esc", "tpms_system_error": "tpms",
                          "eps_steering_fault": "eps", "airbag_warning": "airbag",
                          "high_voltage_battery_fault": "battery", "seatbelt_warning": "seatbelt"}.items():
        if symptom in keys:
            keys.add(icon)
    value = normalize(text)
    if value != normalize(EXPLANATION_CHOICE):
        if "rua" in value or "turtle" in value:
            keys &= {"turtle"}
        elif "tro luc phanh" in value:
            keys &= {"brake_system_fault"}
        elif "abs" in value:
            keys &= {"abs", "abs_fault"}
        elif "esc" in value:
            keys &= {"esc", "esc_fault"}
    paragraphs = [description for key, description in EXPLANATIONS.items() if key in keys]
    if paragraphs:
        return "\n\n".join(paragraphs)
    labels = [VISIBLE_WARNING_LABELS.get(key, key.replace("_", " ")) for key in sorted(keys)]
    if labels:
        return "Em đã nhận diện: " + ", ".join(labels) + ". Chưa có đủ hướng dẫn đối chiếu cho cảnh báo này; vui lòng cho biết mẫu xe và nội dung thông báo để em tra cứu đúng phiên bản."
    return "Em chưa nhận diện chắc chắn cảnh báo này trong ảnh. Vui lòng cho biết nội dung chữ hoặc gửi ảnh rõ hơn để em giải thích đúng cảnh báo."
