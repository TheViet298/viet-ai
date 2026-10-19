import pytest

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']


@pytest.mark.parametrize('model', ['VF3', 'VF6', 'VF7', 'VF8', 'VF9'])
def test_comparison_without_trim_defaults_to_eco(model):
    from src.services.vehicle_catalog import select_vehicle_cards
    cards = select_vehicle_cards(f'So sánh VF5 và {model}')
    assert [(card.model, card.variant) for card in cards] == [('VF5', None), (model, 'eco')]


@pytest.mark.asyncio
async def test_history_title_generation_cannot_overwrite_new_conversation_memory(client, customer_db, monkeypatch):
    import src.api.customer as api
    from src.models.db_models import ChatSession, Message
    from sqlalchemy.orm import Session
    from sqlalchemy import update
    session_id = 'title-concurrent-memory'
    customer_db.add(ChatSession(id=session_id, owner='user:regression-customer', memory_states={}))
    customer_db.add(Message(id='title-message', session_id=session_id, sender_type='CUSTOMER', content='Giá VF5 bao nhiêu?'))
    customer_db.commit()
    memory = {session_id: {'conversation_context': {'subject': 'VF5', 'active_goal': 'quote'}}}

    def title_while_turn_finishes(messages):
        with Session(customer_db.get_bind()) as writer:
            writer.execute(update(ChatSession).where(ChatSession.id == session_id).values(memory_states=memory))
            writer.commit()
        return 'Giá VF5 bao nhiêu?'

    monkeypatch.setattr(api, 'extract_session_title', title_while_turn_finishes)
    response = await client.get('/api/v1/customer/sessions')
    assert response.status_code == 200
    customer_db.expire_all()
    assert customer_db.get(ChatSession, session_id).memory_states == memory


@pytest.mark.asyncio
@pytest.mark.parametrize('followup,models,comparison', [
    ('Còn VF7 thì sao?', {'VF7'}, False),
    ('So sánh với VF7', {'VF5', 'VF7'}, True),
])
async def test_product_followup_keeps_cards_and_previous_comparison_model(client, customer_db, followup, models, comparison):
    session = 'product-followup'
    for message in ['Giá VF5 bao nhiêu?', followup]:
        response = await client.post('/api/v1/customer/chat', json={'session_id': session, 'message': message})
        assert response.status_code == 200
    data = response.json()['data']
    assert {card['model'] for card in data['vehicle_cards']} == models
    assert all(card['image_url'] for card in data['vehicle_cards'])
    assert data['vehicle_comparison'] is comparison
    history = await client.get(f'/api/v1/customer/sessions/{session}/history')
    assert history.json()['data']['messages'][-1]['vehicle_cards'] == data['vehicle_cards']


@pytest.mark.asyncio
@pytest.mark.parametrize('followup', [
    'so với VF3', 'So với VF 3?', 'so voi vf3', 'So sánh với VF3',
])
async def test_short_comparison_keeps_previously_advised_model(client, customer_db, followup):
    session = 'short-comparison-followup'
    for message in ['tư vấn VF8', followup]:
        response = await client.post('/api/v1/customer/chat', json={
            'session_id': session, 'message': message})
        assert response.status_code == 200
    data = response.json()['data']
    assert data['vehicle_comparison'] is True
    assert [card['model'] for card in data['vehicle_cards']] == ['VF8', 'VF3']
    assert len(data['vehicle_cards']) == 2
    history = (await client.get(f'/api/v1/customer/sessions/{session}/history')).json()['data']['messages']
    assert history[-1]['vehicle_comparison'] is True
    assert history[-1]['vehicle_cards'] == data['vehicle_cards']


@pytest.mark.asyncio
@pytest.mark.parametrize('followup', ['so bản plus', 'So sánh bản Plus?', 'so ban plus'])
async def test_comparison_trim_followup_keeps_both_models(client, customer_db, followup):
    session = 'comparison-trim-followup'
    for message in ['tư vấn VF8', 'so với VF3', followup, 'so bản eco']:
        response = await client.post('/api/v1/customer/chat', json={
            'session_id': session, 'message': message})
        assert response.status_code == 200
        if message in {followup, 'so bản eco'}:
            data = response.json()['data']
            expected = 'eco' if message == 'so bản eco' else 'plus'
            assert data['vehicle_comparison'] is True
            assert [(c['model'], c['variant']) for c in data['vehicle_cards']] == [
                ('VF8', expected), ('VF3', expected)]
            assert len(data['citations']) == 2
            assert all(expected in c['title'].casefold() for c in data['citations'])
    history = (await client.get(f'/api/v1/customer/sessions/{session}/history')).json()['data']['messages']
    assert history[-1]['vehicle_cards'] == data['vehicle_cards']
    assert history[-1]['citations'] == data['citations']


@pytest.mark.asyncio
async def test_new_model_overview_clears_previous_comparison_for_trim_followup(client, customer_db):
    for message in ['tư vấn VF8', 'so với VF3', 'tư vấn VF7', 'so bản plus']:
        response = await client.post('/api/v1/customer/chat', json={
            'session_id': 'comparison-reset', 'message': message})
        assert response.status_code == 200
    data = response.json()['data']
    assert not any(c['model'] in {'VF8', 'VF3'} for c in data['vehicle_cards'])
    assert data['vehicle_comparison'] is False


@pytest.mark.parametrize('model,variants', [('VF3', ['eco', 'plus']), ('VF5', [None]),
    ('VF6', ['eco', 'plus']), ('VF7', ['eco', 'plus', 'plus-awd']),
    ('VF8', ['eco', 'plus']), ('VF9', ['eco', 'plus'])])
def test_each_model_overview_contains_all_reviewed_versions(model, variants):
    from src.services.vehicle_catalog import select_vehicle_cards
    assert [c.variant for c in select_vehicle_cards('Tư vấn về ' + model)] == variants


@pytest.mark.parametrize('model', ['VF3', 'VF6', 'VF7', 'VF8', 'VF9'])
def test_explicit_plus_never_returns_eco(model):
    from src.services.vehicle_catalog import select_vehicle_cards
    cards = select_vehicle_cards('Tư vấn về ' + model + ' Plus')
    assert len(cards) == 1 and cards[0].variant == 'plus'


def test_vf7_plus_fwd_and_awd_do_not_mix_specs_or_prices():
    from src.services.vehicle_catalog import select_vehicle_cards
    fwd = select_vehicle_cards('VF7 Plus')[0]
    awd = select_vehicle_cards('VF7 Plus AWD')[0]
    assert fwd.name == 'VinFast VF 7 Plus'
    assert '500,5 km (NEDC)' in [s.value for s in fwd.specs]
    assert '150 kW' in [s.value for s in fwd.specs]
    assert fwd.price_label == 'Từ 830.000.000 VNĐ'
    assert awd.variant == 'plus-awd'
    assert '469 km (NEDC)' in [s.value for s in awd.specs]
    assert '260 kW' in [s.value for s in awd.specs]
    assert awd.price_label == 'Chưa có giá xác thực'


def test_cross_model_comparison_uses_only_the_requested_versions():
    from src.services.vehicle_catalog import select_vehicle_cards
    cards = select_vehicle_cards('So sánh VF7 Plus và VF6 Eco')
    assert [(c.model, c.variant) for c in cards] == [('VF7', 'plus'), ('VF6', 'eco')]
    assert len(select_vehicle_cards('So sánh VF7 và VF6')) == 2
    assert select_vehicle_cards('VF5 Plus') == []


@pytest.mark.asyncio
@pytest.mark.parametrize('model,count', [('VF3', 2), ('VF5', 1), ('VF6', 2), ('VF7', 3), ('VF8', 2), ('VF9', 2)])
async def test_model_versions_are_returned_and_restored(client, customer_db, model, count):
    session_id = 'model-versions-' + model
    response = await client.post('/api/v1/customer/chat', json={'session_id': session_id, 'message': 'Tư vấn về ' + model})
    assert response.status_code == 200
    data = response.json()['data']
    assert len(data['vehicle_cards']) == count
    assert all(c['name'] in data['message'] for c in data['vehicle_cards'])
    history = (await client.get(f'/api/v1/customer/sessions/{session_id}/history')).json()['data']['messages']
    assert history[-1]['vehicle_cards'] == data['vehicle_cards']


def test_same_model_comparison_preserves_order_and_awd_version():
    from src.services.vehicle_catalog import select_vehicle_cards, is_generic_vehicle_comparison
    question = 'So sánh VF7 Plus AWD và VF7 Eco'
    assert is_generic_vehicle_comparison(question)
    assert [c.variant for c in select_vehicle_cards(question)] == ['plus-awd', 'eco']


@pytest.mark.parametrize('question', ['Thông số VF7 Eco AWD', 'Thông số VF6 Eco AWD',
                                    'So sánh VF7 Plus và VF6 Eco AWD'])
def test_unsupported_drive_configuration_is_not_split_or_partially_compared(question):
    from src.services.vehicle_catalog import select_vehicle_cards
    assert select_vehicle_cards(question) == []


@pytest.mark.parametrize('model', ['VF8', 'VF9'])
def test_awd_alias_preserves_existing_plus_version(model):
    from src.services.vehicle_catalog import select_vehicle_cards
    cards = select_vehicle_cards('Thông số ' + model + ' Plus AWD')
    assert len(cards) == 1 and cards[0].variant == 'plus'


def test_vf8_drive_labels_match_existing_versions():
    from src.services.vehicle_catalog import select_vehicle_cards
    assert [c.variant for c in select_vehicle_cards('Thông số VF8 Eco FWD')] == ['eco']
    assert [c.variant for c in select_vehicle_cards('So sánh VF8 Eco FWD và VF8 Plus AWD')] == ['eco', 'plus']


@pytest.mark.asyncio
@pytest.mark.parametrize('question,model', [('Tư vấn về VF 7', 'VF7'), ('Tư vấn VF5', 'VF5'),
    ('Giới thiệu về VF 6', 'VF6'), ('Thông tin về VF 9', 'VF9'), ('Tư vấn về VF 8', 'VF8')])
async def test_natural_overview_after_quote_starts_new_topic(client, customer_db, question, model):
    from src.models.db_models import ChatSession
    await client.post('/api/v1/customer/chat', json={
        'session_id': 'natural-overview', 'message': 'Dự toán lăn bánh VF8 Eco',
    })
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'natural-overview', 'message': question,
    })
    assert response.status_code == 200
    data = response.json()['data']
    assert data['vehicle_cards'] and all(c['model'] == model for c in data['vehicle_cards'])
    assert 'chi-phi-lan-banh' not in data['message']
    session = customer_db.get(ChatSession, 'natural-overview')
    turn = session.memory_states['natural-overview']['turn_understanding']
    assert turn['move'] == 'new_question'
    assert turn['goal'] == 'overview'


@pytest.mark.parametrize('question', ['Tư vấn về bảo dưỡng VF7', 'Tư vấn về VF7 bị mất phanh',
    'Không cần tư vấn về VF7, tôi hỏi bảo hành', 'VF7 có những màu gì?', 'Tư vấn về VF7 lỗi sạc'])
def test_natural_advice_does_not_promote_service_or_color_questions(question):
    from src.services.vehicle_catalog import select_vehicle_cards
    assert select_vehicle_cards(question) == []


def test_bare_model_continues_product_browsing():
    from src.services.vehicle_catalog import select_vehicle_cards
    assert select_vehicle_cards('VF5', active_goal='overview')[0].model == 'VF5'


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
    assert select_vehicle_cards('Tư vấn các dòng xe VinFast') == []
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
    cards = select_vehicle_cards('Tôi không mua VF8, tư vấn mua VF6')
    assert {card.model for card in cards} == {'VF6'}
    assert [card.variant for card in cards] == ['eco', 'plus']

@pytest.mark.parametrize('question', ['Tư vấn xe VF8 về cách sạc', 'Không cần thông số VF8'])
def test_service_focus_and_direct_negation_override_general_product_words(question):
    from src.services.vehicle_catalog import select_vehicle_cards
    assert select_vehicle_cards(question) == []


def test_estimate_chip_and_equivalent_on_road_price_have_the_same_card():
    from src.services.vehicle_catalog import select_vehicle_cards
    estimate = select_vehicle_cards('Dự toán lăn bánh VinFast VF8 Plus')
    equivalent = select_vehicle_cards('Giá lăn bánh VinFast VF8 Plus bao nhiêu?')
    assert [(c.model, c.variant) for c in estimate] == [('VF8','plus')]
    assert estimate == equivalent
