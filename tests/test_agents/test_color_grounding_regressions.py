import json
from pathlib import Path

import pytest

from src.services.rag_service import RAGService, source_registry


def captured_vf7_specs():
    path = Path(__file__).resolve().parents[1] / 'fixtures/rag_color_vf7_v7.json'
    row = json.loads(path.read_text(encoding='utf-8'))
    return row['query'], [{**citation, 'distance': .2} for citation in row['citations']]


def test_color_retrieval_rejects_captured_specs_with_no_color_entities():
    query, citations = captured_vf7_specs()
    rows = {'documents': [[c['relevant_snippet'] for c in citations]],
            'metadatas': [[{**c, 'applicable_models': 'VF7'} for c in citations]],
            'distances': [[.2] * len(citations)], 'ids': [[f'specs-{i}' for i in range(len(citations))]]}
    result = RAGService().filter_results(rows, 'VF7', query)
    assert result['status'] == 'NO_SOURCE'
    assert result['citations'] == []


@pytest.mark.asyncio
@pytest.mark.parametrize('goal', ['appearance', None])
async def test_color_generation_cannot_invent_entities_from_specs_with_empty_claims(monkeypatch, goal):
    from src.agents.nodes import rag_node as node
    query, citations = captured_vf7_specs()

    async def search(*args, **kwargs):
        return {'status': 'SUCCESS', 'citations': citations, 'diagnostics': {'category': 'success'}}

    async def generate(*args, **kwargs):
        return node.GroundedAnswer(answer='VF7 Plus có các màu Black, White, Red, Blue, Silver.',
                                   source_ids=['SRC-009'], supported=True, claims=[])

    monkeypatch.setattr(node, 'vinfast_manual_search', search)
    monkeypatch.setattr(node, 'structured_call', generate)
    result = await node.rag_node({'latest_user_message': query, 'vehicle_model': 'VF7', 'confidence_score': .9,
                                  'turn_understanding': {'goal': goal}})
    assert result['is_no_source']
    assert result['rag_citations'] == []
    assert result['retrieval_diagnostics']['category'] == 'missing_answer_evidence'
    assert 'Silver' not in result['response']


@pytest.mark.asyncio
async def test_model_colors_tag_cannot_certify_a_passage_without_color_names(monkeypatch):
    from src.agents.nodes import rag_node as node
    citation = {**source_registry()['SRC-009'], 'source_id': 'SRC-009', 'applicable_models': ['VF8'],
                'catalog_scope': 'model_colors', 'relevant_snippet': 'VF8 Plus có công suất 300 kW.', 'distance': .2}

    async def search(*args, **kwargs):
        return {'status': 'SUCCESS', 'citations': [citation]}

    monkeypatch.setattr(node, 'vinfast_manual_search', search)
    result = await node.rag_node({'latest_user_message': 'VF8 Plus có màu gì?', 'vehicle_model': 'VF8',
                                  'confidence_score': .9, 'turn_understanding': {'goal': 'appearance'}})
    assert result['is_no_source']
    assert result['rag_citations'] == []


@pytest.mark.asyncio
async def test_exact_color_passage_uses_only_source_names_even_without_scope_tag(monkeypatch):
    from src.agents.nodes import rag_node as node
    snippet = ('Màu sắc ngoại thất VF8: Infinity Blanc; Jet Black; Crimson Red; Ivy Green.\n'
               'Thông tin chung mẫu xe, chưa xác nhận màu có sẵn cho từng phiên bản.')
    citation = {**source_registry()['SRC-009'], 'source_id': 'SRC-009', 'applicable_models': ['VF8'],
                'relevant_snippet': snippet, 'distance': .2}

    async def search(*args, **kwargs):
        return {'status': 'SUCCESS', 'citations': [citation]}

    async def generate(*args, **kwargs):
        return node.GroundedAnswer(answer='VF8 có màu Silver.', source_ids=['SRC-009'], supported=True, claims=[])

    monkeypatch.setattr(node, 'vinfast_manual_search', search)
    monkeypatch.setattr(node, 'structured_call', generate)
    result = await node.rag_node({'latest_user_message': 'VF8 có màu gì?', 'vehicle_model': 'VF8',
                                  'confidence_score': .9, 'turn_understanding': {'goal': 'appearance'}})
    assert not result['is_no_source']
    assert snippet in result['response']
    assert 'Silver' not in result['response']
