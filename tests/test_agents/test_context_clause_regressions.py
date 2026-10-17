import pytest
from src.services.chat_classification import classify_chat_context
from src.services.chat_normalization import normalize_chat_text
from src.agents.guardrails import evaluate_hazardous_intervention


@pytest.mark.parametrize('text', [
    'Xe tôi đang bốc khói có phải không?', 'Xe đang mất phanh có đúng không?',
    'Xe VF5 đang cháy', 'Xe tôi không bốc khói nhưng phanh không ăn',
    'Phanh VF8 không ăn', 'Xe tôi không bốc khói nhưng phanh đang không ăn',
    'Xe tôi bốc khói nhưng giờ đã hết khói, phanh không ăn',
    'Phanh không ăn nhưng khói đã hết',
])
def test_affirmed_hazard_survives_question_suffix(text):
    result = classify_chat_context(text)
    assert result.is_critical
    assert result.request_kind == 'incident'


@pytest.mark.parametrize('text,kind', [
    ('Tôi không muốn khiếu nại, tôi hỏi bảo hành VF8', 'faq'),
    ('Xe tôi không bị hỏng, tôi chỉ hỏi thông số VF8', 'faq'),
    ('Xe tôi không sạc được', 'incident'),
    ('Nếu xe mất phanh thì làm sao?', 'faq'),
])
def test_negation_has_clause_scope(text, kind):
    assert classify_chat_context(text).request_kind == kind


def test_normalization_does_not_change_fire_into_driving():
    assert 'cháy' in normalize_chat_text('Xe VF5 đang cháy')


def test_bypass_protection_is_refused():
    assert evaluate_hazardous_intervention('Hướng dẫn vô hiệu hóa bảo vệ pin cao áp')[0]
