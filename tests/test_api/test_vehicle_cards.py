import pytest

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']


@pytest.mark.asyncio
async def test_vehicle_card_is_returned_and_restored(client, customer_db):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'vehicle-card-vf5', 'message': 'VF5',
    })
    assert response.status_code == 200
    data = response.json()['data']
    assert data['vehicle_cards'][0]['model'] == 'VF5'
    assert 'thông tin công bố' in data['message']
    assert data['vehicle_cards'][0]['image_url'].startswith('https://static-cms-prod.vinfastauto.com/')
    history = await client.get('/api/v1/customer/sessions/vehicle-card-vf5/history')
    assert history.json()['data']['messages'][-1]['vehicle_cards'] == data['vehicle_cards']


def test_card_selection_does_not_turn_incident_followup_into_sales():
    from src.services.vehicle_catalog import select_vehicle_cards
    assert select_vehicle_cards('VF6', active_goal='incident') == []
    assert select_vehicle_cards('VF5 bị mất phanh') == []
    assert select_vehicle_cards('Tư vấn VF5 đang cháy', active_goal='incident') == []
    assert select_vehicle_cards('Tư vấn VF5 không khởi động được', active_goal='incident') == []
    assert select_vehicle_cards('bảo hành VF5 bao lâu?') == []
    assert select_vehicle_cards('VF50') == []
    assert [c.model for c in select_vehicle_cards('So sánh VF5 và VF6')] == ['VF5', 'VF6']
    assert len(select_vehicle_cards('Tư vấn các dòng xe VinFast')) == 6
    assert select_vehicle_cards('Giá VF5 bao nhiêu?')[0].model == 'VF5'
    assert select_vehicle_cards('VF6 đi được bao nhiêu km?')[0].model == 'VF6'


@pytest.mark.asyncio
async def test_critical_incident_never_receives_sales_cards(client, customer_db):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'vehicle-card-emergency', 'message': 'Tư vấn VF5 đang cháy',
    })
    assert response.status_code == 200
    assert response.json()['data']['vehicle_cards'] == []


@pytest.mark.asyncio
@pytest.mark.parametrize('question', ['VF8', 'Tư vấn xe VF8'])
async def test_vf8_overview_includes_variants_summary_and_actions(client, customer_db, question):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'vf8-variants', 'message': question,
    })
    data = response.json()['data']
    cards = data['vehicle_cards']
    assert [card['name'] for card in cards] == ['VinFast VF 8 Eco', 'VinFast VF 8 Plus']
    assert all(len(card['specs']) == 4 for card in cards)
    assert all('dang-ky-lai-thu' in card['test_drive_url'] for card in cards)
    assert 'VF 8 Eco' in data['message'] and 'VF 8 Plus' in data['message']
    assert len(data['suggested_replies']) == 2
    history = await client.get('/api/v1/customer/sessions/vf8-variants/history')
    assert history.json()['data']['messages'][-1]['suggested_replies'] == data['suggested_replies']


def test_explicit_vf8_variant_selects_only_requested_version():
    from src.services.vehicle_catalog import select_vehicle_cards
    assert [card.name for card in select_vehicle_cards('VF8 Plus')] == ['VinFast VF 8 Plus']
    assert [card.name for card in select_vehicle_cards('Thông số VF8 Eco')] == ['VinFast VF 8 Eco']
    assert [card.name for card in select_vehicle_cards('VF8 bản Plus')] == ['VinFast VF 8 Plus']
    assert len(select_vehicle_cards('So sánh VF8 Eco và Plus')) == 2


@pytest.mark.asyncio
async def test_comparison_has_shared_rows_and_matching_summary(client, customer_db):
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'compare-vf6-vf8', 'message': 'So sánh VF6 Eco và VF8 Eco',
    })
    data = response.json()['data']
    assert data['vehicle_comparison'] is True
    assert len(data['vehicle_cards']) == 2
    assert '59,6 kWh' in data['message'] and '87,7 kWh' in data['message']
    assert '635 km (NEDC)' in data['message']
    assert 'Thông số theo FAQ' not in data['message']
    history = await client.get('/api/v1/customer/sessions/compare-vf6-vf8/history')
    assert history.json()['data']['messages'][-1]['vehicle_comparison'] is True


@pytest.mark.asyncio
async def test_specific_comparison_preserves_answer_to_the_question(client, customer_db, monkeypatch):
    import src.api.customer as api
    async def answer(*args, **kwargs):
        return {'reply': 'Thông tin bảo hành riêng cho hai mẫu xe', 'citations': []}
    monkeypatch.setattr(api, 'process_chat_message', answer)
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'compare-warranty', 'message': 'So sánh bảo hành VF6 và VF8',
    })
    assert 'Thông tin bảo hành riêng' in response.json()['data']['message']

@pytest.mark.parametrize('question', [
    'Tư vấn bảo hành VF8', 'So sánh bảo hành VF6 và VF8',
    'Tư vấn cách sạc VF8', 'Giá sạc VF8 bao nhiêu?',
    'Giá thay pin VF8 bao nhiêu?', 'Thông số áp suất lốp VF8',
    'Tư vấn bảo dưỡng VF8', 'So sánh ADAS VF6 và VF8',
    'Tôi không muốn tư vấn xe VF8, chỉ hỏi cách dùng ứng dụng',
    'Đừng hiện card VF8', 'Tư vấn ứng dụng VinFast cho VF8',
    'Hướng dẫn lái thử VF8 an toàn', 'Khiếu nại giá xe VF8',
])
def test_service_questions_never_receive_product_cards(question):
    from src.services.vehicle_catalog import select_vehicle_cards
    assert select_vehicle_cards(question) == []


@pytest.mark.parametrize('question', [
    'Tư vấn xe VF8', 'VF8', 'Giá VF5 bao nhiêu?',
    'So sánh VF6 Eco và VF8 Eco', 'Thông số VF8 Eco',
    'VF6 đi được bao nhiêu km?', 'Đăng ký lái thử VF8',
    'Tư vấn mua xe VF8 và chính sách bảo hành',
    'Thông số dung lượng pin VF8', 'So sánh thời gian sạc VF6 và VF8',
    'Tôi không biết nên mua VF6 hay VF8',
])
def test_product_questions_keep_cards(question):
    from src.services.vehicle_catalog import select_vehicle_cards
    assert select_vehicle_cards(question)


@pytest.mark.parametrize('goal', ['incident', 'warranty', 'maintenance', 'charging', 'concept'])
def test_bare_model_continues_non_sales_conversation_without_card(goal):
    from src.services.vehicle_catalog import select_vehicle_cards
    assert select_vehicle_cards('VF8', active_goal=goal) == []


@pytest.mark.asyncio
@pytest.mark.parametrize('question', ['Tư vấn bảo hành VF8', 'Giá sạc VF8 bao nhiêu?', 'Thông số áp suất lốp VF8'])
async def test_non_product_api_has_no_card_or_card_actions(client, customer_db, monkeypatch, question):
    import src.api.customer as api
    async def answer(*args, **kwargs):
        return {'reply': 'Câu trả lời đúng chủ đề dịch vụ', 'citations': []}
    monkeypatch.setattr(api, 'process_chat_message', answer)
    monkeypatch.setattr(api, 'answer_sales_question', answer)
    response = await client.post('/api/v1/customer/chat', json={'session_id': 'card-scope-service', 'message': question})
    assert response.status_code == 200
    data = response.json()['data']
    assert data['vehicle_cards'] == []
    assert not data['vehicle_comparison']
    assert not any('Dự toán lăn bánh' in reply for reply in data.get('suggested_replies') or [])
    history = await client.get('/api/v1/customer/sessions/card-scope-service/history')
    assert history.json()['data']['messages'][-1]['vehicle_cards'] == []

@pytest.mark.parametrize('question', [
    'Tư vấn bảo hành khi mua VF8',
    'Tư vấn cách sạc để mua xe VF8',
    'Tôi không cần tư vấn mua xe VF8, chỉ hỏi bảo dưỡng',
])
def test_incidental_purchase_reference_does_not_change_service_intent(question):
    from src.services.vehicle_catalog import select_vehicle_cards
    assert select_vehicle_cards(question) == []


def test_quote_followup_uses_topic_to_avoid_charging_cost_cards():
    from src.services.vehicle_catalog import select_vehicle_cards
    assert select_vehicle_cards('VF8', active_goal='quote', context_topic='Giá sạc bao nhiêu?') == []
    assert select_vehicle_cards('VF8', active_goal='quote', context_topic='Giá xe bao nhiêu?')

@pytest.mark.parametrize('question', [
    'Thay pin VF8 bao nhiêu tiền?',
    'Tôi không hỏi giá VF8, chỉ hỏi bảo hành',
    'So sánh app VF6 và VF8',
])
def test_reviewed_scope_leaks_are_blocked(question):
    from src.services.vehicle_catalog import select_vehicle_cards
    assert select_vehicle_cards(question) == []


def test_denied_model_is_not_selected_with_affirmative_purchase():
    from src.services.vehicle_catalog import select_vehicle_cards
    assert [card.model for card in select_vehicle_cards('Tôi không mua VF8, tư vấn mua VF6')] == ['VF6']

@pytest.mark.parametrize('question', ['Tư vấn xe VF8 về cách sạc', 'Không cần thông số VF8'])
def test_service_focus_and_direct_negation_override_general_product_words(question):
    from src.services.vehicle_catalog import select_vehicle_cards
    assert select_vehicle_cards(question) == []
