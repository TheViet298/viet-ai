import json
import pytest

from scripts import process_chunks
from src.services.rag_service import RAGService, source_registry


def test_catalog_retains_description_and_separate_model_color_evidence(tmp_path, monkeypatch):
    path = tmp_path / 'cars.jsonl'
    path.write_text(json.dumps({'name': 'VF 8', 'url': 'https://vinfastauto.com/vn_vi/dat-coc-xe-vf8',
        'highlights': [{'title': 'Thiết kế cá nhân hoá', 'description': 'Infinity Blanc Jet Black Crimson Red Ivy Green'}]}), encoding='utf-8')
    monkeypatch.setattr(process_chunks, 'CARS_JSONL', str(path))
    chunks = process_chunks.process_cars_jsonl()
    features = next(c for c in chunks if c['section'] == 'Điểm nổi bật VF 8')
    assert 'Infinity Blanc' in features['content']
    colors = next(c for c in chunks if c.get('catalog_scope') == 'model_colors')
    assert 'Crimson Red' in colors['content']
    assert 'chưa xác nhận' in colors['content']


def test_model_color_source_can_answer_plus_without_claiming_trim_availability():
    meta = {**source_registry()['SRC-009'], 'source_id': 'SRC-009', 'applicable_models': 'VF8',
        'catalog_scope': 'model_colors'}
    doc = 'Màu sắc ngoại thất VinFast VF8: Infinity Blanc, Jet Black, Crimson Red, Ivy Green.\nThông tin chung mẫu xe, chưa xác nhận màu có sẵn cho từng phiên bản.'
    result = {'documents': [[doc]], 'metadatas': [[meta]], 'distances': [[0.2]], 'ids': [['colors']]}
    out = RAGService().filter_results(result, 'VF8', query='VF8 Plus có những màu gì?')
    assert out['status'] == 'SUCCESS'
    assert 'Infinity Blanc' in out['citations'][0]['relevant_snippet']
    # A color passage must not become evidence for version-specific specs.
    assert RAGService().filter_results(result, 'VF8', query='Dung lượng pin VF8 Plus?')['status'] == 'NO_SOURCE'
    assert RAGService().filter_results(result, 'VF8', query='VF8 Plus có những màu nội thất gì?')['status'] == 'NO_SOURCE'


@pytest.mark.asyncio
async def test_verified_color_snapshot_preserves_names_and_scope_without_generation(monkeypatch):
    from src.agents.nodes import rag_node as node
    from src.config import get_settings
    snippet = 'Màu sắc ngoại thất VinFast VF8: Infinity Blanc Jet Black Crimson Red Ivy Green.\nThông tin chung mẫu xe, chưa xác nhận màu có sẵn cho từng phiên bản.'
    citation = {**source_registry()['SRC-009'], 'source_id': 'SRC-009', 'applicable_models': ['VF8'],
                'catalog_scope': 'model_colors', 'relevant_snippet': snippet, 'distance': 0.2}

    async def search(*args, **kwargs):
        return {'status': 'SUCCESS', 'citations': [citation], 'diagnostics': {}}

    async def unexpected_generation(*args, **kwargs):
        raise AssertionError('Verified color snapshot must retain exact catalog names')

    monkeypatch.setattr(get_settings(), 'agent_llm_enabled', True)
    monkeypatch.setattr(node, 'vinfast_manual_search', search)
    monkeypatch.setattr(node, 'structured_call', unexpected_generation)
    out = await node.rag_node({'latest_user_message': 'VF8 Plus có những màu gì?', 'vehicle_model': 'VF8',
                              'confidence_score': 0.9, 'turn_understanding': {'goal': 'appearance'}})
    assert out['retrieval_status'] == 'SUCCESS'
    assert snippet in out['response']
