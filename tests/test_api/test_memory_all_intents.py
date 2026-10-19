"""Accepted HTTP turns, persisted memory and history for every intent family."""
import json
from pathlib import Path

import pytest

from src.models.db_models import ChatSession, Message, User

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']
CASES = json.loads((Path(__file__).resolve().parents[2] / 'eval/datasets/memory_intent_audit_v1.json').read_text(encoding='utf-8'))


@pytest.mark.asyncio
@pytest.mark.parametrize('case', CASES, ids=lambda case: case['id'])
async def test_all_intent_followups_persist_and_survive_session_reload(client, customer_db, case):
    session_id = 'memory-audit-' + case['id']
    first_case_id = None
    for number, message in enumerate([case['seed'], case['followup']], 1):
        response = await client.post('/api/v1/customer/chat', json={
            'session_id': session_id, 'message': message, 'request_id': session_id + str(number)})
        assert response.status_code == 200, response.text
        data = response.json()['data']
        if number == 1:
            first_case_id = data['case_id']
        elif first_case_id:
            assert data['case_id'] == first_case_id
        customer_db.expire_all()
        stored = customer_db.get(ChatSession, session_id)
        state = stored.memory_states[session_id]
        context = state['conversation_context']
        assert context['active_goal'] == (case.get('final_goal', case['goal']) if number == 2 else case['goal'])
        assert state['turn'] == number
        assert state['latest_user_message'] == message
        assert state['response'] == data['message']
        if number == 2:
            assert context['subject'] == case['model']
            for key, expected in case.get('facts', {}).items():
                assert context['facts'][key]['value'] == expected
        # Evict the ORM object between turns; the next request must load DB state.
        customer_db.expunge(stored)
    history = (await client.get(f'/api/v1/customer/sessions/{session_id}/history')).json()['data']['messages']
    assert [m['content'] for m in history if m['sender'] == 'CUSTOMER'] == [case['seed'], case['followup']]
    assert history[-1]['content'] == data['message']
    assert history[-1]['vehicle_cards'] == data['vehicle_cards']
    if case.get('emergency'):
        assert data['show_emergency_banner'] is True
        assert data['priority'] == 'CRITICAL'
    if case['goal'] not in {'incident', 'complaint'}:
        assert data['case_id'] is None
    if case['id'] in {'test-drive', 'maintenance-booking'}:
        assert state['conversation_progress']['state'] == 'external_action_required'
        assert state['conversation_progress']['action_receipt'] is None


@pytest.mark.asyncio
@pytest.mark.parametrize('case', CASES, ids=lambda case: case['id'])
async def test_new_session_does_not_receive_other_intents_memory(client, customer_db, case):
    first = 'memory-old-' + case['id']
    await client.post('/api/v1/customer/chat', json={'session_id': first, 'message': case['seed']})
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'memory-new-' + case['id'], 'message': 'Xin chào'})
    assert response.status_code == 200
    data = response.json()['data']
    assert not data['vehicle_cards']
    assert not data['show_emergency_banner']
    customer_db.expire_all()
    state = customer_db.get(ChatSession, 'memory-new-' + case['id']).memory_states['memory-new-' + case['id']]
    assert state['conversation_context']['subject'] is None
    assert state['conversation_context']['facts'] == {}
    assert state['case_id'] is None


@pytest.mark.asyncio
@pytest.mark.parametrize('case', CASES, ids=lambda case: case['id'])
async def test_other_customer_cannot_continue_another_owners_memory(client, customer_db, case):
    from src.main import app
    from src.services.auth import get_optional_user
    session_id = 'memory-owner-' + case['id']
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': session_id, 'message': case['seed'], 'request_id': 'owner-request'})
    assert response.status_code == 200
    customer_db.expire_all()
    before = customer_db.get(ChatSession, session_id).memory_states
    other = User(id='memory-other', username='memory-other', password_hash='unused', role='CUSTOMER')
    customer_db.add(other)
    customer_db.commit()
    app.dependency_overrides[get_optional_user] = lambda: other
    result = await client.post('/api/v1/customer/chat', json={
        'session_id': session_id, 'message': case['seed'], 'request_id': 'owner-request'})
    assert result.status_code == 403
    customer_db.expire_all()
    assert customer_db.get(ChatSession, session_id).memory_states == before


@pytest.mark.asyncio
@pytest.mark.parametrize('case', CASES, ids=lambda case: case['id'])
async def test_duplicate_request_is_a_receipt_not_another_memory_turn(client, customer_db, case):
    session_id = 'memory-replay-' + case['id']
    payload = {'session_id': session_id, 'message': case['seed'], 'request_id': session_id + '-1'}
    first = await client.post('/api/v1/customer/chat', json=payload)
    assert first.status_code == 200
    customer_db.expire_all()
    before = customer_db.get(ChatSession, session_id).memory_states
    replay = await client.post('/api/v1/customer/chat', json=payload)
    assert replay.status_code == 200
    assert replay.json() == first.json()
    customer_db.expire_all()
    assert customer_db.get(ChatSession, session_id).memory_states == before
    assert customer_db.query(Message).filter_by(session_id=session_id).count() == 2
    conflict = await client.post('/api/v1/customer/chat', json={**payload, 'message': case['followup']})
    assert conflict.status_code == 409
    customer_db.expire_all()
    assert customer_db.get(ChatSession, session_id).memory_states == before


@pytest.mark.asyncio
@pytest.mark.parametrize('case', CASES, ids=lambda case: case['id'])
async def test_failed_followup_rolls_back_every_intents_memory(client, customer_db, monkeypatch, case):
    from src.api import customer
    session_id = 'memory-rollback-' + case['id']
    response = await client.post('/api/v1/customer/chat', json={'session_id': session_id, 'message': case['seed']})
    assert response.status_code == 200
    customer_db.expire_all()
    before = json.loads(json.dumps(customer_db.get(ChatSession, session_id).memory_states))
    async def fail_after_write(payload, current_user, db):
        db.add(Message(id='failed-followup', session_id=session_id, sender_type='CUSTOMER', content=payload.message))
        session = db.get(ChatSession, session_id)
        session.memory_states = {**session.memory_states, session_id: {
            **session.memory_states[session_id], 'turn': 999,
            'conversation_context': {'active_goal': 'quote', 'subject': 'VF9'}}}
        db.flush()
        raise RuntimeError('synthetic memory persistence failure')
    monkeypatch.setattr(customer, '_process_customer_chat', fail_after_write)
    with pytest.raises(RuntimeError, match='synthetic memory persistence failure'):
        await client.post('/api/v1/customer/chat', json={'session_id': session_id, 'message': case['followup']})
    customer_db.expire_all()
    stored = customer_db.get(ChatSession, session_id)
    assert stored.memory_states == before
    assert stored.lease_token is None
    assert customer_db.query(Message).filter_by(session_id=session_id).count() == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('seed,followup,field,value', [
    ('Giá VF8 Plus ở Hà Nội?', 'Không phải Plus, tôi chọn Eco', 'version', 'Eco'),
    ('Giá VF8 Plus ở Hà Nội?', 'Không phải Hà Nội, đăng ký ở Đà Nẵng', 'city', 'Đà Nẵng'),
    ('Bảo hành pin VF8 bao lâu?', 'Không phải pin cao áp, tôi hỏi ắc quy 12V', 'component', 'ắc quy 12V'),
    ('Bảo hành pin VF8 đời 2024?', 'Không phải đời 2024, xe đời 2025', 'year', '2025'),
    ('Giá VF8 Plus ở Hà Nội?', 'Không phải VF8 Plus, tôi chọn VF5 Eco', 'version', 'Eco'),
    ('Giá VF8 Plus ở Hà Nội?', 'Không phải TP.HCM, tôi đăng ký ở Đà Nẵng', 'city', 'Đà Nẵng'),
])
async def test_api_correction_persists_affirmed_value_not_denied_value(client, customer_db, seed, followup, field, value):
    for message in [seed, followup]:
        response = await client.post('/api/v1/customer/chat', json={'session_id': 'memory-correction', 'message': message})
        assert response.status_code == 200
    customer_db.expire_all()
    context = customer_db.get(ChatSession, 'memory-correction').memory_states['memory-correction']['conversation_context']
    assert context['facts'][field]['value'] == value


@pytest.mark.asyncio
async def test_long_conversation_compaction_keeps_latest_subject_and_version(client, customer_db):
    for message in ['Giá VF8 Plus tại Hà Nội?'] + ['Tôi đã nói rồi, còn thiếu gì?'] * 6 + ['Tư vấn VF7 Eco']:
        response = await client.post('/api/v1/customer/chat', json={'session_id': 'memory-long', 'message': message})
        assert response.status_code == 200
    customer_db.expire_all()
    state = customer_db.get(ChatSession, 'memory-long').memory_states['memory-long']
    assert state['turn'] == 8
    assert len(state['messages']) <= 10
    assert state['summary_evidence']
    assert state['conversation_context']['subject'] == 'VF7'
    assert state['conversation_context']['facts']['version']['value'] == 'Eco'
    assert {card['model'] for card in response.json()['data']['vehicle_cards']} == {'VF7'}


@pytest.mark.asyncio
@pytest.mark.parametrize('message,plan', [
    ('Không phải thuê pin, tôi mua kèm pin', 'mua kèm pin'),
    ('Không mua kèm pin, tôi thuê pin', 'thuê pin'),
    ('Tôi thuê pin', 'thuê pin'),
])
async def test_api_battery_plan_correction_keeps_quote_context(client, customer_db, message, plan):
    for text in ['Giá lăn bánh VF8 Plus ở Hà Nội?', message]:
        response = await client.post('/api/v1/customer/chat', json={
            'session_id': 'memory-battery-plan', 'message': text})
        assert response.status_code == 200
    customer_db.expire_all()
    state = customer_db.get(ChatSession, 'memory-battery-plan').memory_states['memory-battery-plan']
    assert state['conversation_context']['active_goal'] == 'quote'
    assert state['turn_understanding']['cost_subject'] == 'vehicle_purchase'
    assert state['conversation_context']['facts']['battery']['value'] == plan
    assert state['conversation_context']['facts']['version']['value'] == 'Plus'


@pytest.mark.asyncio
@pytest.mark.parametrize('message', ['Tôi muốn tìm hiểu dịch vụ thuê pin', 'Giá thuê pin bao nhiêu?'])
async def test_api_rental_service_question_can_leave_quote(client, customer_db, message):
    for text in ['Giá lăn bánh VF8 Plus ở Hà Nội?', message]:
        response = await client.post('/api/v1/customer/chat', json={'session_id': 'rental-switch', 'message': text})
        assert response.status_code == 200
    customer_db.expire_all()
    context = customer_db.get(ChatSession, 'rental-switch').memory_states['rental-switch']['conversation_context']
    assert context['active_goal'] == 'charging_network'


@pytest.mark.asyncio
@pytest.mark.parametrize('message,goal', [
    ('Tôi muốn đặt lịch bảo dưỡng VF8 mua kèm pin', 'maintenance'),
    ('Tôi muốn lái thử VF8 mua kèm pin', 'test_drive'),
    ('Bảo hành xe mua kèm pin bao lâu?', 'warranty'),
])
async def test_api_explicit_service_goal_wins_over_battery_slot(client, customer_db, message, goal):
    for text in ['Giá lăn bánh VF8 Plus ở Hà Nội?', message]:
        response = await client.post('/api/v1/customer/chat', json={'session_id': 'battery-service-switch', 'message': text})
        assert response.status_code == 200
    customer_db.expire_all()
    context = customer_db.get(ChatSession, 'battery-service-switch').memory_states['battery-service-switch']['conversation_context']
    assert context['active_goal'] == goal
