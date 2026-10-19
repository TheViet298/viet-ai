"""Memory contracts for every goal, independent of a model provider."""
import json
from pathlib import Path

import pytest

from src.services.conversation_context import ConversationContext, ConversationFact, apply_turn, understand_turn


CASES = json.loads((Path(__file__).resolve().parents[2] / 'eval/datasets/memory_intent_audit_v1.json').read_text(encoding='utf-8'))
GOALS = {case['goal']: case for case in CASES}


def test_memory_matrix_covers_declared_business_intents():
    from typing import get_args
    from src.agents.state import IntentType
    assert {case['intent'] for case in CASES} == set(get_args(IntentType))


@pytest.mark.asyncio
@pytest.mark.parametrize('case', CASES, ids=lambda case: case['id'])
async def test_goal_followup_remembers_subject_and_current_facts(case):
    context = ConversationContext()
    for number, text in enumerate([case['seed'], case['followup']], 1):
        turn = await understand_turn(text, context, [], {})
        context = apply_turn(context, turn, number)
        assert context.active_goal == (case.get('final_goal', case['goal']) if number == 2 else case['goal'])
    assert context.subject == case['model']
    for key, expected in case.get('facts', {}).items():
        assert context.facts[key].value == expected


@pytest.mark.asyncio
@pytest.mark.parametrize('previous', sorted(GOALS))
@pytest.mark.parametrize('target', sorted(GOALS))
async def test_explicit_goal_switch_does_not_keep_old_operational_state(previous, target):
    context = ConversationContext(active_goal=previous, subject='VF8', topic=GOALS[previous]['seed'],
        facts={'city': ConversationFact(value='OLD-CITY', source_turn=1),
               'version': ConversationFact(value='Plus', source_turn=1)},
        action={'state': 'cancelled_intent'}, pending_question={'slots': ['old_slot']},
        last_answer=[{'turn': 1, 'claims': [{'topic': previous, 'value': 'OLD-ANSWER'}]}])
    turn = await understand_turn(GOALS[target]['seed'], context, [], {})
    result = apply_turn(context, turn, 2)
    assert result.active_goal == target, turn.model_dump()
    if previous != target:
        assert all(fact.value != 'OLD-CITY' for fact in result.facts.values())
        assert result.pending_question == {}
        assert result.action == {}
        assert result.last_answer == []


@pytest.mark.asyncio
@pytest.mark.parametrize('goal', ['quote', 'test_drive', 'warranty', 'maintenance', 'range', 'charging', 'capacity', 'appearance'])
async def test_switching_model_clears_model_specific_facts(goal):
    context = ConversationContext(active_goal=goal, subject='VF8', topic=GOALS[goal]['seed'],
        facts={key: ConversationFact(value=value, source_turn=1) for key, value in
               {'version': 'Plus', 'year': '2024', 'battery': 'mua kèm pin'}.items()})
    result = apply_turn(context, await understand_turn('Còn VF5 thì sao?', context, [], {}), 2)
    assert result.subject == 'VF5'
    assert not {'version', 'year', 'battery'} & result.facts.keys()


@pytest.mark.asyncio
@pytest.mark.parametrize('goal,question,field', [
    ('quote', 'Tôi chưa biết phiên bản', 'version'),
    ('warranty', 'Tôi không nhớ đời xe', 'year'),
    ('test_drive', 'Tôi chưa biết nơi đăng ký', 'city'),
])
async def test_unknown_fact_replaces_previous_confirmed_value(goal, question, field):
    context = ConversationContext(active_goal=goal, subject='VF8', topic=GOALS[goal]['seed'],
        facts={field: ConversationFact(value='old value', source_turn=1)})
    result = apply_turn(context, await understand_turn(question, context, [], {}), 2)
    assert result.facts[field].value is None
    assert result.facts[field].status == 'unknown'


CORRECTIONS = [
    ('quote', 'Không phải VF8, tôi hỏi VF5', 'model', 'VF5'),
    ('quote', 'Không phải Plus, tôi chọn Eco', 'version', 'Eco'),
    ('quote', 'Không phải Hà Nội, đăng ký ở Đà Nẵng', 'city', 'Đà Nẵng'),
    ('warranty', 'Không phải pin cao áp, tôi hỏi ắc quy 12V', 'component', 'ắc quy 12V'),
    ('warranty', 'Không phải đời 2024, xe đời 2025', 'year', '2025'),
    ('quote', 'Không mua kèm pin, tôi thuê pin', 'battery', 'thuê pin'),
    ('quote', 'VF5, không phải VF8', 'model', 'VF5'),
    ('warranty', 'Ắc quy 12V, không phải pin cao áp', 'component', 'ắc quy 12V'),
    ('quote', 'Không phải VF8 Plus, tôi chọn VF5 Eco', 'version', 'Eco'),
    ('quote', 'Không phải TP.HCM, tôi đăng ký ở Đà Nẵng', 'city', 'Đà Nẵng'),
]


@pytest.mark.asyncio
@pytest.mark.parametrize('goal,text,field,value', CORRECTIONS)
async def test_denied_old_value_is_not_saved_as_the_correction(goal, text, field, value):
    context = ConversationContext(active_goal=goal, subject='VF8', topic=GOALS[goal]['seed'])
    turn = await understand_turn(text, context, [], {})
    assert turn.updates[field] == value
    result = apply_turn(context, turn, 2)
    assert result.facts[field].value == value


@pytest.mark.asyncio
@pytest.mark.parametrize('text,field,value', [
    ('Trụ P02', 'charger_id', 'P02'),
    ('Tại Vincom Metropolis', 'station_location', 'Vincom Metropolis'),
    ('Trụ P02 tại Vincom Metropolis', 'charger_id', 'P02'),
    ('Trạm sạc Vincom Metropolis', 'station_location', 'Vincom Metropolis'),
    ('Tôi ở đường Trần Duy Hưng', 'current_location', 'đường Trần Duy Hưng'),
])
async def test_incident_slot_only_followup_preserves_goal(text, field, value):
    context = ConversationContext(active_goal='incident', subject='VF8',
        facts={'error_code': ConversationFact(value='CC01', source_turn=1)})
    turn = await understand_turn(text, context, [], {})
    assert turn.goal == 'incident'
    assert turn.updates[field] == value
    assert apply_turn(context, turn, 2).facts['error_code'].value == 'CC01'


@pytest.mark.asyncio
@pytest.mark.parametrize('field,old_value,denial', [
    ('version', 'Plus', 'Không phải Plus'),
    ('city', 'Hà Nội', 'Không phải Hà Nội'),
    ('year', '2024', 'Không phải đời 2024'),
    ('battery', 'mua kèm pin', 'Không mua kèm pin'),
    ('component', 'pin cao áp', 'Không phải pin cao áp'),
    ('model', 'VF8', 'Không phải VF8'),
])
async def test_denial_without_replacement_retracts_old_fact(field, old_value, denial):
    context = ConversationContext(active_goal='quote', subject='VF8',
        facts={field: ConversationFact(value=old_value, source_turn=1)})
    turn = await understand_turn(denial, context, [], {})
    updated = apply_turn(context, turn, 2)
    assert updated.facts[field].status == 'retracted'
    assert updated.facts[field].value is None
    if field == 'model':
        assert updated.subject is None


@pytest.mark.asyncio
@pytest.mark.parametrize('question,category,area,vehicle', [
    ('còn showroom thì sao', 'SHOWROOM', 'Huế', 'TWO_WHEELER'),
    ('chỉ đường tới chỗ đầu tiên', 'CHARGING_STATION', 'Huế', 'TWO_WHEELER'),
    ('tìm trạm sạc gần tôi', 'CHARGING_STATION', None, 'TWO_WHEELER'),
    ('tìm trạm sạc ô tô ở Hà Nội', 'CHARGING_STATION', 'Hà Nội', 'CAR'),
])
async def test_location_memory_keeps_category_area_and_explicit_vehicle_switch(question, category, area, vehicle):
    from src.services.nearby_intent import classify_location_request
    previous = {'category': 'CHARGING_STATION', 'vehicle_type': 'TWO_WHEELER', 'area_text': 'Huế'}
    action = await classify_location_request(question, previous)
    assert action['category'] == category
    assert action['area_text'] == area
    assert action['vehicle_type'] == vehicle


@pytest.mark.asyncio
@pytest.mark.parametrize('question', ['không tìm trạm sạc nữa', 'Bảo hành pin bao lâu?', 'Giá VF8 Plus bao nhiêu?'])
async def test_location_memory_cannot_override_a_new_service_or_denied_request(question):
    from src.services.nearby_intent import classify_location_request
    previous = {'category': 'CHARGING_STATION', 'vehicle_type': 'CAR', 'area_text': 'Huế'}
    assert await classify_location_request(question, previous) is None


@pytest.mark.parametrize('goal,field', [
    ('quote', 'version'), ('test_drive', 'city'), ('test_drive', 'date'),
    ('maintenance', 'city'), ('maintenance', 'date'), ('warranty', 'year'),
])
def test_retracted_required_fact_is_missing_but_unknown_is_not_reasked(goal, field):
    from src.services.conversation_progress import derive_progress
    context = ConversationContext(active_goal=goal, topic='Tôi muốn đặt lịch bảo dưỡng VF8' if goal == 'maintenance' else '',
        facts={field: ConversationFact(value=None, source_turn=2, status='retracted')})
    assert field in derive_progress(context, {}, None, None).missing_fields
    context.facts[field].status = 'unknown'
    assert field not in derive_progress(context, {}, None, None).missing_fields


@pytest.mark.asyncio
@pytest.mark.parametrize('message,plan', [
    ('Không phải thuê pin, tôi mua kèm pin', 'mua kèm pin'),
    ('Không mua kèm pin, tôi thuê pin', 'thuê pin'),
    ('Tôi thuê pin', 'thuê pin'),
])
async def test_battery_plan_slot_correction_stays_in_vehicle_quote(message, plan):
    context = ConversationContext(active_goal='quote', subject='VF8', topic='Giá lăn bánh VF8?',
        facts={'version': ConversationFact(value='Plus', source_turn=1)})
    turn = await understand_turn(message, context, [], {})
    assert turn.goal == 'quote'
    assert turn.cost_subject == 'vehicle_purchase'
    result = apply_turn(context, turn, 2)
    assert result.facts['battery'].value == plan
    assert result.facts['version'].value == 'Plus'


@pytest.mark.asyncio
@pytest.mark.parametrize('message', ['Tôi muốn tìm hiểu dịch vụ thuê pin', 'Giá thuê pin bao nhiêu?'])
async def test_explicit_rental_service_question_can_leave_vehicle_quote(message):
    context = ConversationContext(active_goal='quote', subject='VF8')
    turn = await understand_turn(message, context, [], {})
    assert turn.goal == 'charging_network'
    assert turn.cost_subject == 'battery_rental'


@pytest.mark.asyncio
@pytest.mark.parametrize('message,goal', [
    ('Tôi muốn đặt lịch bảo dưỡng VF8 mua kèm pin', 'maintenance'),
    ('Tôi muốn lái thử VF8 mua kèm pin', 'test_drive'),
    ('Bảo hành xe mua kèm pin bao lâu?', 'warranty'),
])
async def test_battery_detail_does_not_block_an_explicit_goal_change(message, goal):
    turn = await understand_turn(message, ConversationContext(active_goal='quote', subject='VF8'), [], {})
    assert turn.goal == goal
