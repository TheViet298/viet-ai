import pytest
from httpx import ASGITransport, AsyncClient

from src.config import get_settings
from src.main import app
from src.models.db_models import ChatRequestRecord, ChatSession, Message, User, UserMemoryFact
from src.services.auth import get_current_user, get_optional_user, require_customer

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']
PREFIX = '/api/v1/customer'
SEED = 'Hãy nhớ xe của tôi là VF8 Plus, tôi ở Hà Nội'


@pytest.fixture(autouse=True)
def enabled(monkeypatch):
    monkeypatch.setattr(get_settings(), 'user_memory_enabled', True)


async def send(client, text, session='memory-a', **kwargs):
    response = await client.post(PREFIX + '/chat', json={'session_id': session, 'message': text, **kwargs})
    assert response.status_code == 200, response.text
    return response


async def facts(client):
    response = await client.get(PREFIX + '/memory')
    assert response.status_code == 200, response.text
    return response.json()['data']


@pytest.mark.asyncio
@pytest.mark.parametrize('language,question,expected', [
    ('en', 'Nhắc lại thông tin tôi đã khai báo trước đây.', 'vi'),
    ('vi', 'What car and trim did I tell you I own, and which city do I live in?', 'en'),
])
async def test_remember_and_recall_new_session_without_model_generation(client, customer_db, monkeypatch, language, question, expected):
    import src.api.customer as module
    async def unexpected(*args, **kwargs):
        pytest.fail('Explicit memory operations must not depend on RAG generation')
    monkeypatch.setattr(module, 'process_chat_message', unexpected)
    await send(client, SEED, language='en', request_id='remember-once')
    stored = await facts(client)
    assert stored['revision'] == 1
    assert stored['facts']['owned_vehicle.model']['value'] == 'VF8'
    assert stored['facts']['owned_vehicle.version']['value'] == 'Plus'
    assert stored['facts']['home_city']['value'] == 'Hà Nội'
    assert stored['facts']['home_city']['source_session_id'] == 'memory-a'
    response = await send(client, question, 'memory-b', language=language)
    data = response.json()['data']
    assert data['language'] == expected
    assert 'VF8' in data['message'].replace(' ', '') and 'Plus' in data['message']
    assert ('Hà Nội' if expected == 'vi' else 'Hanoi') in data['message']
    assert 'sự cố' not in data['message'] and not data['vehicle_cards']


@pytest.mark.asyncio
async def test_new_session_correction_replaces_model_and_city_without_comparison(client, customer_db):
    await send(client, SEED)
    response = await send(client, 'Không phải VF8, xe tôi là VF5, tôi ở Đà Nẵng', 'memory-b')
    assert not response.json()['data']['vehicle_comparison']
    stored = await facts(client)
    assert stored['facts']['owned_vehicle.model']['value'] == 'VF5'
    assert stored['facts']['owned_vehicle.version']['value'] is None
    assert stored['facts']['home_city']['value'] == 'Đà Nẵng'
    recalled = await send(client, 'Nhắc lại thông tin tôi đã khai báo trước đây.', 'memory-c')
    assert 'VF8' not in recalled.json()['data']['message'].replace(' ', '')


@pytest.mark.asyncio
async def test_chat_forget_cannot_be_resurrected_by_old_session_or_request_replay(client, customer_db):
    remembered = await send(client, SEED, request_id='remember-forget')
    same_replay = await send(client, SEED, request_id='remember-forget')
    assert same_replay.json() == remembered.json()
    assert (await facts(client))['revision'] == 1
    await send(client, 'Hãy quên hết thông tin tôi đã nhờ lưu', 'memory-b')
    forgotten = await facts(client)
    assert forgotten['revision'] == 2
    assert all(fact['value'] is None for fact in forgotten['facts'].values())
    for session in ['memory-a', 'memory-c']:
        response = await send(client, 'Xe tôi là dòng nào?', session)
        assert 'VF8' not in response.json()['data']['message'].replace(' ', '')
    replay = await send(client, SEED, request_id='remember-forget')
    assert 'VF8' not in replay.json()['data']['message'].replace(' ', '')
    assert (await facts(client))['revision'] == 2
    assert customer_db.get(User, 'regression-customer').vehicle_model is None


@pytest.mark.asyncio
async def test_delete_key_is_idempotent_and_removes_vehicle_dependencies(client, customer_db):
    await send(client, SEED)
    deleted = await client.delete(PREFIX + '/memory/owned_vehicle.model')
    assert deleted.status_code == 200
    revision = deleted.json()['data']['revision']
    again = await client.delete(PREFIX + '/memory/owned_vehicle.model')
    assert again.status_code == 200 and again.json()['data']['revision'] == revision
    stored = await facts(client)
    assert stored['facts']['owned_vehicle.model']['value'] is None
    assert stored['facts']['owned_vehicle.version']['value'] is None
    assert stored['facts']['home_city']['value'] == 'Hà Nội'
    assert (await client.delete(PREFIX + '/memory/current_location')).status_code == 400


@pytest.mark.asyncio
async def test_delete_source_session_invalidates_chat_facts_and_preserves_business_cases(client, customer_db):
    await send(client, SEED)
    incident = await send(client, 'Xe VF5 của tôi không sạc được, mã lỗi CC01', 'incident-session')
    case_id = incident.json()['data']['case_id']
    assert case_id
    result = await client.delete(PREFIX + '/sessions/memory-a')
    assert result.status_code == 200
    stored = await facts(client)
    assert all(fact['value'] is None for fact in stored['facts'].values())
    from src.models.db_models import Case
    assert customer_db.get(Case, case_id) is not None


@pytest.mark.asyncio
async def test_clear_history_preserves_independently_entered_profile_fact(client, customer_db):
    await send(client, SEED)
    user = customer_db.get(User, 'regression-customer')
    app.dependency_overrides[get_current_user] = lambda: user
    updated = await client.patch('/api/v1/auth/me', json={'vehicle_model': 'VF5'})
    assert updated.status_code == 200
    cleared = await client.delete(PREFIX + '/sessions')
    assert cleared.status_code == 200
    stored = await facts(client)
    assert stored['facts']['owned_vehicle.model']['value'] == 'VF5'
    assert stored['facts']['owned_vehicle.model']['source_kind'] == 'profile'
    assert stored['facts']['home_city']['value'] is None


@pytest.mark.asyncio
async def test_other_user_cannot_read_or_forget_facts_via_owner_parameters(client, customer_db):
    await send(client, SEED)
    other = User(id='memory-other', username='memory-other', password_hash='unused', role='CUSTOMER')
    customer_db.add(other)
    customer_db.commit()
    app.dependency_overrides[require_customer] = lambda: other
    app.dependency_overrides[get_optional_user] = lambda: other
    response = await client.get(PREFIX + '/memory?user_id=regression-customer')
    assert response.status_code == 200 and not response.json()['data']['facts']
    assert (await client.delete(PREFIX + '/memory?user_id=regression-customer')).status_code == 200
    assert customer_db.query(UserMemoryFact).filter_by(user_id='regression-customer', status='confirmed').count() == 3


@pytest.mark.asyncio
async def test_memory_api_requires_auth_and_customer_role(client, customer_db):
    app.dependency_overrides.pop(require_customer)
    assert (await client.get(PREFIX + '/memory')).status_code == 401
    assert (await client.delete(PREFIX + '/memory')).status_code == 401
    staff = User(id='memory-staff', username='memory-staff', password_hash='unused', role='STAFF')
    customer_db.add(staff)
    customer_db.commit()
    app.dependency_overrides[get_current_user] = lambda: staff
    assert (await client.get(PREFIX + '/memory')).status_code == 403


@pytest.mark.asyncio
async def test_fault_after_memory_flush_rolls_back_every_turn_write(client, customer_db, monkeypatch):
    import src.services.chat_turns as module
    def fail_after_write(*args, **kwargs):
        raise RuntimeError('synthetic persist failure')
    monkeypatch.setattr(module, 'accept_application_memory', fail_after_write)
    with pytest.raises(RuntimeError, match='synthetic persist failure'):
        await client.post(PREFIX + '/chat', json={'session_id': 'rollback-memory', 'message': SEED,
                                               'request_id': 'rollback-remember'})
    customer_db.expire_all()
    assert customer_db.get(User, 'regression-customer').memory_revision == 0
    assert customer_db.get(User, 'regression-customer').vehicle_model is None
    assert customer_db.query(UserMemoryFact).count() == 0
    assert customer_db.query(Message).filter_by(session_id='rollback-memory').count() == 0
    assert customer_db.query(ChatRequestRecord).count() == 0


@pytest.mark.asyncio
async def test_memory_does_not_force_generic_services_or_explicit_interest_model(client, customer_db):
    await send(client, SEED)
    application = await send(client, 'Ứng dụng VinFast có tính năng gì?', 'other-topic')
    assert application.json()['data']['citations']
    customer_db.expire_all()
    context = customer_db.get(ChatSession, 'other-topic').memory_states['other-topic']['conversation_context']
    assert context['subject'] is None
    advice = await send(client, 'Tư vấn VF3', 'other-topic')
    assert {card['model'] for card in advice.json()['data']['vehicle_cards']} == {'VF3'}
    assert (await facts(client))['facts']['owned_vehicle.model']['value'] == 'VF8'


@pytest.mark.asyncio
async def test_profile_model_is_only_a_confirmation_hint_for_new_incident(client, customer_db):
    await send(client, SEED)
    result = await send(client, 'Xe tôi không sạc được', 'new-incident')
    assert 'VF8' in result.json()['data']['message'].replace(' ', '')
    customer_db.expire_all()
    state = customer_db.get(ChatSession, 'new-incident').memory_states['new-incident']
    assert state['conversation_context']['active_goal'] == 'incident'
    assert not state.get('captured_fields', {}).get('current_location')


@pytest.mark.asyncio
async def test_feature_off_keeps_legacy_behavior_without_durable_writes(client, customer_db, monkeypatch):
    monkeypatch.setattr(get_settings(), 'user_memory_enabled', False)
    await send(client, SEED)
    assert customer_db.query(UserMemoryFact).count() == 0
    assert customer_db.get(User, 'regression-customer').memory_revision == 0


@pytest.mark.asyncio
async def test_personal_service_uses_selected_owned_facts_without_old_interest(client, customer_db, monkeypatch):
    import src.api.customer as module
    await send(client, SEED)
    await send(client, 'Tư vấn VF3', 'service-personal')
    captured = []
    async def answer(text, **kwargs):
        captured.append(kwargs['client_context'])
        return {'reply': 'Cần đối chiếu sổ bảo hành đúng xe.', 'citations': [], 'is_no_source': True}
    monkeypatch.setattr(module, 'process_chat_message', answer)
    await send(client, 'Bảo hành pin xe tôi bao lâu?', 'service-personal')
    assert captured[-1]['vehicle_model'] == 'VF8'
    assert captured[-1]['conversation_context']['subject'] == 'VF8'
    assert captured[-1]['conversation_context']['facts']['version']['value'] == 'Plus'


@pytest.mark.asyncio
async def test_memory_command_inside_incident_does_not_replace_incident_vehicle(client, customer_db):
    from src.models.db_models import CaseBrief
    incident = await send(client, 'Xe VF5 của tôi không sạc được, mã lỗi CC01', 'incident-memory')
    case_id = incident.json()['data']['case_id']
    await send(client, 'Hãy nhớ xe của tôi là VF8 Plus', 'incident-memory')
    following = await send(client, 'Trụ P02 tại Vincom Metropolis', 'incident-memory')
    assert following.json()['data']['case_id'] == case_id
    brief = customer_db.query(CaseBrief).filter_by(case_id=case_id).one()
    assert brief.captured_fields['vehicle_model'] == 'VF5'
    assert brief.captured_fields['charger_id'] == 'P02'


@pytest.mark.asyncio
async def test_memory_receipts_and_telemetry_do_not_duplicate_personal_values(client, customer_db, monkeypatch):
    import json
    from src.services import observability
    from tests.test_observability import FakeClient
    capture = FakeClient()
    monkeypatch.setattr(observability, '_client', capture)
    await send(client, SEED, request_id='private-receipt')
    await send(client, 'Nhắc lại thông tin tôi đã khai báo trước đây.', 'recall-private', request_id='private-recall')
    for record in customer_db.query(ChatRequestRecord).all():
        assert 'VF8' not in json.dumps(record.response, ensure_ascii=False)
        assert 'Hà Nội' not in json.dumps(record.response, ensure_ascii=False)
    assert 'Hà Nội' not in str([span.fields for span in capture.records])


@pytest.mark.asyncio
async def test_source_deletion_fences_a_turn_that_had_not_saved_any_facts(client, customer_db):
    from src.services.user_memory import MemoryChange, apply_user_memory_changes, load_user_memory
    user = customer_db.get(User, 'regression-customer')
    before = load_user_memory(customer_db, user)
    customer_db.add(ChatSession(id='pending-source', owner='user:regression-customer'))
    customer_db.commit()
    assert (await client.delete(PREFIX + '/sessions/pending-source')).status_code == 200
    stale = apply_user_memory_changes(customer_db, user, [MemoryChange(key='owned_vehicle.model', value='VF8')],
        expected_revision=before.revision, source_kind='profile', source_session_id=None, source_message_id=None)
    assert stale.status == 'conflict'
    assert not load_user_memory(customer_db, user).facts


@pytest.mark.asyncio
@pytest.mark.parametrize('path', ['/memory', '/sessions/memory-a', '/sessions'])
async def test_forget_and_source_deletion_share_sqlite_turn_admission(client, customer_db, monkeypatch, path):
    from contextlib import asynccontextmanager
    import src.services.sqlite_admission as module
    await send(client, SEED)
    observed = []
    @asynccontextmanager
    async def admission(db):
        observed.append(str(db.get_bind().url))
        yield
    monkeypatch.setattr(module, 'chat_writer', admission)
    response = await client.delete(PREFIX + path)
    assert response.status_code == 200
    assert len(observed) == 1


@pytest.mark.asyncio
async def test_revision_conflict_never_acknowledges_saved_facts(client, customer_db, monkeypatch):
    from src.services import user_memory
    original = user_memory.apply_user_memory_changes
    def newer_revision(db, user, changes, **kwargs):
        user_memory.fence_user_memory_revision(db, user, kwargs['expected_revision'], advance=True)
        return original(db, user, changes, **kwargs)
    monkeypatch.setattr(user_memory, 'apply_user_memory_changes', newer_revision)
    response = await send(client, SEED)
    assert 'chưa lưu' in response.json()['data']['message']
    assert not customer_db.query(UserMemoryFact).count()
    state = customer_db.get(ChatSession, 'memory-a').memory_states['memory-a']
    assert state['final_diagnostics']['answer_status'] == 'error'


@pytest.mark.asyncio
async def test_remember_plus_business_question_keeps_both_requested_operations(client, customer_db, monkeypatch):
    import src.api.customer as module
    called = []
    async def answer(text, **kwargs):
        called.append(text)
        return {'reply': 'Cần đối chiếu sổ bảo hành đúng xe.', 'citations': [], 'is_no_source': True}
    monkeypatch.setattr(module, 'process_chat_message', answer)
    response = await send(client, 'Hãy nhớ xe của tôi là VF8 Plus, và giải thích chính sách bảo hành pin.')
    assert called and 'bảo hành' in called[0]
    assert 'Cần đối chiếu' in response.json()['data']['message']
    assert 'ghi nhớ' in response.json()['data']['message']
    assert (await facts(client))['facts']['owned_vehicle.model']['value'] == 'VF8'
    state = customer_db.get(ChatSession, 'memory-a').memory_states['memory-a']
    assert state['final_diagnostics']['answer_status'] == 'needs_data'


@pytest.mark.asyncio
async def test_forget_invalidates_old_personal_service_scope_before_new_incident(client, customer_db):
    await send(client, SEED)
    await send(client, 'Bảo hành pin xe tôi bao lâu?', 'personal-service')
    assert (await client.delete(PREFIX + '/memory')).status_code == 200
    response = await send(client, 'Xe tôi không sạc được', 'personal-service')
    assert 'VF8' not in response.json()['data']['message'].replace(' ', '')
    assert customer_db.get(User, 'regression-customer').vehicle_model is None
