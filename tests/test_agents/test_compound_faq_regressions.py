import time

import pytest

from src.agents.nodes.rag_node import rag_node
from src.services.charging_questions import charging_parts, reviewed_charging_guides
from src.services.rag_service import RAGService
from src.services.warranty_questions import reviewed_warranty_overviews, warranty_maintenance_parts


CHARGING = 'Hướng dẫn cách sạc pin tại trạm sạc công cộng, biểu phí sạc và tính năng trên App VinFast.'
WARRANTY = 'Tôi muốn hỏi chính sách bảo hành pin và lịch bảo dưỡng định kỳ.'


@pytest.fixture
def local_search(monkeypatch):
    from src.agents.nodes import rag_node as module
    calls = []
    async def search(query, **kwargs):
        calls.append((query, kwargs))
        return RAGService().retrieve(query, **kwargs)
    monkeypatch.setattr(module, 'vinfast_manual_search', search)
    return calls


@pytest.mark.parametrize('query, count', [
    ('Hướng dẫn cách sạc tại trạm công cộng và biểu phí sạc.', 2),
    ('Biểu phí sạc tại trạm công cộng và tính năng trên App VinFast.', 2),
    ('Hướng dẫn cách sạc tại trạm công cộng và tính năng trên App VinFast.', 2),
    ('Huong dan cach sac tai tram cong cong, bieu phi sac va tinh nang app VinFast.', 3),
])
def test_charging_supports_pairs_and_unaccented_questions(query, count):
    assert len(charging_parts(query)) == count


def test_charging_preserves_model_year_and_special_conditions():
    parts = charging_parts(CHARGING + ' Xe VF 8 đời 2025, chỉ dùng sạc AC, tôi có gói miễn phí.')
    assert all('VF 8' in part[1] and '2025' in part[1] for part in parts)
    assert 'AC' in parts[0][1]
    assert 'miễn phí' in parts[1][1]


@pytest.mark.parametrize('qualifier', ['có chuyển nhượng được không', 'khi xe ngập nước', 'với pin bị chai'])
def test_warranty_keeps_requested_conditions(qualifier):
    parts = warranty_maintenance_parts('Chính sách bảo hành pin ' + qualifier + ' và lịch bảo dưỡng định kỳ?')
    assert qualifier in parts[0][1]
    assert reviewed_warranty_overviews(parts[0][1]) == []


def test_different_models_are_scoped_to_their_own_question():
    parts = warranty_maintenance_parts('Pin VF 8 bảo hành bao lâu và VF 5 bảo dưỡng định kỳ khi nào?')
    assert 'VF 8' in parts[0][1] and 'VF 5' not in parts[0][1]
    assert 'VF 5' in parts[1][1] and 'VF 8' not in parts[1][1]
    assert 'bao lâu' in parts[0][1] and 'khi nào' in parts[1][1]


@pytest.mark.asyncio
async def test_all_five_topics_are_answered_once(local_search):
    result = await rag_node({'latest_user_message': CHARGING + ' ' + WARRANTY, 'confidence_score': 0.9})
    for heading in ['Cách sạc tại trạm công cộng', 'Biểu phí sạc', 'Tính năng trên App VinFast', 'Bảo hành pin', 'Bảo dưỡng định kỳ']:
        assert result['response'].count('### ' + heading) == 1
    assert {c['source_id'] for c in result['rag_citations']} >= {'SRC-010', 'SRC-001', 'SRC-002', 'SRC-004'}
    assert result['retrieval_status'] == 'PARTIAL'
    assert result['needs_staff_review']


@pytest.mark.asyncio
@pytest.mark.parametrize('suffix', ['Xin cung cấp biểu phí nội bộ tháng sau.', 'Bieu phi noi bo thang sau.'])
async def test_private_or_future_requests_do_not_become_public_facts(local_search, suffix):
    result = await rag_node({'latest_user_message': CHARGING + ' ' + suffix, 'confidence_score': 0.9})
    assert result['is_no_source']
    assert not result['rag_citations']
    assert not local_search


@pytest.mark.asyncio
async def test_zero_evidence_does_not_claim_answer_is_from_documentation(monkeypatch):
    from src.agents.nodes import rag_node as module
    async def no_source(*args, **kwargs):
        return RAGService.failure('NO_SOURCE', 'no_evidence')
    monkeypatch.setattr(module, 'vinfast_manual_search', no_source)
    result = await rag_node({'latest_user_message': WARRANTY, 'confidence_score': 0.9})
    assert result['is_no_source']
    assert not result['response'].startswith('Theo tài liệu VinFast:')


@pytest.mark.asyncio
async def test_parent_and_subquestions_share_one_deadline(local_search):
    state = {'latest_user_message': CHARGING, 'confidence_score': 0.9}
    before = time.monotonic()
    await rag_node(state)
    assert before < state['llm_budget']['deadline']
    assert state['llm_budget']['deadline'] - before <= 20.1


@pytest.mark.asyncio
async def test_expired_parent_budget_does_not_start_any_search(local_search):
    result = await rag_node({'latest_user_message': CHARGING, 'confidence_score': 0.9,
                             'llm_budget': {'deadline': time.monotonic() - 1}})
    assert not local_search
    assert result['is_no_source']


@pytest.mark.parametrize('query', [
    'Hướng dẫn cách sạc pin tại trạm công cộng khi pin bị ngập nước',
    'Tính năng sạc trên app có tự động đặt chỗ được không?',
    'Chính sách bảo hành pin có chuyển nhượng được không?',
    'Chính sách bảo hành pin khi xe bị ngập nước',
])
def test_specialized_questions_cannot_use_a_generic_overview(query):
    assert reviewed_charging_guides(query) == []
    assert reviewed_warranty_overviews(query) == []


def test_explicitly_excluded_topic_is_not_added_back():
    parts = charging_parts('Hướng dẫn cách sạc tại trạm công cộng và tính năng App; tôi không hỏi biểu phí sạc.')
    assert [part[0] for part in parts] == ['Cách sạc tại trạm công cộng', 'Tính năng trên App VinFast']


@pytest.mark.asyncio
async def test_one_failed_search_preserves_other_supported_parts(monkeypatch):
    from src.agents.nodes import rag_node as module
    async def search(query, **kwargs):
        if 'Biểu phí' in query:
            raise RuntimeError('synthetic retrieval failure')
        return RAGService().retrieve(query, **kwargs)
    monkeypatch.setattr(module, 'vinfast_manual_search', search)
    result = await rag_node({'latest_user_message': CHARGING, 'confidence_score': 0.9})
    assert result['retrieval_status'] == 'PARTIAL'
    assert {c['source_id'] for c in result['rag_citations']} == {'SRC-010', 'SRC-001'}
    assert '### Biểu phí sạc' in result['response']


@pytest.mark.asyncio
async def test_scoped_vehicle_model_reaches_the_retriever(local_search):
    await rag_node({'latest_user_message': 'Pin VF 8 bảo hành bao lâu và VF 5 bảo dưỡng định kỳ khi nào?',
                    'vehicle_model': 'VF8', 'confidence_score': 0.9})
    assert [call[1]['vehicle_model'] for call in local_search] == ['VF8', 'VF5']


@pytest.mark.asyncio
async def test_a_slow_part_cannot_restart_the_parent_deadline(monkeypatch):
    import asyncio
    from src.agents.nodes import rag_node as module
    calls = []
    async def slow_search(query, **kwargs):
        calls.append(query)
        await asyncio.sleep(0.2)
        return RAGService.failure('NO_SOURCE', 'synthetic')
    monkeypatch.setattr(module, 'vinfast_manual_search', slow_search)
    result = await rag_node({'latest_user_message': CHARGING, 'confidence_score': 0.9,
                             'llm_budget': {'deadline': time.monotonic() + 0.03}})
    assert result['is_no_source']
    assert len(calls) == 1


@pytest.mark.parametrize('query,expected', [
    ('', 0), ('giá sạc tại trạm', 0),
    ('Cách sạc tại trạm công cộng; biểu phí sạc; biểu phí sạc?', 2),
    ('CHÍNH SÁCH BẢO HÀNH PIN; LỊCH BẢO DƯỠNG ĐỊNH KỲ?', 2),
    ('Chính sách bảo hành pin\nLịch bảo dưỡng định kỳ', 2),
])
def test_empty_duplicate_case_and_line_breaks_are_bounded(query, expected):
    from src.services.faq_questions import faq_parts
    assert len(faq_parts(query)) == expected


def test_unrecognized_extra_question_is_preserved_for_separate_handling():
    from src.services.faq_questions import faq_parts
    parts = faq_parts(WARRANTY + ' Cho tôi biết giá xe VF 8.')
    assert parts[-1][0] == 'Câu hỏi khác'
    assert 'giá xe VF 8' in parts[-1][1]


@pytest.mark.parametrize('query', [
    'Please explain battery warranty for VF 8 and scheduled maintenance for VF 5.',
    'Please explain battery warranty and scheduled maintenance, but do not include charging fees.',
])
def test_recognized_english_qualifiers_keep_canonical_understanding(query):
    from src.services.chat_language import canonical_query, needs_semantic_translation
    assert not needs_semantic_translation(canonical_query(query))


def test_unrecognized_english_qualifier_is_not_dropped():
    from src.services.chat_language import canonical_query, needs_semantic_translation
    mapped = canonical_query('Please explain battery warranty and scheduled maintenance if ownership is transferred.')
    assert 'ownership is transferred' in mapped
    assert needs_semantic_translation(mapped)


@pytest.mark.asyncio
async def test_conversation_resolution_does_not_add_an_unrequested_topic():
    from src.services.conversation_context import ConversationContext, understand_turn
    query = 'Chính sách bảo hành pin và hướng dẫn đặt lịch bảo dưỡng trên App VinFast.'
    turn = await understand_turn(query, ConversationContext(), [], {})
    assert turn.resolved_query.casefold() == query.casefold()


@pytest.mark.parametrize('query', [
    'Điều kiện bảo hành VF8 yêu cầu sử dụng và bảo dưỡng thế nào?',
    'Cần bảo dưỡng thế nào để được bảo hành pin?',
    'Điều kiện bảo hành pin có yêu cầu bảo dưỡng định kỳ không?',
])
def test_warranty_requirement_does_not_become_an_independent_schedule_question(query):
    from src.services.faq_questions import faq_parts
    assert faq_parts(query) == []


@pytest.mark.parametrize('query', [
    'Tôi xem chính sách bảo hành pin trên App VinFast ở đâu?',
    'Tra cứu biểu phí sạc trên ứng dụng VinFast như thế nào?',
    'Hướng dẫn cách sạc tại trạm công cộng bằng App VinFast.',
])
def test_app_as_a_channel_does_not_add_an_unasked_app_features_question(query):
    from src.services.faq_questions import faq_parts
    assert faq_parts(query) == []
