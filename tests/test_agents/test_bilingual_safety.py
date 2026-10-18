import pytest
from src.agents.guardrails import evaluate_hard_safety


@pytest.mark.parametrize('text', [
    'VF7 có lửa ở cổng sạc', 'Có ngọn lửa ở cổng sạc VF7',
    'My VF8 is emitting smoke from the battery compartment',
    'The brakes on my VF7 have failed while I am on the highway',
    'There are flames at the charging port of my VF7',
    'My car is not smoking, but the brakes have failed',
    "My brakes don't work", 'My brakes are not responding.',
])
def test_current_danger_is_critical_in_both_languages(text):
    assert evaluate_hard_safety(text)[0] is True


@pytest.mark.parametrize('text', [
    'My VF7 is not smoking or on fire; I just want to ask about its price',
    'My car is not on fire. What should I do if smoke comes from the battery?',
    'Yesterday my car was smoking, but it is fine now',
    'Xe không có khói, không cháy, tôi muốn hỏi giá VF7',
])
def test_denied_or_hypothetical_danger_is_not_current(text):
    assert evaluate_hard_safety(text)[0] is False


def test_negated_hazards_do_not_turn_price_question_into_incident():
    from src.agents.nodes.triage_node import classify_request_kind
    assert classify_request_kind('Xe VF7 không có khói, không cháy, tôi muốn hỏi giá') == 'faq'
