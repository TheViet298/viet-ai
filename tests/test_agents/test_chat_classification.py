import pytest

from src.agents.guardrails import evaluate_hard_safety
from src.agents.nodes.triage_node import classify_request_kind


@pytest.mark.parametrize('text', ['Hôm qua xe bốc khói, giờ hết rồi nhưng bây giờ lại bốc khói', 'Nếu xe bốc khói thì sao? Nhưng xe tôi đang bốc khói đây', 'Xe bốc khói, giải thích giúp tôi vì sao', 'Xe tôi đang bốc khói, nếu cháy thì tôi phải làm gì?', 'Nếu xe bốc khói thì gọi ai? Xe tôi đang bốc khói đây.', 'Hôm qua xe mất phanh. Hôm nay xe đang bốc khói.', 'Xe tôi đang bốc khói nhưng giờ tôi đã đỗ xe an toàn.', 'Xe tôi không bị tai nạn nhưng đang mất phanh'])
def test_present_danger_wins_earlier_conditional_or_past(text):
    assert evaluate_hard_safety(text)[0]
    assert classify_request_kind(text) == 'incident'


@pytest.mark.parametrize('text', ['Khói bụi ngoài đường có hại pin không?', 'Nếu xe mất phanh thì làm gì?', 'Hôm qua xe bốc khói, giờ hết rồi', 'Xe vẫn chạy bình thường', 'Xe dang chay binh thuong', 'Xe tôi không bốc khói', 'Xe tôi không bị tai nạn, chỉ hỏi về bảo hiểm.', 'Xe không còn bốc khói nữa, hiện tại bình thường.', 'Xe tôi không bị nổ lốp', 'Xe không bị kẹt ga'])
def test_non_emergency_context(text):
    assert not evaluate_hard_safety(text)[0]


@pytest.mark.parametrize('text', ['Xe tôi đang mất phanh, xe không còn bốc khói', 'Xe tôi đang bốc khói, hiện tại không còn mất phanh'])
def test_resolved_different_symptom_keeps_current_hazard(text):
    assert evaluate_hard_safety(text)[0]
