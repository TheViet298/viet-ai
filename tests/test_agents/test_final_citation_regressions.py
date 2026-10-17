import importlib
import pytest


@pytest.mark.asyncio
async def test_numeric_evidence_must_be_in_selected_displayed_citations(monkeypatch):
    node = importlib.import_module('src.agents.nodes.rag_node')
    citations = [{'source_id': key, 'relevant_snippet': f'VF8 quãng đường một lần sạc {value} km.',
                  'title': 'Thông số VF8', 'url': 'https://vinfastauto.com', 'distance': .2}
                 for key, value in [('A', 400), ('B', 500)]]
    async def search(*args, **kwargs):
        return {'status': 'SUCCESS', 'citations': citations}
    async def generate(*args, **kwargs):
        return node.GroundedAnswer(answer='VF8 quãng đường một lần sạc 500 km.', source_ids=['A'], supported=True)
    monkeypatch.setattr(node, 'vinfast_manual_search', search)
    monkeypatch.setattr(node, 'structured_call', generate)
    monkeypatch.setattr(node, 'valid_citation', lambda *args: True)
    monkeypatch.setattr(node, 'select_supported_evidence', lambda query, values: values)
    result = await node.rag_node({'latest_user_message': 'Quãng đường VF8?', 'vehicle_model': 'VF8', 'confidence_score': .9})
    assert result['is_no_source']
    assert result['rag_citations'] == []


@pytest.mark.asyncio
async def test_explicitly_unsupported_nonnumeric_answer_is_not_published(monkeypatch):
    node = importlib.import_module('src.agents.nodes.rag_node')
    citations = [{'source_id':'s', 'relevant_snippet':'VF8 có trang bị hỗ trợ người lái.', 'distance':.2}]
    async def search(*args, **kwargs):
        return {'status':'SUCCESS', 'citations':citations}
    async def generate(*args, **kwargs):
        return node.GroundedAnswer(answer='VF8 hỗ trợ tự lái hoàn toàn trên mọi tuyến đường.', source_ids=['s'], supported=False)
    monkeypatch.setattr(node, 'vinfast_manual_search', search)
    monkeypatch.setattr(node, 'structured_call', generate)
    monkeypatch.setattr(node, 'valid_citation', lambda *args: True)
    monkeypatch.setattr(node, 'select_supported_evidence', lambda query, values: values)
    result = await node.rag_node({'latest_user_message':'VF8 hỗ trợ lái thế nào?', 'confidence_score':.9})
    assert result['is_no_source']
    assert result['needs_staff_review']
