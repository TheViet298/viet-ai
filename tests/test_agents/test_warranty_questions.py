import pytest

from src.agents.nodes.rag_node import rag_node
from src.services.rag_service import RAGService, valid_citation


QUESTION = 'Tôi muốn hỏi chính sách bảo hành pin và lịch bảo dưỡng định kỳ.'


@pytest.mark.asyncio
async def test_warranty_button_answers_both_topics_and_asks_for_vehicle(monkeypatch):
    from src.agents.nodes import rag_node as module
    async def search(query, **kwargs):
        return RAGService().retrieve(query, **kwargs)
    monkeypatch.setattr(module, 'vinfast_manual_search', search)
    result = await rag_node({'latest_user_message': QUESTION, 'confidence_score': 0.9})
    assert not result['is_no_source']
    assert '### Bảo hành pin' in result['response']
    assert '### Bảo dưỡng định kỳ' in result['response']
    assert 'dòng xe' in result['response']
    assert 'mức phí' not in result['response']
    assert {citation['source_id'] for citation in result['rag_citations']} == {'SRC-002', 'SRC-004'}
    assert all(valid_citation(c) for c in result['rag_citations'])


def test_warranty_split_preserves_vehicle_year_and_usage():
    from src.services.warranty_questions import warranty_maintenance_parts
    parts = warranty_maintenance_parts(QUESTION + ' Xe VF 8 đời 2025, chạy dịch vụ.')
    assert len(parts) == 2
    assert all('VF 8' in part[1] and '2025' in part[1] and 'dịch vụ' in part[1] for part in parts)
    assert warranty_maintenance_parts('Pin lỗi và quá hạn bảo dưỡng, tôi muốn khiếu nại bảo hành') == []
    personal = warranty_maintenance_parts(QUESTION + ' Xe VF 8 đời 2025, 15.000 km, không chạy dịch vụ.')
    assert all('không chạy dịch vụ' in part[1] and '15.000 km' in part[1] for part in personal)


def test_general_maintenance_overview_has_no_universal_interval():
    result = RAGService().retrieve('Lịch bảo dưỡng định kỳ VinFast')
    assert result['status'] == 'SUCCESS'
    assert valid_citation(result['citations'][0])
    assert 'quãng đường' in result['citations'][0]['relevant_snippet']
    import re
    assert not re.search(r'\d[\d.,]*\s*(?:km|tháng|năm)', result['citations'][0]['relevant_snippet'])


@pytest.mark.parametrize('query,model', [
    ('Lịch bảo dưỡng định kỳ VF 8', None),
    ('Lịch bảo dưỡng định kỳ VinFast', 'VF8'),
    ('Pin VF 8 bảo hành bao lâu?', None),
    ('Chính sách bảo hành pin VinFast cho xe chạy dịch vụ', None),
    ('Lịch bảo dưỡng của VF 3 và VF 8 có khác nhau không?', None),
])
def test_model_specific_question_does_not_use_general_overview(query, model):
    from src.services.warranty_questions import reviewed_warranty_overviews
    assert reviewed_warranty_overviews(query, model) == []
