import pytest

from src.models.db_models import CaseBrief, ChatSession

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']


@pytest.mark.asyncio
async def test_web_vague_location_cannot_pollute_memory_or_overwrite_brief(client, customer_db):
    sid = 'location-followup'
    first = await client.post('/api/v1/customer/chat', json={
        'session_id': sid,
        'message': 'Xe VF8 không sạc được tại trạm Metropolis, trụ P01, mã lỗi CC01',
    })
    assert first.status_code == 200
    cid = first.json()['data']['case_id']
    assert cid
    vague = await client.post('/api/v1/customer/chat', json={
        'session_id': sid, 'case_id': cid, 'message': 'Tôi vẫn đang ở cạnh xe',
    })
    assert vague.status_code == 200
    customer_db.expire_all()
    assert customer_db.get(ChatSession, sid).memory_states[sid]['captured_fields']['station_location'] == 'Metropolis'
    assert customer_db.query(CaseBrief).filter_by(case_id=cid).first().captured_fields['station_location'] == 'Metropolis'
    correction = await client.post('/api/v1/customer/chat', json={
        'session_id': sid, 'case_id': cid, 'message': 'Đính chính: tôi ở trạm sạc Vincom Landmark 81',
    })
    assert correction.status_code == 200
    customer_db.expire_all()
    assert customer_db.get(ChatSession, sid).memory_states[sid]['captured_fields']['station_location'] == 'Vincom Landmark 81'
    assert customer_db.query(CaseBrief).filter_by(case_id=cid).first().captured_fields['station_location'] == 'Vincom Landmark 81'


@pytest.mark.asyncio
async def test_web_unidentified_station_asks_for_details_without_saving_a_location(client, customer_db):
    sid = 'location-unknown'
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': sid, 'message': 'Xe VF8 không sạc được, tôi đang ở trạm sạc gần nhà',
    })
    assert response.status_code == 200
    data = response.json()['data']
    assert data['response_type'] == 'CLARIFICATION'
    assert 'trạm sạc' in data['message']
    fields = customer_db.get(ChatSession, sid).memory_states[sid]['captured_fields']
    assert 'station_location' not in fields and 'current_location' not in fields
