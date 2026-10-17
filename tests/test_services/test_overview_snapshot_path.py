import pytest
from src.services import knowledge_questions


@pytest.mark.asyncio
@pytest.mark.parametrize('model', ['VF3', 'VF5', 'VF6', 'VF7', 'VF8', 'VF9'])
@pytest.mark.parametrize('phrase', ['Tư vấn về {}', 'tu van {}', 'tôi muốn hỏi về {}', 'cho tôi thông tin {}'])
async def test_overview_snapshot_does_not_call_rag(monkeypatch, model, phrase):
    async def unexpected(*args, **kwargs):
        pytest.fail('A verified simple product overview must not consume a RAG/model attempt')
    monkeypatch.setattr(knowledge_questions, 'rag_node', unexpected)
    raw = phrase.format(model)
    result = await knowledge_questions.answer_sales_question(raw, model, 'snapshot-fixture',
        turn_understanding={'goal':'overview', 'original_text':raw, 'request_kind':'faq'})
    assert result['answer_path'] == 'snapshot'
    assert not result['is_no_source']
    assert 'Giá bán trên là giá niêm yết chưa phải là giá lăn bánh' in result['reply']
