import pytest
from src.services.conversation_context import ConversationContext, ConversationFact, understand_turn


def test_tomorrow_morning_shorthand_preserves_date_and_time_preference():
    from src.services.conversation_context import user_updates
    updates = user_updates('Sáng mai ở Hà Nội')
    assert updates['date'] == 'ngay mai'
    assert updates['time_window'] == 'sáng'


@pytest.mark.asyncio
@pytest.mark.parametrize('query', ['Lịch bảo dưỡng VF8 như thế nào?', 'Chu kỳ bảo dưỡng định kỳ VF8 là bao nhiêu km?'])
async def test_maintenance_intervals_do_not_become_appointment_requests(query):
    turn = await understand_turn(query, ConversationContext(), [], {})
    assert turn.goal == 'maintenance'
    assert 'Đặt lịch' not in turn.resolved_query
    assert turn.source_need == 'manual'


@pytest.mark.asyncio
async def test_explicit_maintenance_booking_uses_guide():
    turn = await understand_turn('Tôi muốn đặt lịch bảo dưỡng VF8', ConversationContext(), [], {})
    assert turn.source_need == 'guide'


@pytest.mark.asyncio
@pytest.mark.parametrize('text,goal,cost,source', [
    ('tôi muốn hỏi về vf7', 'overview', None, 'catalog'),
    ('tu van vf7', 'overview', None, 'catalog'),
    ('Cho tôi thông tin VF8', 'overview', None, 'catalog'),
    ('Tìm hiểu xe VF6', 'overview', None, 'catalog'),
    ('Giá sạc VF8 bao nhiêu?', 'charging_network', 'charging', 'policy'),
    ('Chi phí thuê pin VF8?', 'charging_network', 'battery_rental', 'policy'),
    ('Hướng dẫn đăng nhập ứng dụng VinFast', 'application', None, 'guide'),
    ('VF7 đi bao xa?', 'range', None, 'catalog'),
    ('Sức chứa VF8 bao nhiêu?', 'capacity', None, 'catalog'),
    ('Bao lâu sạc đầy VF8?', 'charging', None, 'manual'),
    ('Tôi muốn trải nghiệm lái VF7', 'test_drive', None, 'catalog'),
    ('Đánh giá VF7', 'overview', None, 'catalog'),
    ('Tôi muốn tìm hiểu VF7', 'overview', None, 'catalog'),
    ('Bạn tư vấn giúp tôi về VF7 nhé', 'overview', None, 'catalog'),
    ('VF7 có những phiên bản nào?', 'overview', None, 'catalog'),
    ('Tôi muốn mua VF7', 'overview', None, 'catalog'),
    ('Xin chào, tôi muốn hỏi về VF7', 'overview', None, 'catalog'),
    ('Thời gian sạc đầy VF8 là bao nhiêu?', 'charging', None, 'manual'),
    ('Sạc VF8 từ 10% đến 70% mất mấy phút?', 'charging', None, 'manual'),
    ('Tôi muốn hỏi thời gian nạp đầy pin VF8', 'charging', None, 'manual'),
    ('VF8 chạy được bao xa khi sạc đầy?', 'range', None, 'catalog'),
    ('VF8 chứa được bao nhiêu điện trong pin?', 'capacity', None, 'catalog'),
    ('Sạc VF8 giá bao nhiêu?', 'charging_network', 'charging', 'policy'),
    ('Thay pin VF8 giá bao nhiêu?', 'maintenance', 'repair', 'policy'),
    ('Bảo dưỡng VF8 giá bao nhiêu?', 'maintenance', 'maintenance', 'policy'),
])
async def test_explicit_question_replaces_quote(text, goal, cost, source):
    turn = await understand_turn(text, ConversationContext(active_goal='quote', topic='Giá VF8 Plus', subject='VF8'), [], {})
    assert turn.goal == goal
    assert turn.move == 'new_question'
    assert turn.cost_subject == cost
    assert turn.source_need == source
    assert 'Giá niêm yết' not in turn.resolved_query


@pytest.mark.asyncio
async def test_code_correction_retracts_old_and_accepts_new():
    context = ConversationContext(active_goal='incident', facts={'error_code': ConversationFact(value='CC01', source_turn=1)})
    turn = await understand_turn('Không phải CC01, tôi nói CC02', context, [], {})
    assert turn.updates['error_code'] == 'CC02'
    assert 'error_code' in turn.retracted_fields


@pytest.mark.asyncio
@pytest.mark.parametrize('question', ['Nếu VF8 mất phanh thì cần làm gì?', 'neu vf8 mat phanh thi can lam gi'])
async def test_hypothetical_new_topic_does_not_continue_quote(question):
    turn = await understand_turn(question, ConversationContext(active_goal='quote', topic='Giá VF8 Plus', subject='VF8'), [], {})
    assert turn.goal is None
    assert turn.move == 'new_question'
    assert 'Giá niêm yết' not in turn.resolved_query
