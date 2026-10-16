import pytest

from src.services.conversation_context import ConversationContext, apply_turn, understand_turn


@pytest.mark.asyncio
@pytest.mark.parametrize('question', ['vf8 plus có những màu gì', 'VF8 Plus mau nao?', 'Màu sắc ngoại thất VF8 Plus',
                                    'VF8 Plus có màu trắng không?', 'VF8 Plus co mau trang khong?'])
async def test_color_question_switches_away_from_pending_quote(question):
    context = ConversationContext(active_goal='quote', subject='VF8')
    turn = await understand_turn(question, context, [], {})
    assert turn.move == 'new_question'
    assert turn.goal == 'appearance'
    assert turn.subject == 'VF8'
    assert turn.updates['version'] == 'Plus'
    assert 'lăn bánh' not in turn.resolved_query
    assert not turn.needs_confirmation


@pytest.mark.asyncio
async def test_pending_quote_accepts_version_battery_and_city():
    context = ConversationContext(active_goal='quote', subject='VF8')
    turn = await understand_turn('VF8 Plus, mua kèm pin, Hà Nội', context, [], {})
    assert turn.move == 'supply_info'
    assert turn.goal == 'quote'
    assert turn.updates == {'model': 'VF8', 'version': 'Plus', 'battery': 'mua kèm pin', 'city': 'Hà Nội'}
    result = apply_turn(context, turn, 2)
    assert result.facts['city'].source_turn == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('text,move,goal', [
    ('Pin cao áp, không phải ắc quy 12V', 'correct', 'warranty'),
    ('500 hay 450 km đúng?', 'verify_claim', 'range'),
    ('Bạn vừa nói khoảng 500 km, tôi thấy nơi khác nói 450 km, cái nào đúng?', 'verify_claim', 'range'),
    ('Vậy giờ tôi cần làm gì?', 'ask_next_step', 'maintenance'),
    ('Toi da noi roi, con thieu gi?', 'ask_status', 'quote'),
    ('Xe tôi đang mất phanh', 'new_incident', 'incident'),
])
async def test_natural_moves(text, move, goal):
    context = ConversationContext(active_goal=goal if goal != 'incident' else 'quote', subject='VF8')
    turn = await understand_turn(text, context, [], {})
    assert (turn.move, turn.goal) == (move, goal)
    assert turn.original_text == text


@pytest.mark.asyncio
async def test_model_switch_scopes_version_and_unknown_is_not_reasked():
    context = ConversationContext(active_goal='quote', subject='VF8')
    context = apply_turn(context, await understand_turn('VF8 Plus ở Hà Nội', context, [], {}), 1)
    context = apply_turn(context, await understand_turn('Còn VF5 thì sao?', context, [], {}), 2)
    assert context.subject == 'VF5'
    assert 'version' not in context.facts
    context = apply_turn(context, await understand_turn('Tôi chưa biết phiên bản', context, [], {}), 3)
    assert context.facts['version'].status == 'unknown'


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['không sạc được', 'không di chuyển được', 'không mở được cửa'])
async def test_incident_with_correction_keeps_incident_precedence(fault):
    context = ConversationContext(active_goal='quote', subject='VF8')
    turn = await understand_turn('Không phải hỏi giá, xe tôi ' + fault, context, [], {})
    assert (turn.move, turn.goal, turn.subject) == ('new_incident', 'incident', None)


@pytest.mark.asyncio
async def test_cancelled_intent_can_be_reopened():
    context = ConversationContext(active_goal='test_drive', action={'state': 'cancelled_intent'})
    turn = await understand_turn('Giờ tôi muốn đặt lái thử VF8', context, [], {})
    assert apply_turn(context, turn, 3).action == {}


@pytest.mark.asyncio
async def test_denied_code_retracts_shared_fact():
    context = ConversationContext(active_goal='incident', subject='VF8')
    context = apply_turn(context, await understand_turn('Trụ báo CC01', context, [], {}), 1)
    context = apply_turn(context, await understand_turn('Xe không còn báo CC01 nữa', context, [], {}), 2)
    assert context.facts['error_code'].status == 'retracted'


@pytest.mark.asyncio
async def test_classifier_timeout_preserves_ambiguous_reference(monkeypatch):
    from src.services import agent_llm
    async def timeout(*args, **kwargs):
        return None
    monkeypatch.setattr(agent_llm, 'structured_call', timeout)
    turn = await understand_turn('Vậy được không?', ConversationContext(active_goal='quote', subject='VF8'), [], {})
    assert turn.goal == 'quote'
    assert turn.subject == 'VF8'
    assert turn.needs_confirmation
