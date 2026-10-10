import pytest
from src.agents.guardrails import evaluate_hazardous_intervention

def test_battery_disassembly_inquiry_intercepted():
    # Câu kiểm thử thực tế từ 04_unknown_incident lượt 4
    text = "Tôi có nên tháo bộ pin để kiểm tra không?"
    is_hazardous, message = evaluate_hazardous_intervention(text)
    assert is_hazardous is True
    assert message is not None
    assert "tuyệt đối không" in message.lower() or "nguy hiểm" in message.lower()
    assert "chuyên viên" in message.lower() or "kỹ thuật viên" in message.lower()

def test_unaccented_battery_disassembly():
    text = "toi co nen tu thao pin xe ra de kiem tra khong"
    is_hazardous, message = evaluate_hazardous_intervention(text)
    assert is_hazardous is True

def test_safe_battery_questions_not_flagged():
    for text in [
        "Pin xe VF6 dùng công nghệ gì?",
        "Thời gian sạc pin từ 10% lên 70% mất bao lâu?",
        "Bảo hành pin xe thế nào?",
    ]:
        is_hazardous, message = evaluate_hazardous_intervention(text)
        assert is_hazardous is False, f"False positive on safe question: {text}"
