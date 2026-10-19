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
    ('VF8 bảo dưỡng định kỳ lần đầu ở bao nhiêu km?', 'VF8'),
    ('VF3 đời 2025 bảo dưỡng định kỳ khi nào?', 'VF3'),
    ('VF3 chạy dịch vụ thương mại bảo dưỡng định kỳ khi nào?', 'VF3'),
    ('VF3 cần thay dung dịch làm mát định kỳ khi nào?', 'VF3'),
])
def test_schedule_does_not_cross_unknown_scope(query, model):
    from src.services.reviewed_knowledge import reviewed_maintenance_schedules
    assert not reviewed_maintenance_schedules(query, model)


def test_vf5_model_colors_are_not_trim_year_or_stock_assertions():
    from src.services.reviewed_knowledge import reviewed_model_colors
    rows = reviewed_model_colors('VF5 có những màu gì?', 'VF5')
    assert rows and 'Urban Mint' in rows[0]['relevant_snippet']
    assert 'tồn kho' in rows[0]['relevant_snippet']
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
    ('VF5 có những màu gì?', 'VF5', ['Urban Mint', 'tồn kho']),
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
