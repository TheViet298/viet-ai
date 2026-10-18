import pytest
from src.services.answer_evidence import extract_numeric_claims, validate_answer_claims


@pytest.mark.parametrize('text,keys', [
    ('VF8 sạc từ 10% đến 80% trong 30 phút.', ['soc', 'soc', 'charging_time']),
    ('Tốc độ tối đa VF8 là 200 km/h.', ['speed']),
    ('Chu kỳ bảo dưỡng VF8 là 1 năm.', ['maintenance_interval']),
])
def test_exact_source_quantities_have_correct_semantics(text, keys):
    citations = [{'source_id': 's', 'relevant_snippet': text}]
    claims = extract_numeric_claims(text, citations, 'VF8', text)
    assert [claim.claim_key for claim in claims] == keys
    assert validate_answer_claims(claims, citations, [])['supported']


def test_speed_cannot_be_supported_by_range():
    source = [{'source_id': 's', 'relevant_snippet': 'VF8 quãng đường 200 km.'}]
    claims = extract_numeric_claims('Tốc độ tối đa VF8 200 km/h.', source, 'VF8')
    assert not validate_answer_claims(claims, source, [])['supported']


@pytest.mark.parametrize('answer', ['VF7 quãng đường 500 km.', 'VF8 Eco quãng đường 500 km.'])
def test_explicit_answer_model_and_trim_are_not_replaced_by_context(answer):
    source = [{'source_id':'s', 'relevant_snippet':'VF8 Plus quãng đường 500 km (WLTP).'}]
    claims = extract_numeric_claims(answer, source, 'VF8 Plus')
    assert not validate_answer_claims(claims, source, [])['supported']


def test_explicit_answer_component_cannot_inherit_different_component():
    source = [{'source_id':'s', 'relevant_snippet':'Pin cao áp VF8 bảo hành 10 năm.'}]
    claims = extract_numeric_claims('Ắc quy VF8 bảo hành 10 năm.', source, 'VF8 pin cao áp', 'Bảo hành pin VF8?')
    assert not validate_answer_claims(claims, source, [])['supported']
