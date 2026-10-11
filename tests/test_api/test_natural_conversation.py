import json
from pathlib import Path

import pytest

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']

CASES = json.loads((Path(__file__).resolve().parents[2] / 'eval/datasets/natural_conversation_acceptance.json').read_text(encoding='utf-8'))
GOALS = {'quote-slots': 'quote', 'drive-action': 'test_drive', 'model-switch': 'warranty',
         'component-correction': 'warranty', 'challenge-number': 'range', 'unknown-version': 'capacity',
         'cancel-action': 'test_drive', 'next-step': 'maintenance', 'concept-detail': 'concept',
         'incident-slots': 'incident', 'incident-resolved': 'incident', 'new-emergency': 'incident',
         'price-control': 'quote', 'warranty': 'warranty', 'battery-warranty': 'warranty',
         'charging-time': 'charging', 'range': 'range', 'battery-capacity': 'capacity',
         'test-drive': 'test_drive', 'maintenance': 'maintenance', 'concept': 'concept'}


@pytest.mark.asyncio
@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
async def test_acceptance_dataset_preserves_goal_and_route(client, customer_db, monkeypatch, case):
    from src.agents.nodes import rag_node
    from src.models.db_models import ChatSession
    async def missing(*args, **kwargs):
        return {'status': 'NO_SOURCE', 'citations': [], 'diagnostics': {}}
    monkeypatch.setattr(rag_node, 'vinfast_manual_search', missing)
    turns = case.get('turns') or [case['first'], case['followup']]
    for index, text in enumerate(turns, 1):
        result = await client.post('/api/v1/customer/chat', json={'session_id': case['id'], 'message': text})
        assert result.status_code == 200
        data = result.json()['data']
        if not case['id'].startswith('incident-') and not (case['id'] == 'new-emergency' and index == 2):
            assert data['case_id'] is None
            assert data['response_type'] == 'FAQ_ANSWER'
        assert data['response_type'] != 'OUT_OF_SCOPE'
    customer_db.expire_all()
    state = customer_db.get(ChatSession, case['id']).memory_states[case['id']]
    context = state['conversation_context']
    assert context['active_goal'] == GOALS[case['id']]
    assert state['turn'] == len(turns)
    if case['id'] == 'quote-slots':
        assert {k: v['value'] for k, v in context['facts'].items()} == {
            'model': 'VF8', 'version': 'Plus', 'battery': 'mua kèm pin', 'city': 'Hà Nội'}
    if case['id'] == 'unknown-version':
        assert context['facts']['version']['status'] == 'unknown'
        assert 'có thể tư vấn tiếp' in data['message'].casefold()
        assert 'đơn vị năng lượng' in data['message']
    if case['id'] == 'model-switch':
        assert context['subject'] == 'VF5'
    if case['id'] == 'drive-action':
        assert state['conversation_progress']['state'] == 'external_action_required'
        assert 'exact_date' in state['conversation_progress']['missing_fields']


@pytest.mark.asyncio
@pytest.mark.parametrize('first,followup,goal,move,need', [
    ('Giá lăn bánh VF8?', 'VF8 Plus, mua kèm pin, Hà Nội', 'quote', 'supply_info', 'chi-phi-lan-banh'),
    ('Tôi muốn lái thử VF8 ở Hà Nội thứ bảy', 'Có đặt được luôn không?', 'test_drive', 'request_action', 'chưa'),
    ('Tôi muốn đặt lịch bảo dưỡng VF8', 'Vậy giờ tôi cần làm gì?', 'maintenance', 'ask_next_step', 'Ứng dụng'),
    ('Bảo hành pin VF8 bao lâu?', 'Pin cao áp, không phải ắc quy 12V', 'warranty', 'correct', 'cao áp'),
    ('VF8 đi được bao nhiêu km?', '500 hay 450 km đúng?', 'range', 'verify_claim', 'xác'),
])
async def test_natural_followups_use_shared_context(client, customer_db, monkeypatch, first, followup, goal, move, need):
    from src.agents.nodes import rag_node
    from src.models.db_models import ChatSession

    async def missing(*args, **kwargs):
        return {'status': 'NO_SOURCE', 'citations': [], 'diagnostics': {}}
    monkeypatch.setattr(rag_node, 'vinfast_manual_search', missing)
    for text in (first, followup):
        result = await client.post('/api/v1/customer/chat', json={'session_id': 'natural', 'message': text})
        assert result.status_code == 200
    data = result.json()['data']
    assert data['case_id'] is None
    assert need in data['message']
    customer_db.expire_all()
    state = customer_db.get(ChatSession, 'natural').memory_states['natural']
    assert state['conversation_context']['active_goal'] == goal
    assert state['turn_understanding']['move'] == move


@pytest.mark.asyncio
async def test_retry_keeps_context_version(client, customer_db):
    from src.models.db_models import ChatSession
    payload = {'session_id': 'retry-natural', 'message': 'Giá VF8 Plus ở Hà Nội?', 'request_id': 'one'}
    first = await client.post('/api/v1/customer/chat', json=payload)
    second = await client.post('/api/v1/customer/chat', json=payload)
    assert first.json() == second.json()
    customer_db.expire_all()
    state = customer_db.get(ChatSession, 'retry-natural').memory_states['retry-natural']
    assert state['conversation_context']['facts']['version']['source_turn'] == 1


@pytest.mark.asyncio
async def test_quote_returns_verified_public_price_without_showroom_discount(client, customer_db, monkeypatch):
    from src.agents.nodes import rag_node
    from src.services.rag_service import source_registry
    calls = []
    async def price(query, **kwargs):
        calls.append(query)
        citation = {**source_registry()['SRC-009'], 'source_id': 'SRC-009',
                    'applicable_models': ['VF8'], 'distance': .2,
                    'relevant_snippet': 'VF8 Plus giá bán công bố từ 1.079.000.000 VNĐ.'}
        return {'status': 'SUCCESS', 'citations': [citation]}
    monkeypatch.setattr(rag_node, 'vinfast_manual_search', price)
    await client.post('/api/v1/customer/chat', json={'session_id': 'public-price', 'message': 'Giá lăn bánh VF8?'})
    result = await client.post('/api/v1/customer/chat', json={'session_id': 'public-price', 'message': 'VF8 Plus, mua kèm pin, Hà Nội'})
    data = result.json()['data']
    assert 'từ 1.079.000.000 VNĐ' in data['message']
    for value in ('VF8', 'Plus', 'mua kèm pin', 'Hà Nội', 'chi-phi-lan-banh'):
        assert value in data['message']
    assert 'nào' not in data['message']
    assert data['citations']
    assert 'Plus' in calls[-1]


@pytest.mark.asyncio
async def test_failed_turn_rolls_back_context(client, customer_db, monkeypatch):
    import src.api.customer as api
    from src.models.db_models import ChatSession
    await client.post('/api/v1/customer/chat', json={'session_id': 'rollback-context', 'message': 'Giá VF8?'})
    customer_db.expire_all()
    before = customer_db.get(ChatSession, 'rollback-context').memory_states
    async def fail(*args, **kwargs):
        raise RuntimeError('synthetic failure')
    monkeypatch.setattr(api, 'answer_sales_question', fail)
    with pytest.raises(RuntimeError, match='synthetic failure'):
        await client.post('/api/v1/customer/chat', json={'session_id': 'rollback-context', 'message': 'VF8 Plus ở Hà Nội'})
    customer_db.expire_all()
    assert customer_db.get(ChatSession, 'rollback-context').memory_states == before


@pytest.mark.asyncio
async def test_context_restart_and_owner_isolation(client, customer_db):
    from src.main import app
    from src.models.db_models import ChatSession, User
    from src.services.auth import get_optional_user
    await client.post('/api/v1/customer/chat', json={'session_id': 'restart-context', 'message': 'Giá VF8 Plus mua kèm pin ở Hà Nội?'})
    customer_db.expunge(customer_db.get(ChatSession, 'restart-context'))
    result = await client.post('/api/v1/customer/chat', json={'session_id': 'restart-context', 'message': 'Tôi đã nói rồi, còn thiếu gì?'})
    assert 'Plus' in result.json()['data']['message']
    other = User(id='context-other', username='context-other', password_hash='unused', role='CUSTOMER')
    customer_db.add(other)
    customer_db.commit()
    app.dependency_overrides[get_optional_user] = lambda: other
    denied = await client.post('/api/v1/customer/chat', json={'session_id': 'restart-context', 'message': 'Có đặt được không?'})
    assert denied.status_code == 403
    fresh = await client.post('/api/v1/customer/chat', json={'session_id': 'fresh-context', 'message': 'Giá VF5?'})
    assert fresh.status_code == 200
    assert 'version' not in customer_db.get(ChatSession, 'fresh-context').memory_states['fresh-context']['conversation_context']['facts']


@pytest.mark.asyncio
async def test_followup_context_budget_error_keeps_goal_and_next_step(client, customer_db, monkeypatch):
    from src.agents.nodes import rag_node
    from src.services.rag_service import source_registry
    async def oversized(*args, **kwargs):
        citation = {**source_registry()['SRC-004'], 'source_id': 'SRC-004', 'applicable_models': ['VF8'],
                    'distance': .2, 'relevant_snippet': 'VF8 bảo dưỡng theo sổ bảo dưỡng đúng đời xe và điều kiện sử dụng. ' * 500}
        return {'status': 'SUCCESS', 'citations': [citation]}
    monkeypatch.setattr(rag_node, 'vinfast_manual_search', oversized)
    for text in ('VF8 cần bảo dưỡng sau bao nhiêu km?', 'Sao không có mốc bảo dưỡng chính xác?'):
        result = await client.post('/api/v1/customer/chat', json={'session_id': 'budget-followup', 'message': text})
        assert result.status_code == 200
    reply = result.json()['data']['message']
    assert 'Mốc bảo dưỡng' in reply
    assert 'đời xe' in reply
    assert 'số km hiện tại' in reply


def test_persisting_followup_preserves_contextual_budget_reply():
    from src.services.session_store import prepare_application_turn
    reply = 'Mốc bảo dưỡng cần đối chiếu đúng đời xe. Anh/chị cho biết đời xe và số km hiện tại nhé.'
    state = {'is_no_source': True, 'response': reply,
             'turn_understanding': {'move': 'elaborate', 'goal': 'maintenance'},
             'retrieval_diagnostics': {'category': 'context_budget_exceeded', 'stage': 'prompt'}}
    prepare_application_turn(state)
    assert state['response'] == reply
