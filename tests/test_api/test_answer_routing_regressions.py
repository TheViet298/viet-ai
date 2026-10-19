"""Semantic contracts for failures observed in the answer coverage audit."""
import pytest

from src.agents.nodes.triage_node import classify_request_kind
from src.models.db_models import ChatSession, CaseBrief
from src.services.chat_language import detect_language
from src.services.conversation_context import ConversationContext, understand_turn

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']


@pytest.mark.parametrize('question,expected', [
    ('Hệ thống hỗ trợ người lái ADAS trên xe VF 8 bao gồm những tính năng cơ bản nào?', 'faq'),
    ('Xe VF8 bao gom nhung tinh nang ADAS nao?', 'faq'),
    ('Xe VF8 báo lỗi CC01', 'incident'),
    ('Xe VF8 bao loi CC01', 'incident'),
])
def test_information_is_not_a_fault_report(question, expected):
    assert classify_request_kind(question) == expected


@pytest.mark.parametrize('question,expected', [
    ('Cách tự đấu dây điện để can thiệp tăng công suất pin xe điện tại nhà?', 'vi'),
    ('Cach can thiep he thong dien tai nha?', 'vi'),
    ('Can you explain charging at home?', 'en'),
    ('What is the price in Hà Nội?', 'en'),
])
def test_language_is_decided_from_sentence(question, expected):
    assert detect_language(question) == expected


@pytest.mark.asyncio
async def test_model_recall_is_not_a_color_question():
    turn = await understand_turn('Tôi đã nói tôi sử dụng mẫu xe nào?', ConversationContext(subject='VF8'), [], {})
    assert turn.goal != 'appearance'


@pytest.mark.asyncio
async def test_ownership_correction_is_not_an_unsolicited_comparison(client, customer_db):
    for text in ['Hãy nhớ xe của tôi là VF8 Plus, tôi ở Hà Nội',
                 'Không phải VF8, xe tôi là VF5, tôi ở Đà Nẵng']:
        result = await client.post('/api/v1/customer/chat', json={'session_id': 'correct-owned', 'message': text})
        assert result.status_code == 200
    data = result.json()['data']
    assert data['vehicle_comparison'] is False
    assert not data['vehicle_cards']
    assert 'VF5' in data['message']


@pytest.mark.asyncio
@pytest.mark.parametrize('question', ['Ứng dụng VinFast có tính năng gì?',
                                    'Chính sách bảo hành pin và lịch bảo dưỡng định kỳ'])
async def test_generic_service_after_car_keeps_generic_scope(client, customer_db, question):
    await client.post('/api/v1/customer/chat', json={'session_id': 'generic-after-car', 'message': 'Tư vấn VF8'})
    response = await client.post('/api/v1/customer/chat', json={'session_id': 'generic-after-car', 'message': question})
    assert response.status_code == 200
    data = response.json()['data']
    assert data['citations']
    assert 'chưa tra cứu' not in data['message']
    customer_db.expire_all()
    state = customer_db.get(ChatSession, 'generic-after-car').memory_states['generic-after-car']
    assert state['conversation_context']['subject'] is None


@pytest.mark.asyncio
async def test_booking_through_app_does_not_add_unrequested_charging_features():
    from src.services.faq_questions import faq_parts
    assert not faq_parts('Hướng dẫn đặt lịch bảo dưỡng qua ứng dụng')
    context = ConversationContext(subject='VF8', active_goal='overview', topic='Tư vấn VF8')
    turn = await understand_turn('Hướng dẫn đặt lịch bảo dưỡng qua ứng dụng', context, [], {})
    assert 'Tính năng sạc' not in turn.resolved_query
    assert not faq_parts(turn.resolved_query)


@pytest.mark.asyncio
@pytest.mark.parametrize('question,subject', [
    ('Biểu phí sạc tại trạm công cộng', None),
    ('Bảo hành pin xe VF8 của tôi bao lâu?', 'VF8'),
    ('Bảo hành pin xe của tôi bao lâu?', 'VF8'),
    ('Màu xe VF8 có những màu nào?', 'VF8'),
])
async def test_explicit_question_scope(question, subject):
    context = ConversationContext(subject='VF8', active_goal='overview', topic='Tư vấn VF8')
    turn = await understand_turn(question, context, [], {})
    assert turn.subject == subject


@pytest.mark.asyncio
async def test_incident_correction_after_status_is_acknowledged(client, customer_db):
    session = 'correct-incident-status'
    messages = ['Xe VF5 của tôi không sạc được, mã lỗi CC01', 'Trụ P01 tại Vincom Metropolis',
                'Xe báo lỗi CC01, pin còn 35%', 'Tôi đã nói rồi, còn thiếu gì?',
                'Không phải trụ P01, trụ P02', 'Xe không còn báo CC01 nữa', 'Tôi đã dừng ở nơi an toàn']
    case_id = None
    for number, text in enumerate(messages):
        result = await client.post('/api/v1/customer/chat', json={'session_id': session, 'message': text})
        assert result.status_code == 200
        data = result.json()['data']
        case_id = case_id or data['case_id']
        assert data['case_id'] == case_id
        if number >= 4:
            assert 'chưa tra cứu' not in data['message']
            assert not data['citations']
        if number == 4:
            assert 'P02' in data['message']
        customer_db.expire_all()
        state = customer_db.get(ChatSession, session).memory_states[session]
        assert state['conversation_context']['active_goal'] == 'incident'
    brief = customer_db.query(CaseBrief).filter_by(case_id=case_id).first()
    assert brief.captured_fields['charger_id'] == 'P02'
    assert 'error_code' not in brief.captured_fields
