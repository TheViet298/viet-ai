import pytest

from src.services.charging_questions import charging_parts, is_public_charging_procedure
from src.services.answer_evidence import answer_section


QUESTION = 'Hướng dẫn cách sạc pin tại trạm sạc công cộng, biểu phí sạc và tính năng trên App VinFast.'


def test_compound_charging_question_keeps_three_independent_requests():
    parts = charging_parts(QUESTION)
    assert [part[0] for part in parts] == ['Cách sạc tại trạm công cộng', 'Biểu phí sạc', 'Tính năng trên App VinFast']
    assert 'biểu phí' not in parts[0][1].lower()
    assert charging_parts('Xe báo lỗi sạc, tôi cần hỗ trợ trên app') == []
    assert charging_parts('Giá sạc tại trạm công cộng') == []


def test_charging_hardware_or_battery_damage_is_not_a_charging_procedure():
    question = 'Hướng dẫn cách sạc pin tại trạm sạc công cộng'
    assert is_public_charging_procedure(question)
    assert not answer_section(question, 'Trụ sạc công cộng\nKiểm tra chi phí đền bù nếu pin hỏng do lỗi khách hàng.')
    assert answer_section(question, 'Hướng dẫn sạc tại trạm công cộng\nBước 1: Đỗ xe.\nBước 2: Cắm súng sạc vào cổng sạc.\nBước 3: Kiểm tra trạng thái sạc.')


def test_reviewed_charging_procedure_is_available_without_a_vector_index():
    from src.services.rag_service import RAGService, valid_citation
    result = RAGService().retrieve('Hướng dẫn cách sạc pin tại trạm sạc công cộng')
    assert result['status'] == 'SUCCESS'
    assert valid_citation(result['citations'][0])
    assert 'Bước 1' in result['citations'][0]['relevant_snippet']


@pytest.mark.asyncio
async def test_compound_answer_preserves_supported_part_when_another_has_no_source(monkeypatch):
    from src.agents.nodes import rag_node as module
    async def search(query, **kwargs):
        from src.services.rag_service import RAGService
        return RAGService().retrieve(query)
    monkeypatch.setattr(module, 'vinfast_manual_search', search)
    result = await module.rag_node({'latest_user_message': QUESTION, 'confidence_score': 0.9})
    assert not result['is_no_source']
    assert result['rag_citations']
    assert 'Cách sạc tại trạm công cộng' in result['response']
    assert 'Biểu phí sạc' in result['response']
    assert 'Tính năng trên App VinFast' in result['response']
