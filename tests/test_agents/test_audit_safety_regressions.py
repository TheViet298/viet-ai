"""Natural symptom wording must preserve the deterministic safety workflow."""
import pytest

from src.agents.guardrails import evaluate_hard_safety


@pytest.mark.parametrize('text,rule', [
    ('The accelerator pedal on my VF8 is stuck while I am driving.', 'ACCELERATOR_JAM'),
    ('A tire on my VF8 has just burst on the highway.', 'TIRE_BURST'),
    ('My VF7 brakes have stopped working while I am driving.', 'BRAKE_FAILURE'),
    ('The brake pedal in my VF8 goes all the way to the floor while I am driving.', 'BRAKE_FAILURE'),
    ('Chân phanh VF8 của tôi sát sàn khi đang lái xe.', 'BRAKE_FAILURE'),
    ('Bàn đạp ga trên chiếc VF8 của tôi bị kẹt trong khi tôi đang lái xe.', 'ACCELERATOR_JAM'),
    ('Lốp trên chiếc VF8 của tôi vừa bị nổ trên đường cao tốc.', 'TIRE_BURST'),
    ('Phanh VF7 của tôi đã ngừng hoạt động trong khi tôi đang lái xe.', 'BRAKE_FAILURE'),
])
def test_natural_current_symptom_triggers_its_safety_rule(text, rule):
    assert evaluate_hard_safety(text) == (True, rule, 'CRITICAL')


@pytest.mark.parametrize('text', [
    'My VF8 is not emitting smoke. I only want to ask about its price.',
    'There are no flames at the charging port of my VF7. I only want its price.',
    'My VF8 is not emitting smoke or burning.',
    'My brakes have not stopped working. I only want the price.',
    'The accelerator pedal on my VF8 is not stuck.',
    'A tire on my VF8 has not burst.',
    'Chân phanh VF8 của tôi không sát sàn.',
    'Chân phanh VF8 của tôi không chạm xuống sàn.',
    'Chân phanh VF8 của tôi chưa xuống tận sàn.',
    'Bàn đạp ga trên VF8 của tôi không bị kẹt.',
    'Lốp trên VF8 của tôi không bị nổ.',
    'Nếu chân phanh VF8 của tôi sát sàn thì cần làm gì?',
    'What should I do if the accelerator pedal on my VF8 is stuck?',
])
def test_denied_or_hypothetical_symptom_does_not_create_current_danger(text):
    assert not evaluate_hard_safety(text)[0]


@pytest.mark.parametrize('text,rule', [
    ('My VF8 is not emitting smoke, but my brakes have stopped working.', 'BRAKE_FAILURE'),
    ('There are no flames, but the accelerator pedal on my VF8 is stuck.', 'ACCELERATOR_JAM'),
    ('Xe tôi mất phanh và lốp không bị nổ', 'BRAKE_FAILURE'),
    ('Lốp xe VF8 bị nổ và chân phanh không sát sàn', 'TIRE_BURST'),
])
def test_denial_of_one_hazard_preserves_another_current_hazard(text, rule):
    assert evaluate_hard_safety(text) == (True, rule, 'CRITICAL')
