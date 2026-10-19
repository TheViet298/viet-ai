"""Answer completeness is independent of HTTP success and citation presence."""
import pytest

from src.models.db_models import ChatSession, Message
from src.services.rag_service import RAGService
from src.services.request_diagnostics import final_response_diagnostics

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']


@pytest.mark.asyncio
@pytest.mark.parametrize('missing,expected', [
    ('NO_SOURCE', 'partial'), ('TIMEOUT', 'partial'), (None, 'answered'), ('all', 'needs_data'),
    ('all_timeout', 'error'),
])
async def test_compound_status_survives_api_history_and_replay(client, customer_db, monkeypatch, missing, expected):
    from src.agents.nodes import rag_node as module

    async def search(query, **kwargs):
        if missing in {'all', 'all_timeout'} or (missing and 'bảo dưỡng' in query.casefold()):
            status = 'TIMEOUT' if missing in {'TIMEOUT', 'all_timeout'} else 'NO_SOURCE'
            return RAGService.failure(status, 'synthetic_' + status.casefold())
        return RAGService().retrieve(query, **kwargs)

    monkeypatch.setattr(module, 'vinfast_manual_search', search)
    payload = {'session_id': 'compound-status', 'message': 'Chính sách bảo hành pin và lịch bảo dưỡng định kỳ',
               'request_id': 'compound-request'}
    response = await client.post('/api/v1/customer/chat', json=payload)
    assert response.status_code == 200
    data = response.json()['data']
    assert data['message'].count('### Bảo hành pin') == 1
    assert data['message'].count('### Bảo dưỡng định kỳ') == 1
    customer_db.expire_all()
    state = customer_db.get(ChatSession, payload['session_id']).memory_states[payload['session_id']]
    assert state['final_diagnostics']['answer_status'] == expected
    assert state['final_diagnostics']['final_outcome'] == {
        'partial': 'partial', 'answered': 'success', 'needs_data': 'needs_verified_data', 'error': 'error'}[expected]
    parts = state['conversation_retrieval']['parts']
    assert all(part['status'] in {'SUCCESS', 'NO_SOURCE', 'ERROR', 'TIMEOUT'} for part in parts)
    if expected == 'partial':
        assert parts[0]['status'] == 'SUCCESS' and parts[1]['status'] == missing
        assert data['citations'] and 'chưa' in data['message']
    history = customer_db.query(Message).filter_by(session_id=payload['session_id'], sender_type='AGENT').one()
    assert history.msg_metadata['answer_status'] == expected
    replay = await client.post('/api/v1/customer/chat', json=payload)
    assert replay.json() == response.json()
    assert customer_db.query(Message).filter_by(session_id=payload['session_id']).count() == 2
    async def available(query, **kwargs):
        return RAGService().retrieve(query, **kwargs)
    monkeypatch.setattr(module, 'vinfast_manual_search', available)
    following = await client.post('/api/v1/customer/chat', json={
        'session_id': payload['session_id'], 'message': 'Ứng dụng VinFast có tính năng gì?'})
    assert following.status_code == 200
    customer_db.expire_all()
    state = customer_db.get(ChatSession, payload['session_id']).memory_states[payload['session_id']]
    assert state['final_diagnostics']['answer_status'] == 'answered'
    assert not state['conversation_retrieval'].get('parts')


@pytest.mark.parametrize('status,outcome', [
    ('refused', 'success'), ('external_action_required', 'success'),
    ('needs_clarification', 'needs_clarification'), ('needs_data', 'needs_verified_data'),
])
def test_operational_and_boundary_results_are_not_answered(status, outcome):
    result = final_response_diagnostics(answer_path='general', successful=True, stages=[], answer_status=status)
    assert result['answer_status'] == status and result['final_outcome'] == outcome
