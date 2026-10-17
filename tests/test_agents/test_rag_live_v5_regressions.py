import pytest

from src.services.answer_evidence import AnswerClaim, extract_numeric_claims, validate_answer_claims
from src.services.rag_service import RAGService, requested_source_type, source_registry


TARIFF = ('Đơn giá sạc: 3.858 VNĐ/kWh (áp dụng từ ngày 19/03/2024).\n'
          'Phí sử dụng dịch vụ trạm sạc bổ sung sau khi hoàn thành phiên sạc:\n'
          'Miễn phí từ phút thứ 1 đến phút thứ 10\n'
          '1.000 đồng/phút từ phút thứ 11 đến phút thứ 60\n'
          '2.000 đồng/phút từ phút thứ 61 đến phút thứ 120\n'
          '4.000 đồng/phút từ phút thứ 121 trở đi')


def tariff_source():
    return {'source_id': 'SRC-006', 'source_type': 'official_service',
            'applicable_models': ['ALL'], 'relevant_snippet': TARIFF}


def test_tariff_excerpt_removes_preceding_battery_repair_paragraph():
    from src.services.answer_evidence import answer_section
    intro = 'VinFast cung cấp đơn giá sạc ô tô điện tại các trạm sạc công cộng như sau:\n'
    text = '2. Nếu pin hỏng do lỗi Khách hàng thì Khách hàng phải đền bù chi phí sửa chữa.\n' + intro + TARIFF
    excerpt = answer_section('Biểu phí sạc VF8?', text)
    assert 'pin hỏng' not in excerpt
    assert TARIFF in excerpt


@pytest.mark.asyncio
async def test_tariff_answer_retains_complete_source_conditions_without_regeneration(monkeypatch):
    from src.agents.nodes import rag_node as node
    citation = {**source_registry()['SRC-006'], **tariff_source(), 'distance': .2}
    async def search(*args, **kwargs):
        return {'status': 'SUCCESS', 'citations': [citation]}
    async def generate(*args, **kwargs):
        pytest.fail('A reviewed tariff should retain its verbatim conditions')
    monkeypatch.setattr(node, 'vinfast_manual_search', search)
    monkeypatch.setattr(node, 'structured_call', generate)
    result = await node.rag_node({'latest_user_message': 'Biểu phí sạc VF8?', 'vehicle_model': 'VF8', 'confidence_score': .9})
    assert not result['is_no_source']
    assert TARIFF in result['response']
    assert result['rag_citations']


def test_effective_date_is_not_a_vehicle_starting_price_qualifier():
    claim = AnswerClaim(claim_key='price', value='3.858', unit='VNĐ/kWh', subject='Giá sạc VF7',
                        conditions=['Áp dụng từ ngày 19/03/2024'], source_ids=['SRC-006'])
    assert validate_answer_claims([claim], [tariff_source()], [])['supported']


def test_currency_unit_determines_tariff_claim_type_even_if_model_mislabels_it():
    claim = AnswerClaim(claim_key='charging_time', value='1000', unit='VNĐ/phút', subject='Phí dịch vụ trạm sạc',
                        conditions=['từ phút thứ 11 đến phút thứ 60'], source_ids=['SRC-006'])
    assert validate_answer_claims([claim], [tariff_source()], [])['supported']


def test_explicit_free_tariff_can_support_zero_in_same_tier():
    claim = AnswerClaim(claim_key='price', value='0', unit='VNĐ/phút', subject='Phí dịch vụ trạm sạc',
                        conditions=['từ phút thứ 1 đến phút thứ 10'], source_ids=['SRC-006'])
    assert validate_answer_claims([claim], [tariff_source()], [])['supported']
    wrong = claim.model_copy(update={'conditions': ['từ phút thứ 11 đến phút thứ 60']})
    assert not validate_answer_claims([wrong], [tariff_source()], [])['supported']


def test_negated_free_tariff_never_certifies_zero():
    source = {**tariff_source(), 'relevant_snippet': 'Không miễn phí từ phút thứ 1 đến phút thứ 10.'}
    claim = AnswerClaim(claim_key='price', value='0', unit='VNĐ/phút', subject='',
                        conditions=['từ phút thứ 1 đến phút thứ 10'], source_ids=['SRC-006'])
    assert not validate_answer_claims([claim], [source], [])['supported']


@pytest.mark.parametrize('answer', [
    'Miễn phí từ phút thứ1 trở đi.',
    'Miễn phí từ phút thứ 1 đến phút thứ 11.',
    'Miễn phí từ phút thứ 11 đến phút thứ 60.',
    'Miễn phí không giới hạn.',
    'Miễn phí.',
])
def test_answer_side_free_tariff_cannot_omit_or_expand_source_tier(answer):
    claims = extract_numeric_claims(answer, [tariff_source()], 'VF8')
    assert claims, 'A free-price assertion must not bypass validation through an empty claim list'
    assert not validate_answer_claims(claims, [tariff_source()], [])['supported']


@pytest.mark.parametrize('answer', ['Miễn phí từ phút thứ 1 đến phút thứ 10.',
                                  'Miễn phí từ phút thứ1 đến phút thứ10.'])
def test_answer_side_free_tariff_is_zero_with_exact_stated_tier(answer):
    claims = extract_numeric_claims(answer, [tariff_source()], 'VF8')
    assert len(claims) == 1
    assert claims[0].value == '0'
    assert claims[0].unit == 'đồng/phút'
    assert claims[0].conditions == ['tu phut thu 1 den phut thu 10']
    assert validate_answer_claims(claims, [tariff_source()], [])['supported']


@pytest.mark.asyncio
@pytest.mark.parametrize('answer,refused', [('Miễn phí từ phút thứ1 trở đi.', True),
                                          ('Miễn phí từ phút thứ 1 đến phút thứ 11.', True),
                                          ('Miễn phí từ phút thứ 1 đến phút thứ 10.', False)])
async def test_generated_free_tariff_cannot_bypass_rag_with_empty_structured_claims(monkeypatch, answer, refused):
    from src.agents.nodes import rag_node as node
    citation = {**source_registry()['SRC-006'], **tariff_source(), 'distance': .2}

    async def search(*args, **kwargs):
        return {'status': 'SUCCESS', 'citations': [citation]}

    async def generate(*args, **kwargs):
        return node.GroundedAnswer(answer=answer, source_ids=['SRC-006'], supported=True, claims=[])

    monkeypatch.setattr(node, 'vinfast_manual_search', search)
    monkeypatch.setattr(node, 'structured_call', generate)
    # Exercise free-price assertions generated outside the verbatim tariff path.
    result = await node.rag_node({'latest_user_message': 'Thông tin dịch vụ VF8?', 'vehicle_model': 'VF8', 'confidence_score': .9})
    assert result['is_no_source'] is refused
    if refused:
        assert result['rag_citations'] == []
        assert result['retrieval_diagnostics']['category'] == 'unsupported_numeric_claim'
    else:
        assert result['answer_claims'][0]['conditions'] == ['tu phut thu 1 den phut thu 10']


@pytest.mark.parametrize('separator', ['; ', ', '])
def test_one_line_tariff_keeps_each_fee_with_its_own_minute_tier(separator):
    answer = separator.join(TARIFF.splitlines()[3:])
    claims = extract_numeric_claims(answer, [tariff_source()], 'VF7')
    assert len(claims) == 3
    assert [c.conditions for c in claims] == [
        ['tu phut thu 11 den phut thu 60'], ['tu phut thu 61 den phut thu 120'], ['tu phut thu 121 tro di']]
    assert validate_answer_claims(claims, [tariff_source()], [])['supported']


def test_flattened_full_tariff_does_not_attach_free_parking_tier_to_energy_price():
    answer = TARIFF.replace('\n', '; ')
    claims = extract_numeric_claims(answer, [tariff_source()], 'VF7')
    assert claims[0].conditions == ['ap dung tu ngay 19/03/2024']
    assert len(claims) == 5  # Includes the explicitly stated free-minute tier.
    assert validate_answer_claims(claims, [tariff_source()], [])['supported']


@pytest.mark.parametrize('query', ['Lịch bảo dưỡng VF8 như thế nào?', 'Lịch bảo dưỡng VF8 là gì?',
                                  'Đặt lịch bảo dưỡng VF8 . Lịch bảo dưỡng VF8 như thế nào?'])
def test_maintenance_schedule_requires_manual_not_booking_guide(query):
    assert requested_source_type(query) == 'official_manual'
    meta = {**source_registry()['SRC-001'], 'source_id': 'SRC-001', 'applicable_models': 'ALL'}
    rows = {'documents': [['7.1. Cách đặt lịch bảo dưỡng\nBước 1: Chọn Đặt dịch vụ.\nBước 2: Chọn xưởng.']],
            'metadatas': [[meta]], 'distances': [[.2]], 'ids': [['booking']]}
    assert RAGService().filter_results(rows, 'VF8', query)['citations'] == []


def test_maintenance_interval_evidence_retains_both_limits_and_condition():
    text = 'Lịch bảo dưỡng VF8\nBảo dưỡng định kỳ sau 12 tháng hoặc 12.000 km, tùy điều kiện nào đến trước.'
    meta = {**source_registry()['SRC-007'], 'source_id': 'SRC-007', 'applicable_models': 'VF8'}
    rows = {'documents': [[text]], 'metadatas': [[meta]], 'distances': [[.2]], 'ids': [['schedule']]}
    result = RAGService().filter_results(rows, 'VF8', 'Lịch bảo dưỡng VF8 như thế nào?')
    assert result['status'] == 'SUCCESS'
    assert result['citations'][0]['relevant_snippet'] == text


def test_whole_vehicle_schedule_cannot_be_replaced_by_coolant_change_note():
    text = ('Ghi chú về Lịch bảo dưỡng\nDung dịch làm mát pin và động cơ điện phải được thay thế sau mỗi 10 năm '
            'hoặc khi pin được thay thế.\nBộ truyền động điện không cần bảo dưỡng.')
    meta = {**source_registry()['SRC-007'], 'source_id': 'SRC-007', 'applicable_models': 'VF8'}
    rows = {'documents': [[text]], 'metadatas': [[meta]], 'distances': [[.2]], 'ids': [['coolant']]}
    assert RAGService().filter_results(rows, 'VF8', 'Lịch bảo dưỡng VF8 là gì?')['citations'] == []


def test_maintenance_document_lookup_accepts_reference_without_inventing_an_interval():
    text = 'Chu kỳ bảo dưỡng VF8 cần đối chiếu sổ bảo dưỡng đúng dòng xe và điều kiện sử dụng.'
    meta = {**source_registry()['SRC-004'], 'source_id': 'SRC-004', 'applicable_models': 'VF8'}
    rows = {'documents': [[text]], 'metadatas': [[meta]], 'distances': [[.2]], 'ids': [['reference']]}
    result = RAGService().filter_results(rows, 'VF8', 'Chu kỳ bảo dưỡng VF8 cần tra cứu trong tài liệu nào?')
    assert result['status'] == 'SUCCESS'
    assert result['citations'][0]['relevant_snippet'] == text
    assert RAGService().filter_results(rows, 'VF8', 'Chu kỳ bảo dưỡng VF8 là bao nhiêu km?')['citations'] == []


@pytest.mark.asyncio
async def test_rag_case_brief_does_not_repeat_customer_contact_instruction():
    from src.agents.nodes.case_brief_node import case_brief_node
    body = 'Em chưa có lịch bảo dưỡng đúng đời xe. Quý khách có thể liên hệ chuyên viên VinFast để đối chiếu.'
    result = await case_brief_node({'latest_user_message': 'Lịch bảo dưỡng VF8?', 'response': body,
                                    'is_rag_query': True, 'is_no_source': True, 'user_role': 'guest'})
    assert result['response'] == body
    assert result['needs_staff_review']


def test_booking_goal_does_not_accept_footer_mention_after_an_unrelated_procedure():
    text = ('7.4. Kiểm tra cảnh báo lỗi\nBước 1: Chọn Cảnh báo lỗi.\nBước 2: Xem các nhóm cảnh báo.\n'
            'Ứng dụng còn hỗ trợ đặt lịch bảo dưỡng và nhiều tiện ích khác.\nThông tin liên hệ dịch vụ khách hàng.')
    meta = {**source_registry()['SRC-001'], 'source_id': 'SRC-001', 'applicable_models': 'ALL'}
    rows = {'documents': [[text]], 'metadatas': [[meta]], 'distances': [[.2]], 'ids': [['footer']]}
    assert RAGService().filter_results(rows, 'VF8', 'Đặt lịch bảo dưỡng VF8 là gì?')['citations'] == []
