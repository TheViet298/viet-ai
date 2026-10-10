import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, get_db
from src.main import app
from src.models.db_models import Case, CaseBrief, Message, User
from src.services.auth import get_optional_user, require_customer
from src.services.session_store import get_store


@pytest.mark.asyncio
async def test_web_success_memory_is_atomic_and_retry_does_not_advance(client, chat_db):
    import json

    from src.models.db_models import ChatSession
    from src.services.session_store import decode_state
    db, _, _ = chat_db
    payload = {'session_id': 'atomic', 'request_id': 'atomic-1', 'message': 'Trạm sạc VinFast tính phí thế nào?'}
    response = await client.post('/api/v1/customer/chat', json=payload)
    assert response.status_code == 200
    states = db.get(ChatSession, 'atomic').memory_states
    assert states and decode_state(json.dumps(states['atomic']))['turn'] == 1
    count = db.query(Message).filter_by(session_id='atomic').count()
    await client.post('/api/v1/customer/chat', json=payload)
    assert db.query(Message).filter_by(session_id='atomic').count() == count
    assert db.get(ChatSession, 'atomic').memory_states == states


@pytest.mark.asyncio
async def test_existing_owned_core_memory_imports_without_new_core_write(client, chat_db):
    from src.agents.chatbot_agent import process_chat_message
    from src.models.db_models import ChatSession
    db, a, _ = chat_db
    await process_chat_message('Xin chào', session_id='legacy-chat', user_role='customer', owner=a.id, persist_business_case=False)
    with get_store().connect() as core:
        before = core.execute("SELECT count(*) FROM messages WHERE session_id='legacy-chat'").fetchone()[0]
    await client.post('/api/v1/customer/chat', json={'session_id': 'legacy-chat', 'message': 'Trạm sạc VinFast tính phí thế nào?'})
    snapshot = db.get(ChatSession, 'legacy-chat').memory_states['legacy-chat']
    assert snapshot['turn'] == 2
    with get_store().connect() as core:
        assert core.execute("SELECT count(*) FROM messages WHERE session_id='legacy-chat'").fetchone()[0] == before


@pytest.mark.asyncio
async def test_existing_cardd_confirmation_imports_prefixed_legacy_state(client, chat_db):
    from src.agents.chatbot_agent import process_chat_message
    from src.models.db_models import ChatSession
    db, a, _ = chat_db
    prefix = f'cardd:{a.id}:legacy-photo'
    evidence = {'schema_version': '1.0', 'image_id': 'legacy-photo', 'damage': {
        'status': 'detected', 'model_version': 'a' * 64, 'threshold': 0.25,
        'detections': [{'label': 'dent', 'confidence': 0.29, 'bbox_xyxy': [0.1, 0.1, 0.8, 0.7]}]}}
    await process_chat_message('Xe VF8 của tôi có ảnh ngoại thất', session_id=prefix, user_role='customer',
                               owner=a.id, damage_evidence=evidence, persist_business_case=False)
    db.add(Message(id='legacy-photo-user', session_id='legacy-photo', sender_type='CUSTOMER', content='Ảnh đây',
                   msg_metadata={'user_id': a.id, 'vehicle_context': {'owned_model': 'VF8', 'incident_scope': 1}}))
    db.add(Message(id='legacy-photo-agent', session_id='legacy-photo', sender_type='AGENT', content='Xác nhận ảnh',
                   msg_metadata={'user_id': a.id, 'cardd_flow': True, 'response_type': 'CLARIFICATION'}))
    db.commit()
    response = await client.post('/api/v1/customer/chat', json={'session_id': 'legacy-photo', 'message': 'Xác nhận hư hại trong ảnh'})
    assert response.status_code == 200
    visual = response.json()['data']['visual_evidence']
    assert visual['image_id'] == 'legacy-photo' and visual['confirmation'] == 'confirmed'
    assert db.get(ChatSession, 'legacy-photo').memory_states[prefix]['cardd_evidence']['image_id'] == 'legacy-photo'


@pytest.mark.asyncio
async def test_legacy_hypothetical_fact_is_not_promoted_during_import(client, chat_db):
    from src.models.db_models import ChatSession
    db, a, _ = chat_db
    store = get_store()
    state, version = store.claim('legacy-hypothetical', a.id, 'customer')
    state.update(turn=1, latest_user_message='Nếu xe báo lỗi CC01 thì làm gì?', response='FAQ',
                 captured_fields={'error_code': 'CC01'}, fact_history=[{'field': 'error_code', 'value': 'CC01',
                 'status': 'valid', 'provenance': 'user:turn:1', 'valid_from': '2026-10-06T00:00:00+00:00', 'valid_to': None}])
    store.save_turn('legacy-hypothetical', a.id, version, state, persist_business_case=False)
    await client.post('/api/v1/customer/chat', json={'session_id': 'legacy-hypothetical', 'message': 'Trạm sạc VinFast tính phí thế nào?'})
    snapshot = db.get(ChatSession, 'legacy-hypothetical').memory_states['legacy-hypothetical']
    assert 'error_code' not in snapshot['captured_fields']


def test_legacy_fact_denied_in_later_turn_is_not_imported(chat_db):
    _, a, _ = chat_db
    store = get_store()
    for index, text in enumerate(['Xe VF8 của tôi đang báo lỗi CC01', 'Xe tôi không báo mã lỗi CC01 nữa'], 1):
        state, version = store.claim('legacy-denied', a.id, 'customer')
        state.update(turn=index, latest_user_message=text, response='reply', captured_fields={'error_code': 'CC01'},
                     fact_history=[{'field': 'error_code', 'value': 'CC01', 'status': 'valid', 'provenance': 'user:turn:1'}])
        store.save_turn('legacy-denied', a.id, version, state, persist_business_case=False)
    assert 'error_code' not in store.read_existing_state('legacy-denied', a.id, 'customer')['captured_fields']


@pytest.mark.asyncio
async def test_deterministic_web_turn_is_in_canonical_memory(client, chat_db):
    import json

    from src.models.db_models import ChatSession
    from src.services.session_store import decode_state
    db, _, _ = chat_db
    await client.post('/api/v1/customer/chat', json={'session_id': 'canonical', 'message': 'Xe VF8 không sạc được'})
    row = db.get(ChatSession, 'canonical')
    state = decode_state(json.dumps(row.memory_states.get('canonical', {})))
    assert state.get('turn') == 1
    assert any('không sạc được' in str(m.content) for m in state['messages'])


@pytest.mark.asyncio
async def test_guest_emergency_memory_uses_current_message(client, chat_db):
    import json

    from src.models.db_models import ChatSession
    from src.services.session_store import decode_state
    db, _, _ = chat_db
    app.dependency_overrides[get_optional_user] = lambda: None
    await client.post('/api/v1/customer/chat', json={'session_id': 'guest-danger', 'guest_session_id': 'guest-danger', 'message': 'Xin chào'})
    await client.post('/api/v1/customer/chat', json={'session_id': 'guest-danger', 'guest_session_id': 'guest-danger', 'message': 'Xe bốc khói'})
    snapshot = db.get(ChatSession, 'guest-danger').memory_states['guest-danger']
    state = decode_state(json.dumps(snapshot))
    assert state['latest_user_message'] == 'Xe bốc khói'
    assert state['turn'] == 2


@pytest.mark.asyncio
async def test_web_scope_reset_does_not_resummarize_old_messages(client, chat_db):
    import json

    from src.models.db_models import ChatSession
    from src.services.session_store import decode_state
    db, _, _ = chat_db
    for _ in range(5):
        await client.post('/api/v1/customer/chat', json={'session_id': 'web-scope', 'message': 'Xe VF8 của tôi không sạc được tại trụ P01, mã lỗi CC01'})
    await client.post('/api/v1/customer/chat', json={'session_id': 'web-scope', 'message': 'Tôi đang sử dụng xe VF5 khác, xe này không sạc được'})
    state = decode_state(json.dumps(db.get(ChatSession, 'web-scope').memory_states['web-scope']))
    assert 'CC01' not in state.get('memory_summary', '')
    assert not state.get('summary_evidence')


@pytest.mark.asyncio
async def test_new_vehicle_keeps_previous_critical_visible(client, chat_db):
    db, _, _ = chat_db
    first = (await client.post('/api/v1/customer/chat', json={'session_id': 'critical-cars', 'message': 'Xe VF8 của tôi bốc khói'})).json()['data']
    second = (await client.post('/api/v1/customer/chat', json={'session_id': 'critical-cars', 'message': 'Tôi đang sử dụng xe VF5 khác, xe này không sạc được'})).json()['data']
    assert second['show_emergency_banner']
    assert db.get(Case, first['case_id']).priority == 'CRITICAL'
    third = (await client.post('/api/v1/customer/chat', json={'session_id': 'critical-cars', 'message': 'Trụ P02, lỗi CC02'})).json()['data']
    assert third['case_id'] != first['case_id'] and third['priority'] == 'HIGH'
    status = (await client.get(f"/api/v1/customer/cases/{third['case_id']}/status")).json()['data']
    assert status['emergency_context']['case_id'] == first['case_id']
    assert third['emergency_context']['case_id'] == first['case_id']


@pytest.mark.asyncio
async def test_new_vehicle_does_not_overwrite_previous_case(client, chat_db):
    db, _, _ = chat_db
    first = (await client.post('/api/v1/customer/chat', json={'session_id': 'cars', 'message': 'Xe VF8 của tôi không sạc được tại trụ P01, mã lỗi CC01'})).json()['data']
    second = (await client.post('/api/v1/customer/chat', json={'session_id': 'cars', 'case_id': first['case_id'], 'message': 'Tôi đang sử dụng xe VF5 khác, xe này không sạc được'})).json()['data']
    assert second['response_type'] == 'CLARIFICATION'
    assert 'P01' not in second['message'] and second['case_id'] is None
    brief = db.query(CaseBrief).filter_by(case_id=first['case_id']).one()
    assert brief.captured_fields['vehicle_model'] == 'VF8'
    third = (await client.post('/api/v1/customer/chat', json={'session_id': 'cars', 'message': 'Trụ P02, lỗi CC02'})).json()['data']
    assert third['case_id'] and third['case_id'] != first['case_id']
    assert db.query(CaseBrief).filter_by(case_id=first['case_id']).one().captured_fields['vehicle_model'] == 'VF8'


@pytest.mark.asyncio
async def test_negated_error_does_not_route_incident(client, chat_db):
    response = await client.post('/api/v1/customer/chat', json={'session_id': 'denied', 'message': 'Xe tôi không báo mã lỗi CC01'})
    data = response.json()['data']
    assert data['response_type'] == 'FAQ_ANSWER'
    assert 'đang gặp sự cố' not in data['message'] and data['case_id'] is None


@pytest.mark.asyncio
async def test_web_failure_after_core_has_no_committed_core_turn(client, chat_db, monkeypatch):
    from src.api import customer
    original = customer.process_chat_message

    async def fail_after_core(*args, **kwargs):
        await original(*args, **kwargs)
        raise RuntimeError('after draft')

    monkeypatch.setattr(customer, 'process_chat_message', fail_after_core)
    with pytest.raises(RuntimeError, match='after draft'):
        await client.post('/api/v1/customer/chat', json={'session_id': 'rollback', 'message': 'Trạm sạc VinFast tính phí thế nào?'})
    db, _, _ = chat_db
    assert db.query(Message).filter_by(session_id='rollback').count() == 0
    with get_store().connect() as core:
        assert core.execute("SELECT count(*) FROM messages WHERE session_id='rollback'").fetchone()[0] == 0


@pytest.fixture
def chat_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'web.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        a = User(id="remediation-a", username="remediation-a", password_hash="unused", role="CUSTOMER")
        b = User(id="remediation-b", username="remediation-b", password_hash="unused", role="CUSTOMER")
        db.add_all([a, b])
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_optional_user] = lambda: a
        app.dependency_overrides[require_customer] = lambda: app.dependency_overrides[get_optional_user]()
        yield db, a, b
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.asyncio
async def test_case_and_session_owner_checked_before_writes(client, chat_db):
    db, a, b = chat_db
    first = await client.post('/api/v1/customer/chat', json={'session_id': 'owned', 'message': 'Xe bốc khói'})
    cid = first.json()['data']['case_id']
    before = db.query(Message).count()
    app.dependency_overrides[get_optional_user] = lambda: b
    for payload in [dict(session_id='other', case_id=cid), dict(session_id='owned')]:
        r = await client.post('/api/v1/customer/chat', json={**payload, 'message': 'Xin chào'})
        assert r.status_code == 403
        assert db.query(Message).count() == before
    app.dependency_overrides[get_optional_user] = lambda: None
    r = await client.post('/api/v1/customer/chat', json={'session_id': 'owned', 'guest_session_id': 'guest', 'message': 'Xin chào'})
    assert r.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['Xe bị liệt phanh', 'Xe boc khoi', 'Mat phanh tren cao toc', 'Xe bốc khói, giải thích giúp tôi vì sao', 'Xe hiện rùa vàng và dừng giữa cao tốc'])
async def test_guest_quota_never_blocks_emergency(client, chat_db, text):
    db, _, _ = chat_db
    app.dependency_overrides[get_optional_user] = lambda: None
    db.add_all([Message(id=f'quota-{i}', session_id='quota', sender_type='CUSTOMER', content='demo') for i in range(5)])
    db.commit()
    r = await client.post('/api/v1/customer/chat', json={'session_id': 'quota', 'guest_session_id': 'quota', 'message': text})
    assert r.status_code == 200
    data = r.json()['data']
    assert data['priority'] == 'CRITICAL'
    assert data['show_emergency_banner'] and data['request_location']
    assert '1900-232389' in data['message'] + (data['safe_guidance'] or '')
    assert data['case_id'] is None
    assert db.query(Case).count() == 0
    normal = await client.post('/api/v1/customer/chat', json={'session_id': 'quota', 'guest_session_id': 'quota', 'message': 'Xin chào'})
    assert normal.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['Khói bụi ngoài đường có hại pin không?', 'Hôm qua xe tôi hiện rùa vàng, giờ hết rồi', 'Tháng trước xe tôi bị không sạc, giờ hết rồi', 'Nếu xe hiện rùa vàng thì tôi nên làm gì?', 'CC01 nghĩa là gì?', 'Trạm sạc VinFast tính phí thế nào?'])
async def test_knowledge_has_no_case_or_incident_prompt(client, chat_db, text):
    db, _, _ = chat_db
    r = await client.post('/api/v1/customer/chat', json={'session_id': 'faq', 'message': text})
    data = r.json()['data']
    assert data['response_type'] == 'FAQ_ANSWER'
    assert data['case_id'] is None
    assert not data['show_emergency_banner']
    assert 'CASE-' not in data['message']
    assert 'dòng xe đang sử dụng' not in data['message']
    assert db.query(Case).count() == 0
    with get_store().connect() as conn:
        assert conn.execute('SELECT count(*) FROM cases').fetchone()[0] == 0


@pytest.mark.asyncio
async def test_current_failure_wins_explanation(client, chat_db):
    r = await client.post('/api/v1/customer/chat', json={'session_id': 'failure', 'message': 'Xe không chạy được, giải thích giúp tôi'})
    assert r.json()['data']['response_type'] == 'CLARIFICATION'


@pytest.mark.asyncio
async def test_reopened_and_repeated_emergency_reuse_case_and_brief(client, chat_db):
    db, _, _ = chat_db
    body = {'session_id': 'reopen', 'message': 'Xe bốc khói'}
    first = (await client.post('/api/v1/customer/chat', json=body)).json()['data']
    db.get(Case, first['case_id']).status = 'Reopened'
    db.commit()
    second = await client.post('/api/v1/customer/chat', json=body)
    assert second.status_code == 200
    assert second.json()['data']['case_id'] == first['case_id']
    assert db.query(Case).count() == 1
    assert db.query(CaseBrief).count() == 1


@pytest.mark.asyncio
async def test_location_action_has_matching_text(client, chat_db):
    r = await client.post('/api/v1/customer/chat', json={'session_id': 'location', 'message': 'Tìm trạm sạc gần tôi'})
    data = r.json()['data']
    assert data['request_location']
    assert 'trạm sạc' in data['message']
    assert 'tuổi thọ pin' not in data['message']
    assert data['case_id'] is None


@pytest.mark.asyncio
async def test_missing_soc_station_charger_not_fabricated(client, chat_db):
    db, _, _ = chat_db
    r = await client.post('/api/v1/customer/chat', json={'session_id': 'facts', 'message': 'VF8 bị kẹt súng sạc'})
    data = r.json()['data']
    fields = db.query(CaseBrief).filter_by(case_id=data['case_id']).one().captured_fields
    assert fields['current_soc'] is None
    assert fields['charger_id'] is None
    assert fields['error_code'] is None
    assert fields['station_location'] is None


@pytest.mark.asyncio
async def test_safety_ack_persists_without_resolving_and_new_danger_resets(client, chat_db):
    db, _, b = chat_db
    first = (await client.post('/api/v1/customer/chat', json={'session_id': 'safety', 'message': 'Xe bốc khói'})).json()['data']
    cid = first['case_id']
    url = f'/api/v1/customer/cases/{cid}/safety-acknowledgement'
    ack = await client.post(url, json={'incident_version': first['incident_version']})
    assert ack.status_code == 200
    assert ack.json()['data']['safety_status'] == 'customer_reported_safe'
    again = await client.post(url, json={'incident_version': first['incident_version']})
    assert again.json()['data'] == ack.json()['data']
    db.expire_all()
    case = db.get(Case, cid)
    assert case.priority == 'CRITICAL' and case.status == 'Staff Reviewing'
    status = (await client.get(f'/api/v1/customer/cases/{cid}/status')).json()['data']
    assert status['safety_status'] == 'customer_reported_safe'
    listed = (await client.get('/api/v1/customer/cases')).json()['data']['cases']
    assert next(c for c in listed if c['id'] == cid)['safety_status'] == 'customer_reported_safe'
    faq = (await client.post('/api/v1/customer/chat', json={'session_id': 'safety', 'message': 'Bảo hành pin là gì?'})).json()['data']
    assert faq['safety_status'] == 'customer_reported_safe'
    assert 'CASE-' not in faq['message']
    danger = (await client.post('/api/v1/customer/chat', json={'session_id': 'safety', 'message': 'Xe lại bốc khói'})).json()['data']
    assert danger['incident_version'] > first['incident_version']
    assert danger['safety_status'] == 'unconfirmed'
    stale = await client.post(url, json={'incident_version': first['incident_version']})
    assert stale.status_code == 409
    app.dependency_overrides[get_optional_user] = lambda: b
    assert (await client.post(url, json={'incident_version': danger['incident_version']})).status_code == 403


@pytest.mark.asyncio
async def test_request_id_retry_is_idempotent_and_mismatch_rejected(client, chat_db):
    db, _, _ = chat_db
    payload = {'session_id': 'retry', 'message': 'Xe bốc khói', 'request_id': 'request-1'}
    first = await client.post('/api/v1/customer/chat', json=payload)
    second = await client.post('/api/v1/customer/chat', json=payload)
    assert second.json()['data'] == first.json()['data']
    assert db.query(Message).count() == 2
    assert db.query(Case).count() == 1
    mismatch = await client.post('/api/v1/customer/chat', json={**payload, 'message': 'Xe mất phanh'})
    assert mismatch.status_code == 409


@pytest.mark.asyncio
async def test_explicit_handoff_is_one_web_case_readable_by_owner(client, chat_db):
    db, _, _ = chat_db
    r = await client.post('/api/v1/customer/chat', json={'session_id': 'handoff', 'message': 'Chuyển chuyên viên hỗ trợ giúp tôi'})
    data = r.json()['data']
    assert data['response_type'] == 'CASE_CREATED'
    assert data['case_id'] in data['message']
    assert db.query(Case).count() == 1
    assert (await client.get(f"/api/v1/customer/cases/{data['case_id']}")).status_code == 200
    with get_store().connect() as conn:
        assert conn.execute('SELECT count(*) FROM cases').fetchone()[0] == 0


@pytest.mark.asyncio
async def test_shared_mock_id_does_not_grant_case_access(client, chat_db):
    db, a, b = chat_db
    a.mock_customer_id = b.mock_customer_id = 'SHARED-MOCK'
    db.commit()
    first = (await client.post('/api/v1/customer/chat', json={'session_id': 'strict', 'message': 'Xe bốc khói'})).json()['data']
    app.dependency_overrides[get_optional_user] = lambda: b
    assert (await client.get(f"/api/v1/customer/cases/{first['case_id']}")).status_code == 403
    listed = await client.get('/api/v1/customer/cases')
    assert listed.json()['data']['total'] == 0


@pytest.mark.asyncio
async def test_turtle_reference_preserves_symbol_and_asks_operational_status(client, chat_db):
    await client.post('/api/v1/customer/chat', json={'session_id': 'symbol', 'message': 'Rùa vàng nghĩa là gì?'})
    r = await client.post('/api/v1/customer/chat', json={'session_id': 'symbol', 'message': 'Xe tôi đang hiện đây này'})
    data = r.json()['data']
    assert data['priority'] == 'HIGH'
    assert 'di chuyển' in data['message']
    assert data['case_id'] is None


@pytest.mark.asyncio
async def test_unverified_location_data_is_not_presented_as_nearby(client, chat_db):
    first = (await client.post('/api/v1/customer/chat', json={'session_id': 'points', 'message': 'Xe bốc khói'})).json()['data']
    points = (await client.get(f"/api/v1/customer/cases/{first['case_id']}/service-points")).json()['data']
    assert points['recommended_points'] == []


@pytest.mark.asyncio
async def test_concurrent_retries_compute_one_turn(client, chat_db):
    db, _, _ = chat_db
    payload = {'session_id': 'concurrent', 'message': 'Xe bốc khói', 'request_id': 'same-request'}
    responses = await asyncio.gather(*(client.post('/api/v1/customer/chat', json=payload) for _ in range(2)))
    assert all(r.status_code == 200 for r in responses)
    assert responses[0].json()['data'] == responses[1].json()['data']
    assert db.query(Case).count() == 1 and db.query(Message).count() == 2


@pytest.mark.asyncio
async def test_emergency_keeps_staff_progress_and_auditable_version(client, chat_db):
    db, _, _ = chat_db
    payload = {'session_id': 'progress', 'message': 'Xe bốc khói'}
    first = (await client.post('/api/v1/customer/chat', json=payload)).json()['data']
    case = db.get(Case, first['case_id'])
    case.status = 'In Progress'
    db.commit()
    second = (await client.post('/api/v1/customer/chat', json=payload)).json()['data']
    assert second['case_id'] == first['case_id']
    assert second['status'] == 'In Progress'
    assert second['incident_version'] == first['incident_version'] + 1


@pytest.mark.asyncio
async def test_handoff_preserves_emergency_evidence(client, chat_db):
    db, _, _ = chat_db
    first = (await client.post('/api/v1/customer/chat', json={'session_id': 'keep-brief', 'message': 'VF8 bốc khói'})).json()['data']
    brief = db.query(CaseBrief).filter_by(case_id=first['case_id']).one()
    before = (brief.summary, dict(brief.captured_fields), brief.suggested_action)
    reply = (await client.post('/api/v1/customer/chat', json={'session_id': 'keep-brief', 'message': 'Chuyển chuyên viên hỗ trợ giúp tôi'})).json()['data']
    db.refresh(brief)
    assert reply['case_id'] == first['case_id']
    assert (brief.summary, brief.captured_fields, brief.suggested_action) == before
    assert db.query(CaseBrief).count() == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['VF8 bị kẹt súng sạc', 'Xe tôi đang báo rùa vàng', 'Tôi khiếu nại dịch vụ showroom'])
async def test_guest_incident_does_not_create_ownerless_case_or_block_safety(client, chat_db, text):
    db, _, _ = chat_db
    app.dependency_overrides[get_optional_user] = lambda: None
    body = {'session_id': 'guest-incident', 'guest_session_id': 'guest-owner'}
    first = await client.post('/api/v1/customer/chat', json={**body, 'message': text})
    assert first.status_code == 200
    assert first.json()['data']['case_id'] is None
    assert db.query(Case).count() == 0
    danger = await client.post('/api/v1/customer/chat', json={**body, 'message': 'Xe bốc khói'})
    assert danger.status_code == 200 and danger.json()['data']['show_emergency_banner']
