import pytest

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']


@pytest.mark.asyncio
async def test_ambiguous_text_does_not_create_case_and_keeps_original(client, customer_db):
    from src.models.db_models import Case, ChatSession, Message
    text = 'kh muon doi xe'
    payload = {'session_id': 'shorthand-ambiguous', 'message': text, 'request_id': 'normalize-once'}
    response = await client.post('/api/v1/customer/chat', json=payload)
    assert response.status_code == 200
    data = response.json()['data']
    assert data['response_type'] == 'CLARIFICATION'
    assert 'viết đầy đủ' in data['message']
    assert data['case_id'] is None
    assert customer_db.query(Case).count() == 0
    message = customer_db.query(Message).filter_by(session_id=payload['session_id'], sender_type='CUSTOMER').one()
    assert message.content == text
    retry = await client.post('/api/v1/customer/chat', json=payload)
    assert retry.json() == response.json()
    customer_db.expire_all()
    state = customer_db.get(ChatSession, payload['session_id']).memory_states[payload['session_id']]
    assert state['turn_understanding']['original_text'] == text
    assert not state['conversation_context']['facts']


@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['phanh k an', 'phanh ko an', 'phanh kh an'])
async def test_api_abbreviated_brakes_are_critical(client, customer_db, text):
    response = await client.post('/api/v1/customer/chat', json={'session_id': 'short-brake', 'message': text})
    assert response.status_code == 200
    data = response.json()['data']
    assert data['priority'] == 'CRITICAL'
    assert data['show_emergency_banner']


@pytest.mark.asyncio
async def test_contextual_shorthand_reaches_warranty_and_preserves_history(client, customer_db, monkeypatch):
    from src.agents.nodes import rag_node
    from src.models.db_models import ChatSession, Message
    from src.services import agent_llm
    calls = []

    async def generate(state, prompt, schema, **kwargs):
        if prompt == 'normalization':
            calls.append(prompt)
            return schema(expansions=[{'token': 'bh', 'replacement': 'bảo hành'}], needs_confirmation=False)
        return None

    async def missing(*args, **kwargs):
        return {'status': 'NO_SOURCE', 'citations': [], 'diagnostics': {}}

    monkeypatch.setattr(agent_llm, 'structured_call', generate)
    monkeypatch.setattr(rag_node, 'vinfast_manual_search', missing)
    text = 'chinh sach bh pin VF8'
    response = await client.post('/api/v1/customer/chat', json={'session_id': 'short-warranty', 'message': text})
    assert response.status_code == 200
    customer_db.expire_all()
    state = customer_db.get(ChatSession, 'short-warranty').memory_states['short-warranty']
    assert state['conversation_context']['active_goal'] == 'warranty'
    assert state['turn_understanding']['original_text'] == text
    assert 'bảo hành' in state['turn_understanding']['resolved_query']
    assert customer_db.query(Message).filter_by(session_id='short-warranty', sender_type='CUSTOMER').one().content == text
    assert calls == ['normalization']


@pytest.mark.asyncio
async def test_answer_to_spelling_question_restores_previous_subject(client, customer_db, monkeypatch):
    from src.agents.nodes import rag_node
    from src.models.db_models import ChatSession

    async def missing(*args, **kwargs):
        return {'status': 'NO_SOURCE', 'citations': [], 'diagnostics': {}}

    monkeypatch.setattr(rag_node, 'vinfast_manual_search', missing)
    first = await client.post('/api/v1/customer/chat', json={'session_id': 'short-followup', 'message': 'bh pin VF8'})
    assert first.json()['data']['response_type'] == 'CLARIFICATION'
    second = await client.post('/api/v1/customer/chat', json={'session_id': 'short-followup', 'message': 'bảo hành'})
    assert second.status_code == 200
    customer_db.expire_all()
    state = customer_db.get(ChatSession, 'short-followup').memory_states['short-followup']
    assert state['conversation_context']['active_goal'] == 'warranty'
    assert state['conversation_context']['subject'] == 'VF8'
    assert state['turn_understanding']['original_text'] == 'bảo hành'


@pytest.mark.asyncio
@pytest.mark.parametrize('short', ['k', 'ko', 'kh'])
async def test_denied_smoke_does_not_create_an_emergency(client, customer_db, short):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'short-denial', 'message': f'{short} co khoi hay mui khet, xe van di duoc'})
    assert response.status_code == 200
    data = response.json()['data']
    assert data['priority'] != 'CRITICAL'
    assert not data['show_emergency_banner']


@pytest.mark.asyncio
async def test_ambiguous_code_does_not_become_an_observed_fact(client, customer_db):
    from src.models.db_models import ChatSession
    response = await client.post('/api/v1/customer/chat', json={'session_id': 'short-code', 'message': 'bh VF8 CC01'})
    assert response.json()['data']['response_type'] == 'CLARIFICATION'
    customer_db.expire_all()
    state = customer_db.get(ChatSession, 'short-code').memory_states['short-code']
    assert not state['captured_fields']
    assert not state['conversation_context']['facts']


@pytest.mark.asyncio
async def test_standalone_agent_preserves_raw_history_and_clarifies(tmp_path):
    from src.agents.chatbot_agent import process_chat_message
    from src.services.session_store import get_store
    result = await process_chat_message('kh muon doi xe', session_id='standalone-short', persist_business_case=False)
    assert result['response_type'] == 'CLARIFICATION'
    assert result['case_id'] is None
    state = get_store().read_existing_state('standalone-short', 'guest:standalone-short', 'guest')
    assert state['messages'][0].content == 'kh muon doi xe'


@pytest.mark.asyncio
async def test_standalone_storage_keeps_customer_spelling():
    from src.agents.chatbot_agent import process_chat_message
    from src.services.session_store import get_store
    text = 'phanh ko an'
    await process_chat_message(text, session_id='standalone-raw', persist_business_case=False)
    store = get_store()
    with store.connect() as db:
        row = db.execute("SELECT content FROM messages WHERE session_id=? AND sender_type='CUSTOMER'",
                         ('standalone-raw',)).fetchone()
        assert row['content'] == text
