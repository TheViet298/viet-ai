import pytest
from src.services.knowledge_questions import answer_sales_question
from src.services.vehicle_catalog import select_vehicle_cards

@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['Tư vấn xe', 'tu van xe', 'Tôi muốn tư vấn mua xe', 'Giới thiệu các dòng xe VinFast', 'Tư vấn chung về xe', 'Tư vấn cho tôi về xe', 'Tôi muốn tìm hiểu các mẫu xe VinFast'])
async def test_general_advice_invites_model_selection_without_cards(text):
    result = await answer_sales_question(text, None, 'general-advice', turn_understanding={'goal': 'overview', 'original_text': text})
    assert result['suggested_replies'] == ['Tư vấn xe VF3', 'Tư vấn xe VF8']
    assert 'mẫu xe nào' in result['reply']
    assert not select_vehicle_cards(text)

@pytest.mark.parametrize('text,model', [('Tư vấn xe VF3','VF3'), ('Tư vấn xe VF8','VF8')])
def test_suggested_model_keeps_cards(text, model):
    assert {c.model for c in select_vehicle_cards(text)} == {model}
