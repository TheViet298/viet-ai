import json
from pathlib import Path
import pytest
from src.services.rag_service import RAGService
CASES=json.loads((Path(__file__).resolve().parents[2]/'eval/datasets/answer_gap_14_v1.json').read_text(encoding='utf-8'))

@pytest.mark.asyncio
@pytest.mark.parametrize('case',CASES,ids=lambda r:r['id'])
async def test_original_fourteen_questions_have_scoped_content(case,monkeypatch):
    from src.agents.nodes import rag_node as module
    from src.services.conversation_context import understand_turn,ConversationContext
    async def search(query,**kwargs):return RAGService().retrieve(query,**kwargs)
    monkeypatch.setattr(module,'vinfast_manual_search',search)
    turn=await understand_turn(case['question'],ConversationContext(),[],{})
    result=await module.rag_node({'latest_user_message':case['question'],'vehicle_model':turn.subject,
        'confidence_score':.9,'turn_understanding':turn.model_dump()})
    assert result['answer_status']==case['expected_status'],result
    assert all(term.casefold()in result['response'].casefold()for term in case['required']),result
    if case['expected_status']not in {'needs_clarification'}:assert result['rag_citations']



def test_model_identifier_is_not_a_warranty_duration():
    from src.services.answer_evidence import extract_numeric_claims
    assert not extract_numeric_claims('Sổ tay VF8 năm 2026 mô tả ADAS.', [], 'VF8', 'ADAS VF8 gồm gì?')


@pytest.mark.parametrize('query,model', [
    ('Bảo hành VF8 The All New bao lâu?', 'VF8'),
    ('Bảo hành VF8 đời 2024 bao lâu?', 'VF8'),
    ('Dung lượng pin VF3 Plus là bao nhiêu?', 'VF3'),
    ('Dung lượng pin danh định VF3?', 'VF3'),
    ('VF7 Plus màu nào còn hàng hôm nay?', 'VF7'),
    ('Cách kích hoạt ADAS VF8?', 'VF8'),
    ('ADAS VF8 đời 2025 gồm gì?', 'VF8'),
    ('Dung lượng pin VF3 và VF5?', 'VF3'),
])
def test_gap_records_do_not_cross_unverified_scope(query, model):
    from src.services.reviewed_gap_answers import reviewed_gap_answers
    assert not reviewed_gap_answers(query, model)


def test_warranty_exclusion_note_is_not_a_different_vehicle_policy():
    from src.services.answer_evidence import answer_section
    assert not answer_section('Thời hạn bảo hành VF8?', 'VF8 The All New bảo hành xe 7 năm hoặc 160.000 km.')
    source = 'VF8 bảo hành xe 10 năm hoặc 200.000 km.\nKhông áp dụng hàng này cho VF8 The All New.'
    assert answer_section('Thời hạn bảo hành VF8?', source) == source


@pytest.mark.parametrize('question', ['Bảo hành VF8 tại Mỹ bao lâu?', 'Bảo hành VF8 ở Canada?',
                                      'VF8 warranty in the US?', 'Bảo hành VF8 tại châu Âu?'])
def test_vn_gap_policy_does_not_assert_foreign_market(question):
    result = RAGService().retrieve(question, vehicle_model='VF8', source_need='policy')
    assert result['status'] == 'NO_SOURCE', result


def test_taxi_policy_uses_commercial_terms():
    result = RAGService().retrieve('VF8 chạy taxi được bảo hành bao lâu?', vehicle_model='VF8')
    assert result['status'] == 'SUCCESS'
    assert result['citations'][0]['key'] == 'commercial_warranty'


@pytest.mark.asyncio
@pytest.mark.parametrize('question,required', [
    ('Dung lượng pin VF3 và tầm hoạt động là bao nhiêu?', ['18,64', 'phiên bản']),
    ('Bảo hành VF8 và dung lượng pin là bao nhiêu?', ['10 năm', 'phiên bản']),
])
async def test_new_gap_answer_keeps_both_requested_facts(question, required, monkeypatch):
    from src.agents.nodes import rag_node as module
    async def search(query, **kwargs): return RAGService().retrieve(query, **kwargs)
    monkeypatch.setattr(module, 'vinfast_manual_search', search)
    result = await module.rag_node({'latest_user_message': question, 'vehicle_model': 'VF3' if 'VF3' in question else 'VF8', 'confidence_score': .9})
    assert result['answer_status'] == 'partial', result
    assert all(term in result['response'] for term in required), result



def test_english_possessive_is_not_the_us_market():
    from src.services.reviewed_gap_answers import foreign_market_request
    assert not foreign_market_request('What is the battery capacity in my VF3?')


def test_denied_taxi_use_is_not_positive_commercial_evidence():
    from src.services.reviewed_gap_answers import reviewed_gap_answers
    assert not reviewed_gap_answers('VF8 không chạy taxi bảo hành bao lâu?', 'VF8')


@pytest.mark.asyncio
async def test_foreign_market_scope_survives_compound_decomposition(monkeypatch):
    from src.agents.nodes import rag_node as module
    async def search(query, **kwargs): return RAGService().retrieve(query, **kwargs)
    monkeypatch.setattr(module, 'vinfast_manual_search', search)
    result = await module.rag_node({'latest_user_message': 'Bảo hành VF8 và dung lượng pin tại Mỹ?',
                                    'vehicle_model': 'VF8', 'confidence_score': .9})
    assert result['answer_status'] == 'needs_data'
    assert not result['rag_citations']
    assert '10 năm' not in result['response']


def test_english_adas_activation_is_not_a_complete_feature_overview():
    from src.services.chat_language import evidence_intent_query
    query = evidence_intent_query('What ADAS features does the VF8 have in 2026, and how do I activate them?')
    result = RAGService().retrieve(query, vehicle_model='VF8')
    assert result['status'] == 'NO_SOURCE', result
