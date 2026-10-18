import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, get_db
from src.main import app
from src.models.db_models import Message, User
from src.services.auth import get_optional_user, require_customer


@pytest.mark.asyncio
@pytest.mark.parametrize('query, locale, headings, source_ids', [
    ('Hướng dẫn cách sạc tại trạm công cộng và biểu phí sạc.', 'vi',
     ['Cách sạc tại trạm công cộng', 'Biểu phí sạc'], {'SRC-010'}),
    ('Biểu phí sạc tại trạm và tính năng trên App VinFast.', 'vi',
     ['Biểu phí sạc', 'Tính năng trên App VinFast'], {'SRC-001'}),
    ('Hướng dẫn cách sạc tại trạm công cộng và chính sách bảo hành pin.', 'vi',
     ['Cách sạc tại trạm công cộng', 'Bảo hành pin'], {'SRC-010', 'SRC-002'}),
    ('How do I charge at a public station and what are the charging fees?', 'en',
     ['Charging at a public station', 'Charging fees'], {'SRC-010'}),
    ('Please explain battery warranty and scheduled maintenance.', 'en',
     ['Battery warranty', 'Scheduled maintenance'], {'SRC-002', 'SRC-004'}),
    ('Please explain public charging steps, charging fees, VinFast app features, battery warranty and scheduled maintenance.', 'en',
     ['Charging at a public station', 'Charging fees', 'VinFast app features', 'Battery warranty', 'Scheduled maintenance'],
     {'SRC-010', 'SRC-001', 'SRC-002', 'SRC-004'}),
])
async def test_compound_faq_variants_keep_all_requested_topics(client, language_db, monkeypatch, query, locale, headings, source_ids):
    from src.agents.nodes import rag_node as module
    search = module.vinfast_manual_search
    searches = []
    async def trace_search(subquery, **kwargs):
        result = await search(subquery, **kwargs)
        searches.append((subquery, result.get('status'), result.get('diagnostics')))
        return result
    monkeypatch.setattr(module, 'vinfast_manual_search', trace_search)
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'compound-variant', 'message': query, 'language': locale})
    assert response.status_code == 200
    data = response.json()['data']
    assert data['language'] == locale
    assert not data['show_emergency_banner']
    assert data['case_id'] is None
    for heading in headings:
        assert data['message'].count('### ' + heading) == 1
    assert {c['source_id'] for c in data['citations']} >= source_ids, searches
    if locale == 'en':
        assert 'Quý khách' not in data['message']


@pytest.mark.asyncio
@pytest.mark.parametrize('query, critical', [
    ('Cách sạc tại trạm, biểu phí sạc và tính năng App. Xe tôi đang bốc khói.', True),
    ('Chính sách bảo hành pin và lịch bảo dưỡng định kỳ. Xe tôi không bốc khói, không cháy.', False),
])
async def test_mixed_faq_never_overrides_current_hazard_or_invents_one(client, language_db, query, critical):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'compound-safety', 'message': query, 'language': 'vi'})
    assert response.status_code == 200
    data = response.json()['data']
    assert data['show_emergency_banner'] is critical
    if critical:
        assert data['priority'] == 'CRITICAL'
        assert 'Bước 4: Cắm súng sạc' not in data['message']


@pytest.mark.asyncio
@pytest.mark.parametrize('app_suffix', [' trên App VinFast', ''])
async def test_warranty_and_booking_instructions_keep_warranty_without_confirming_a_booking(client, language_db, app_suffix):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'warranty-booking-help',
        'message': 'Chính sách bảo hành pin và hướng dẫn đặt lịch bảo dưỡng' + app_suffix + '.', 'language': 'vi'})
    assert response.status_code == 200
    data = response.json()['data']
    assert '### Bảo hành pin' in data['message']
    assert '### Đặt lịch bảo dưỡng' in data['message']
    assert '### Tính năng trên App VinFast' not in data['message']
    assert 'SRC-002' in {c['source_id'] for c in data['citations']}
    assert 'đã đặt lịch thành công' not in data['message'].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize('query, expected, source_ids', [
    ('Please explain public charging, charging fees and VinFast app features.',
     'Charging at a public station', {'SRC-010', 'SRC-001'}),
    ('I would like to ask about battery warranty and scheduled maintenance.',
     'Battery warranty', {'SRC-002', 'SRC-004'}),
])
async def test_english_help_buttons_work_without_translation_model(client, language_db, query, expected, source_ids):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'english-help-button', 'message': query, 'language': 'en'})
    assert response.status_code == 200
    data = response.json()['data']
    assert data['language'] == 'en'
    assert expected in data['message']
    assert 'could not prepare' not in data['message']
    assert not any(word in data['message'] for word in ['Quý khách', 'Bảo hành', 'Theo tài liệu', 'trạm sạc'])
    assert {c['source_id'] for c in data['citations']} >= source_ids
    assert all('dưỡng' not in reply for reply in data['suggested_replies'] or [])
    history = (await client.get('/api/v1/customer/sessions/english-help-button/history')).json()['data']['messages']
    assert history[0]['content'] == query
    assert history[1]['content'] == data['message']


@pytest.fixture
def language_db(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "language.db"}')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(id='language-synthetic', username='language-synthetic', password_hash='unused', role='CUSTOMER')
        db.add(user)
        db.commit()
        app.dependency_overrides.update({get_db: lambda: db, get_optional_user: lambda: user, require_customer: lambda: user})
        yield db
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.asyncio
async def test_english_cards_and_history_preserve_original_input_and_locale(client, language_db):
    message = 'Tell me about the VF7'
    response = await client.post('/api/v1/customer/chat', json={'session_id': 'english-cards', 'message': message})
    assert response.status_code == 200
    data = response.json()['data']
    assert data['language'] == 'en'
    assert [c['variant'] for c in data['vehicle_cards']] == ['eco', 'plus', 'plus-awd']
    assert 'Here are' in data['message']
    assert 'Chưa' not in data['message']
    history = (await client.get('/api/v1/customer/sessions/english-cards/history')).json()['data']['messages']
    assert history[0]['content'] == message
    assert history[1]['content'] == data['message']
    assert all(m['language'] == 'en' for m in history)


@pytest.mark.asyncio
@pytest.mark.parametrize('query', ["My brakes don't work", 'My brakes are not responding.', 'There are flames at the charging port of my VF7'])
async def test_guest_quota_never_blocks_english_emergency(client, language_db, query):
    app.dependency_overrides[get_optional_user] = lambda: None
    for i in range(5):
        language_db.add(Message(id=f'quota-{i}', session_id='english-quota', sender_type='CUSTOMER', content='previous'))
    language_db.commit()
    response = await client.post('/api/v1/customer/chat', json={'session_id': 'english-quota', 'message': query})
    assert response.status_code == 200
    data = response.json()['data']
    assert data['priority'] == 'CRITICAL'
    assert data['show_emergency_banner']
    assert data['language'] == 'en'
    assert data['case_id'] is None
    assert 'safe' in data['safe_guidance'].lower()


@pytest.mark.asyncio
async def test_explicit_output_locale_keeps_vietnamese_product_understanding(client, language_db):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'locale-preference', 'message': 'Tư vấn VF8', 'language': 'en'})
    data = response.json()['data']
    assert data['language'] == 'en'
    assert {c['model'] for c in data['vehicle_cards']} == {'VF8'}
    assert 'Here are' in data['message']


@pytest.mark.asyncio
@pytest.mark.parametrize('query', ['Cảm ơn bạn, tôi hiểu rồi', 'Cám ơn bạn!', 'Cảm ơn, tôi đã hiểu'])
async def test_vietnamese_thanks_with_addressee_is_acknowledged(client, language_db, query):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'thanks-with-addressee', 'message': query})
    assert response.status_code == 200
    data = response.json()['data']
    assert 'rất vui được hỗ trợ' in data['message']
    assert not data['vehicle_cards']


@pytest.mark.asyncio
async def test_thanks_prefix_does_not_swallow_a_new_question(client, language_db):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'thanks-with-question', 'message': 'Cảm ơn bạn, tư vấn VF7'})
    assert response.status_code == 200
    assert 'Khi cần thêm thông tin' not in response.json()['data']['message']


@pytest.mark.asyncio
async def test_unassigned_complaint_does_not_claim_a_specialist_is_working(client, language_db):
    from src.models.db_models import Case
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'complaint-receipt', 'message': 'Tôi muốn khiếu nại thái độ nhân viên showroom'})
    assert response.status_code == 200
    data = response.json()['data']
    case = language_db.get(Case, data['case_id'])
    assert case.assigned_staff_id is None
    assert 'đang xử lý' not in data['safe_guidance']
    assert 'chờ' in data['safe_guidance'].lower()


@pytest.mark.asyncio
async def test_out_of_scope_reply_does_not_claim_an_unexecuted_database_search(client, language_db):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'weather-truth', 'message': 'Thời tiết ngày mai thế nào?'})
    data = response.json()['data']
    assert 'cơ sở dữ liệu' not in data['message']
    assert 'ngoài phạm vi' in data['message']


@pytest.mark.asyncio
async def test_trim_followup_uses_reviewed_product_snapshot(client, language_db):
    for message in ['Tư vấn VF7', 'Còn bản Plus thì sao?']:
        response = await client.post('/api/v1/customer/chat', json={
            'session_id': 'trim-followup-snapshot', 'message': message})
        assert response.status_code == 200
    data = response.json()['data']
    assert '830.000.000' in data['message']
    assert '788.500.000' not in data['message']
    assert 'đời xe' not in data['message']
    assert data['citations']


@pytest.mark.asyncio
async def test_safe_place_followup_keeps_the_same_workflow_in_both_languages(client, language_db):
    results = []
    for language, hazard, safe in [
        ('vi', 'Xe VF8 của tôi đang bốc khói ở khoang pin', 'Tôi đã ở nơi an toàn'),
        ('en', 'My VF8 is emitting smoke from the battery compartment', 'I am in a safe place now'),
    ]:
        session = f'safe-place-parity-{language}'
        first = (await client.post('/api/v1/customer/chat', json={
            'session_id':session,'message':hazard,'language':language})).json()['data']
        second = (await client.post('/api/v1/customer/chat', json={
            'session_id':session,'message':safe,'language':language})).json()['data']
        assert second['case_id'] == first['case_id']
        assert second['language'] == language
        assert second['priority'] == 'CRITICAL'
        assert second['show_emergency_banner'] is True
        assert second['safety_status'] != 'completed'
        results.append(tuple(second.get(k) for k in ('response_type','priority','show_emergency_banner','safety_status')))
    assert results[0] == results[1]


@pytest.mark.asyncio
@pytest.mark.parametrize('query,language', [
    ('Tôi muốn đặt lịch sửa xe VF7', 'vi'),
    ('Tôi muốn đặt lịch sửa chữa xe VF7', 'vi'),
    ('I would like to book a repair appointment for my VF7', 'en'),
])
async def test_repair_booking_uses_external_service_flow(client, language_db, query, language):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'repair-booking', 'message': query, 'language': language})
    assert response.status_code == 200
    data = response.json()['data']
    assert ('chưa thể đặt lịch' if language == 'vi' else 'No appointment has been booked') in data['message']
    assert ('sửa chữa' if language == 'vi' else 'service center') in data['message']
    assert data['case_id'] is None
    assert not data['citations']


@pytest.mark.asyncio
async def test_english_safe_report_is_acknowledged_without_persisted_confirmation(client, language_db):
    from src.models.db_models import Case
    session = 'safe-followup-acknowledgment'
    first = (await client.post('/api/v1/customer/chat', json={
        'session_id': session, 'message': 'My VF8 is emitting smoke from the battery compartment',
        'language': 'en'})).json()['data']
    second = (await client.post('/api/v1/customer/chat', json={
        'session_id': session, 'message': 'I am in a safe place now', 'language': 'en'})).json()['data']
    assert 'you reported being in a safe place' in second['message']
    assert second['message'] != first['message']
    assert 'not yet been saved' in second['message']
    assert second['case_id'] == first['case_id']
    assert second['show_emergency_banner'] is True
    assert second['priority'] == 'CRITICAL'
    assert second['emergency_context']['safety_status'] == 'unconfirmed'
    assert language_db.get(Case, first['case_id']).safety_status == 'unconfirmed'

@pytest.mark.asyncio
@pytest.mark.parametrize('query,language', [('Tư vấn xe','vi'),('tu van xe','vi'),('Tôi muốn tư vấn mua xe','vi'),('Tư vấn chung về xe','vi'),('Tư vấn cho tôi về xe','vi'),('Tôi muốn tìm hiểu các mẫu xe VinFast','vi'),('Vehicle advice','en'),('Tell me about VinFast cars','en')])
async def test_general_advice_has_two_model_branches_and_no_cards(client, language_db, query, language):
    response = await client.post('/api/v1/customer/chat', json={'session_id':'general-branches','message':query,'language':language})
    assert response.status_code == 200
    data=response.json()['data']
    assert data['vehicle_cards'] == []
    assert data['suggested_replies'] == (['Tư vấn xe VF3','Tư vấn xe VF8'] if language=='vi' else ['Tell me about VF3','Tell me about VF8'])
    assert ('mẫu xe nào' if language=='vi' else 'Which model') in data['message']
    follow=await client.post('/api/v1/customer/chat',json={'session_id':'general-branches','message':data['suggested_replies'][1],'language':language})
    assert follow.status_code == 200
    assert {c['model'] for c in follow.json()['data']['vehicle_cards']} == {'VF8'}
