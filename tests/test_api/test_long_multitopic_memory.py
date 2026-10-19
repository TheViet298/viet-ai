"""10–30 user messages in one real API session, asserting every accepted turn."""
import copy
import json
from pathlib import Path

import pytest

from src.models.db_models import ChatRequestRecord, ChatSession, Message

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']
SCENARIOS = json.loads((Path(__file__).resolve().parents[2] / 'eval/datasets/long_multitopic_memory_v1.json').read_text(encoding='utf-8'))


@pytest.mark.asyncio
async def test_history_preserves_turn_order_when_clock_does_not_advance(client, customer_db, monkeypatch):
    from datetime import UTC, datetime
    import src.api.customer as customer_api

    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            fixed = datetime(2040, 1, 1, tzinfo=UTC)
            return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)

    monkeypatch.setattr(customer_api, 'datetime', FixedClock)
    inputs = ['Tư vấn VF8', 'Thời tiết ngày mai thế nào?', 'Cảm ơn', 'Tư vấn VF3']
    expected = []
    for number, message in enumerate(inputs):
        response = await client.post('/api/v1/customer/chat', json={
            'session_id': 'fixed-clock-history', 'message': message, 'request_id': f'clock-{number}'})
        assert response.status_code == 200
        expected.extend([message, response.json()['data']['message']])
        history = (await client.get('/api/v1/customer/sessions/fixed-clock-history/history')).json()['data']['messages']
        assert [item['content'] for item in history] == expected
        assert [item['sender'] for item in history] == ['CUSTOMER', 'AGENT'] * (number + 1)


@pytest.mark.asyncio
@pytest.mark.parametrize('message', ['Xe không còn báo CC01 nữa', 'Tôi đã dừng ở nơi an toàn'])
async def test_incident_updates_keep_current_incident(message):
    from src.services.conversation_context import ConversationContext, ConversationFact, apply_turn, understand_turn
    context = ConversationContext(active_goal='incident', subject='VF5', topic='Xe VF5 báo CC01',
        facts={'error_code': ConversationFact(value='CC01', source_turn=1)})
    turn = await understand_turn(message, context, [], {})
    result = apply_turn(context, turn, 2)
    assert result.active_goal == 'incident'
    assert result.subject == 'VF5'
    assert result.facts['error_code'].status == ('retracted' if 'CC01' in message else 'confirmed')


def test_long_scenarios_have_thirty_turns_and_multiple_topics():
    assert len(SCENARIOS) == 3
    from tests.test_services.test_memory_intent_matrix import GOALS
    assert {step['goal'] for scenario in SCENARIOS for step in scenario['turns']} == set(GOALS)
    for scenario in SCENARIOS:
        assert len(scenario['turns']) == 30
        for length in (10, 20, 30):
            assert len({turn['goal'] for turn in scenario['turns'][:length]}) >= 2


@pytest.mark.asyncio
@pytest.mark.parametrize('delivery', ['continuous', 'reload', 'replay'])
@pytest.mark.parametrize('length', [10, 20, 30])
@pytest.mark.parametrize('scenario', SCENARIOS, ids=lambda case: case['id'])
async def test_long_multitopic_session_checks_each_turn(client, customer_db, tmp_path, scenario, length, delivery):
    session_id = f"long-{scenario['id']}-{length}-{delivery}"
    expected_users, rows = [], []
    case_ids = {}
    for number, step in enumerate(scenario['turns'][:length], 1):
        payload = {'session_id': session_id, 'message': step['message'], 'request_id': f'{session_id}-{number}'}
        if step.get('language'):
            payload['language'] = 'en' if step['language'] == 'vi' else 'vi'
        response = await client.post('/api/v1/customer/chat', json=payload)
        assert response.status_code == 200, f"{session_id} turn {number}: {response.text}"
        data = response.json()['data']
        if step.get('case_group'):
            assert data['case_id']
            assert data['case_id'] == case_ids.setdefault(step['case_group'], data['case_id'])
        expected_users.append(step['message'])
        customer_db.expire_all()
        stored = customer_db.get(ChatSession, session_id)
        state = stored.memory_states[session_id]
        context = state['conversation_context']
        cards = [[card['model'], card['variant']] for card in data['vehicle_cards']]
        rows.append({'turn': number, 'input': step['message'], 'goal': context['active_goal'],
                     'subject': context['subject'], 'facts': context['facts'], 'cards': cards,
                     'language': data['language'], 'response': data['message'],
                     'case_id': data['case_id'], 'emergency': data['show_emergency_banner'],
                     'buffer_messages': len(state['messages']),
                     'summary_evidence_count': len(state.get('summary_evidence', []))})
        (tmp_path / 'transcript.json').write_text(json.dumps({'session': session_id, 'turns': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
        label = f"{session_id} turn {number} ({step['message']}): {context}"
        assert context['active_goal'] == step['goal'], label
        if 'model' in step:
            assert context['subject'] == step['model'], label
        for field, value in step.get('facts', {}).items():
            assert context['facts'].get(field, {}).get('value') == value, label
            assert context['facts'][field]['status'] == 'confirmed', label
        for field, status in step.get('statuses', {}).items():
            assert context['facts'][field]['status'] == status, label
        for field in step.get('absent_facts', []):
            assert field not in context['facts'], label
        if 'cards' in step:
            assert cards == step['cards'], label
        if 'comparison' in step:
            assert data['vehicle_comparison'] is step['comparison'], label
        if step.get('language'):
            assert data['language'] == step['language'], label
        if step.get('progress'):
            assert state['conversation_progress']['state'] == step['progress'], label
        if step.get('no_action_receipt'):
            assert state['conversation_progress']['action_receipt'] is None
        for heading in step.get('headings', []):
            assert data['message'].count('### ' + heading) == 1, label
        if step.get('emergency'):
            assert data['show_emergency_banner'] is True, label
            assert data['priority'] == 'CRITICAL', label
        assert state['turn'] == number
        assert state['latest_user_message'] == step['message']
        assert state['response'] == data['message']
        assert len(state['messages']) <= 10
        assert len(state.get('summary_evidence', [])) <= 20
        history_response = await client.get(f'/api/v1/customer/sessions/{session_id}/history')
        assert history_response.status_code == 200
        history = history_response.json()['data']['messages']
        assert [msg['content'] for msg in history if msg['sender'] == 'CUSTOMER'] == expected_users
        assert len(history) == number * 2
        assert [msg['sender'] for msg in history] == ['CUSTOMER', 'AGENT'] * number
        assert history[-1]['content'] == data['message']
        assert history[-1]['vehicle_cards'] == data['vehicle_cards']
        assert history[-1]['citations'] == (data['citations'] or [])
        assert history[-1]['language'] == data['language']
        if delivery == 'replay' and number % 5 == 0:
            before = copy.deepcopy(stored.memory_states)
            replay = await client.post('/api/v1/customer/chat', json=payload)
            assert replay.status_code == 200
            assert replay.json() == response.json()
            customer_db.expire_all()
            assert customer_db.get(ChatSession, session_id).memory_states == before
            assert customer_db.query(Message).filter_by(session_id=session_id).count() == number * 2
        if delivery == 'reload':
            customer_db.expunge(stored)
    assert state['summary_evidence'], 'Long sessions must exercise compaction, not just grow an unbounded buffer'
    assert customer_db.query(ChatRequestRecord).filter_by(session_id=session_id).count() == length
