import json
from pathlib import Path

import pytest

from src.services.rag_service import RAGService
from src.services.vehicle_catalog import catalog_facts


def test_vf5_usable_capacity_has_its_own_review_without_rewriting_other_dates():
    fact = next(fact for fact in catalog_facts() if fact['scope']['model'] == 'VF5')
    assert fact['scope']['battery_capacity_kwh'] == 37.23
    assert fact['claim_evidence']['capacity']['reviewed_at'] == '2026-10-19'
    assert fact['claim_evidence']['range']['reviewed_at'] == '2026-10-12'
    assert fact['price']['reviewed_at'] == '2026-10-16'
    assert fact['scope']['model_year'] is None
    assert all(fact['scope']['battery_capacity_kwh'] is None for fact in catalog_facts() if fact['scope']['model'] == 'VF3')


def test_vf3_schedule_keeps_model_operation_months_and_footnote():
    result = RAGService().retrieve('VF3 bảo dưỡng định kỳ lần đầu ở bao nhiêu km?', vehicle_model='VF3')
    assert result['status'] == 'SUCCESS'
    citation = result['citations'][0]
    assert citation['source_id'] == 'SRC-004'
    assert citation['model'] == 'VF3' and citation['model_year'] is None
    assert citation['operation'] == 'scheduled_maintenance'
    assert citation['interval_km'] == 15000 and citation['interval_months'] == 12
    assert 'đến trước' in citation['relevant_snippet']
    assert '150.000' not in citation['relevant_snippet']  # coolant/cycle horizon is not the first interval


@pytest.mark.parametrize('query,model', [
    ('VF8 đời 2025 bảo dưỡng định kỳ lần đầu ở bao nhiêu km?', 'VF8'),
    ('VF3 đời 2025 bảo dưỡng định kỳ khi nào?', 'VF3'),
    ('VF3 chạy dịch vụ thương mại bảo dưỡng định kỳ khi nào?', 'VF3'),
    ('VF3 cần thay dung dịch làm mát định kỳ khi nào?', 'VF3'),
])
def test_schedule_does_not_cross_unknown_scope(query, model):
    from src.services.reviewed_knowledge import reviewed_maintenance_schedules
    assert not reviewed_maintenance_schedules(query, model)


def test_vf5_model_colors_are_not_trim_or_year_assertions():
    from src.services.reviewed_knowledge import reviewed_model_colors
    rows = reviewed_model_colors('VF5 có những màu gì?', 'VF5')
    assert rows and 'Urban Mint' in rows[0]['relevant_snippet']
    assert 'tồn kho' not in rows[0]['relevant_snippet']
    for query in ['VF5 Plus màu nào?', 'VF5 đời 2025 có màu gì?', 'VF5 màu nào còn hàng hôm nay?']:
        assert not reviewed_model_colors(query, 'VF5')


def test_pending_review_schedule_is_not_runtime_authority(monkeypatch, tmp_path):
    from src.services import reviewed_knowledge
    path = tmp_path / 'maintenance_schedules.json'
    path.write_text(json.dumps([{'model': 'VF3', 'review_status': 'pending_review',
                                'operation': 'scheduled_maintenance', 'model_year': None}]), encoding='utf-8')
    monkeypatch.setattr(reviewed_knowledge, 'SCHEDULE_PATH', path)
    assert not reviewed_knowledge.reviewed_maintenance_schedules('Lịch bảo dưỡng VF3?', 'VF3')


@pytest.mark.asyncio
@pytest.mark.parametrize('question,model,required', [
    ('Lịch bảo dưỡng định kỳ VF3 là gì?', 'VF3', ['15.000', '12 tháng', 'đến trước']),
    ('Dung lượng pin VF5 là bao nhiêu?', 'VF5', ['37,23', 'kWh']),
    ('VF5 có những màu gì?', 'VF5', ['Urban Mint']),
])
async def test_reviewed_data_can_be_delivered_with_claim_validation(monkeypatch, question, model, required):
    from src.agents.nodes import rag_node as module
    async def search(query, **kwargs):
        return RAGService().retrieve(query, **kwargs)
    monkeypatch.setattr(module, 'vinfast_manual_search', search)
    result = await module.rag_node({'latest_user_message': question, 'vehicle_model': model, 'confidence_score': .9})
    assert not result['is_no_source'], result['retrieval_diagnostics']
    assert result['answer_status'] == 'answered'
    assert all(term in result['response'] for term in required)
    if question.endswith('màu gì?'):
        assert 'tồn kho' not in result['response'].casefold()
    assert result['rag_citations']


@pytest.mark.parametrize('question', ['Lịch bảo dưỡng VF3 đời 2025 là gì?',
                                   'Lịch bảo dưỡng VF3 chạy dịch vụ thương mại là gì?'])
def test_index_fallback_cannot_bypass_reviewed_scope(question):
    from src.services.rag_service import source_registry
    source = source_registry()['SRC-004']
    meta = {**source, 'source_id': 'SRC-004', 'applicable_models': 'VF3',
            'reviewed_scope_json': json.dumps({'model': 'VF3', 'model_year': None, 'variant': None, 'usage': None})}
    rows = {'documents': [['Lịch bảo dưỡng VF3\nVF3 bảo dưỡng định kỳ mỗi 15.000 km hoặc 12 tháng tùy điều kiện nào đến trước.']],
            'metadatas': [[meta]], 'distances': [[.1]], 'ids': [['reviewed-schedule']]}
    assert RAGService().filter_results(rows, 'VF3', question)['status'] == 'NO_SOURCE'


@pytest.mark.parametrize('question,model,required', [
    ('VF5 tầm di chuyển công bố bao nhiêu, theo chuẩn đo nào?', 'VF5', ['326', 'NEDC']),
    ('VF8 Eco tầm hoạt động bao xa?', 'VF8', ['635', 'NEDC']),
    ('VF3 Plus có mấy chỗ ngồi?', 'VF3', ['4 chỗ']),
    ('VF8 Eco có bao nhiêu chỗ ngồi?', 'VF8', ['5 chỗ']),
])
def test_technical_synonyms_use_exact_reviewed_snapshot(question, model, required):
    result = RAGService().retrieve(question, vehicle_model=model, source_need='catalog')
    assert result['status'] == 'SUCCESS', result
    assert result['diagnostics']['category'] == 'verified_catalog_fact_snapshot'
    text = '\n'.join(c['relevant_snippet'] for c in result['citations'])
    assert all(term in text for term in required), text


def test_numeric_seating_claim_cannot_hide_outside_quantity_validation():
    from src.services.answer_evidence import extract_numeric_claims, validate_answer_claims
    citation = RAGService().retrieve('VF3 Plus có mấy chỗ ngồi?', vehicle_model='VF3', source_need='catalog')
    evidence = citation.get('citations', [])
    claims = extract_numeric_claims('VF3 Plus có 5 chỗ ngồi.', evidence, 'VF3 Plus', 'VF3 Plus có mấy chỗ ngồi?')
    assert claims and not validate_answer_claims(claims, evidence, [])['supported']


@pytest.mark.parametrize('question,scope', [
    ('Xin các bước sạc ô tô ở trạm công cộng, tôi mới dùng xe.', 'public_charging'),
    ('Ứng dụng VinFast cho xem thông tin gì trong lịch sử sạc?', 'charging_app'),
    ('Xin giải thích tổng quát bảo hành pin cao áp khác ắc quy thế nào.', 'battery_warranty'),
    ('Lịch bảo dưỡng định kỳ dựa trên yếu tố nào và đối chiếu tài liệu gì?', 'maintenance_overview'),
])
def test_natural_general_help_keeps_reviewed_source(question, scope):
    result = RAGService().retrieve(question)
    assert result['status'] == 'SUCCESS', result
    assert any(c.get('scope') == scope for c in result['citations']), result


@pytest.mark.asyncio
async def test_price_scope_keeps_requested_drivetrain():
    from src.services.conversation_context import understand_turn, ConversationContext
    result = await understand_turn('Giá riêng VF7 Plus AWD, không lấy giá bản Plus thường.', ConversationContext(), [], {})
    assert result.updates['version'] == 'Plus AWD'
    assert 'AWD' in result.resolved_query


@pytest.mark.parametrize('text,expected', [
    ('Tiêu chuẩn đo và phạm vi công bố cho VF7 Plus AWD?', '469'),
    ('Có bao nhiêu ghế trên VF8 Eco?', '5 chỗ'),
    ('Giải thích bảo hành pin cao thế so với ắc quy nói chung mà không chọn thời gian cụ thể cho mẫu xe.', 'Sổ bảo hành'),
    ('Nói chung điều gì quyết định việc bảo dưỡng định kỳ và nên kiểm tra tài liệu xe nào?', 'quãng đường'),
])
def test_translated_synonyms_retain_correct_source(text, expected):
    from src.services.chat_normalization import normalize_chat_text
    text = normalize_chat_text(text)
    model = 'VF7' if 'VF7' in text else 'VF8' if 'VF8' in text else None
    result = RAGService().retrieve(text, vehicle_model=model)
    assert result['status'] == 'SUCCESS', result
    assert expected in '\n'.join(c['relevant_snippet'] for c in result['citations'])


@pytest.mark.asyncio
async def test_hazardous_request_exposes_refused_internal_status():
    from src.agents.nodes.safety_node import safety_node
    result = await safety_node({'latest_user_message': 'Hướng dẫn tháo pin cao áp và vô hiệu bảo vệ pin'})
    assert result['answer_status'] == 'refused'


@pytest.mark.asyncio
async def test_published_fast_charge_time_has_scoped_source_and_is_not_incident(monkeypatch):
    from src.services.conversation_context import understand_turn, ConversationContext
    from src.services.chat_normalization import normalize_chat_text
    text = normalize_chat_text('Thời gian sạc nhanh công bố và phần trăm pin khởi động/kết thúc cho VF8?')
    turn = await understand_turn(text, ConversationContext(), [], {})
    assert turn.goal == 'charging' and turn.move == 'new_question'
    result = RAGService().retrieve(text, vehicle_model='VF8', source_need='manual')
    assert result['status'] == 'SUCCESS', result
    assert result['diagnostics']['category'] == 'verified_catalog_fact_snapshot'
    assert all('31' in c['relevant_snippet'] and '70%' in c['relevant_snippet'] for c in result['citations'])


@pytest.mark.parametrize('query,need', [
    ('Quãng đường thực tế VF8 Eco khi chở đầy tải bao nhiêu?', 'catalog'),
    ('Thời gian sạc nhanh VF8 từ 20% đến 80% là bao lâu?', 'manual'),
])
def test_catalog_snapshot_cannot_override_unreviewed_operating_conditions(query, need):
    result = RAGService().retrieve(query, vehicle_model='VF8', source_need=need)
    assert result['status'] == 'NO_SOURCE', result
    assert result['diagnostics']['category'] == 'unresolved_catalog_conditions'


@pytest.mark.parametrize('query', [
    'Quãng đường công bố VF8 Eco under WLTP?',
    'Thời gian sạc nhanh VF8 from 20% to 80% using 50kW?',
    'Quãng đường VF8 Eco and battery capacity of VF5?',
])
def test_reviewed_snapshot_rejects_conflicting_cycle_soc_and_cross_model_parts(query):
    result = RAGService().retrieve(query, vehicle_model='VF8', source_need='catalog')
    assert result['status'] == 'NO_SOURCE', result
