import pytest
from src.models.db_models import Case

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']


@pytest.mark.asyncio
@pytest.mark.parametrize('message', [
    'Xe VF8 đang bốc khói, có phải lỗi pin không?',
    'Xe VF8 đang mất phanh có đúng không?',
    'Xe VF8 không bốc khói nhưng phanh đang không ăn',
    'Phanh VF8 không ăn',
])
async def test_current_hazard_keeps_api_emergency_outcome(client, customer_db, message):
    data = (await client.post('/api/v1/customer/chat', json={'session_id':'clause-api', 'message':message})).json()['data']
    assert data['priority'] == 'CRITICAL'
    assert data['show_emergency_banner']
    assert not data['vehicle_cards']


@pytest.mark.asyncio
@pytest.mark.parametrize('message', [
    'Tôi không muốn khiếu nại, chỉ hỏi bảo hành VF8',
    'Xe VF8 không bị hỏng, tôi hỏi thông số',
])
async def test_denied_report_does_not_create_case(client, customer_db, message):
    response = await client.post('/api/v1/customer/chat', json={'session_id':'denied-api', 'message':message})
    assert response.status_code == 200
    assert customer_db.query(Case).filter_by(session_id='denied-api').count() == 0
    assert not response.json()['data']['show_emergency_banner']
