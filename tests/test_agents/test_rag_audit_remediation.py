import importlib

import pytest


def test_textual_warranty_scope_is_validated_as_text_with_conditions():
    from src.services.answer_evidence import AnswerClaim, validate_answer_claims
    claim = AnswerClaim(claim_key='warranty', value='toàn lãnh thổ Việt Nam', unit='', subject='', source_ids=['policy'])
    citation = {'source_id': 'policy', 'source_type': 'official_policy',
                'relevant_snippet': 'Bảo hành có hiệu lực trên toàn lãnh thổ Việt Nam.'}
    assert validate_answer_claims([claim], [citation], [])['supported']
    assert not validate_answer_claims([claim.model_copy(update={'value':'toàn thế giới'})], [citation], [])['supported']


def test_complete_procedure_can_span_lines_in_the_same_selected_section():
    from src.services.answer_evidence import AnswerClaim, validate_answer_claims
    citation = {'source_id': 'guide', 'source_type': 'official_guide',
                'relevant_snippet': 'Cách đăng nhập\nBước 1: Nhập tài khoản.\nBước 2: Nhập mật khẩu.\nBước 3: Chọn đăng nhập.'}
    claim = AnswerClaim(claim_key='procedure', value='Nhập tài khoản; Nhập mật khẩu; Chọn đăng nhập.',
                        unit='', subject='', source_ids=['guide'])
    assert validate_answer_claims([claim], [citation], [])['supported']
    assert not validate_answer_claims([claim.model_copy(update={'value':'Chọn đăng nhập; Nhập mật khẩu.'})], [citation], [])['supported']
    assert not validate_answer_claims([claim.model_copy(update={'value':'Nhập tài khoản; Tắt xác thực.'})], [citation], [])['supported']

from src.agents.context_manager import ContextLayers, trim_context_layers, utf8_size
from src.services.answer_evidence import AnswerClaim, validate_answer_claims
from src.services.rag_service import RAGService, rank_candidates, source_registry


def test_feature_claim_is_grounded_in_same_sentence_without_quantity():
    source = {'source_id': 'SRC-001', 'relevant_snippet':
              'Tính năng điều hòa cho phép người dùng theo dõi mức quạt và nhiệt độ thực tế trong xe '
              'để điều chỉnh hệ thống điều hòa ô tô phù hợp với nhu cầu sử dụng.'}
    claim = AnswerClaim(claim_key='features', value='Có thể theo dõi và điều chỉnh điều hòa',
                        unit='', subject='Tính năng điều hòa', source_ids=['SRC-001'])
    assert validate_answer_claims([claim], [source], [])['supported']


@pytest.mark.parametrize('value,source', [
    ('Hỗ trợ tự lái hoàn toàn', 'Hỗ trợ người lái giữ làn đường.'),
    ('Hỗ trợ điều chỉnh điều hòa', 'Không hỗ trợ điều chỉnh điều hòa.'),
    ('Hỗ trợ điều chỉnh điều hòa mọi lúc', 'Hỗ trợ điều chỉnh điều hòa.'),
])
def test_textual_claim_does_not_certify_unstated_or_negated_features(value, source):
    claim = AnswerClaim(claim_key='features', value=value, unit='', subject='', source_ids=['s'])
    assert not validate_answer_claims([claim], [{'source_id': 's', 'relevant_snippet': source}], [])['supported']


def test_textual_feature_cannot_drop_an_operating_condition():
    claim = AnswerClaim(claim_key='features', value='Hỗ trợ điều chỉnh điều hòa', unit='', subject='', source_ids=['s'])
    source = {'source_id': 's', 'relevant_snippet': 'Hỗ trợ điều chỉnh điều hòa chỉ khi xe đã kết nối mạng.'}
    assert not validate_answer_claims([claim], [source], [])['supported']


def test_numeric_claim_cannot_borrow_other_drivetrain():
    claim = AnswerClaim(claim_key='power', value='150', unit='kW', subject='VF7 Plus AWD', source_ids=['s'])
    source = {'source_id': 's', 'relevant_snippet': 'VF7 Plus FWD công suất 150 kW.'}
    assert not validate_answer_claims([claim], [source], [])['supported']


def test_tariff_keeps_denominator_in_numeric_claim_unit():
    from src.services.answer_evidence import extract_numeric_claims
    source = {'source_id': 's', 'relevant_snippet': 'Giá sạc là 3.858 đồng/kWh.'}
    claims = extract_numeric_claims(source['relevant_snippet'], [source])
    assert claims[0].unit == 'đồng/kWh'
    assert validate_answer_claims(claims, [source], [])['supported']
    wrong = claims[0].model_copy(update={'unit': 'đồng/phút'})
    assert not validate_answer_claims([wrong], [source], [])['supported']


def test_tariff_effective_date_and_full_parking_tiers_are_retained():
    from src.services.answer_evidence import extract_numeric_claims
    text = ('Đơn giá sạc: 3.858 VNĐ/kWh (áp dụng từ ngày 19/03/2024).\n'
            'Phí sử dụng dịch vụ trạm sạc bổ sung sau khi hoàn thành phiên sạc:\n'
            'Miễn phí từ phút thứ 1 đến phút thứ 10\n'
            '1.000 đồng/phút từ phút thứ 11 đến phút thứ 60\n'
            '2.000 đồng/phút từ phút thứ 61 đến phút thứ 120\n'
            '4.000 đồng/phút từ phút thứ 121 trở đi')
    source = {'source_id': 'SRC-006', 'source_type': 'official_service', 'relevant_snippet': text}
    claims = extract_numeric_claims(text, [source])
    assert len(claims) == 5  # Includes the explicitly stated free-minute tier.
    assert validate_answer_claims(claims, [source], [])['supported']


def test_tariff_cannot_drop_minute_tier_or_effective_date():
    from src.services.answer_evidence import extract_numeric_claims
    source = {'source_id': 's', 'source_type': 'official_service', 'relevant_snippet':
              'Đơn giá sạc: 3.858 VNĐ/kWh (áp dụng từ ngày 19/03/2024).\n'
              '1.000 đồng/phút từ phút thứ 11 đến phút thứ 60'}
    for answer in ('Giá sạc từ 3.858 VNĐ/kWh.', 'Giá sạc từ 1.000 đồng/phút.'):
        claims = extract_numeric_claims(answer, [source])
        assert not validate_answer_claims(claims, [source], [])['supported']


@pytest.mark.parametrize('models,supported', [(['ALL'], True), (['VF8'], True), (['VF5'], False)])
def test_general_service_tariff_honors_explicit_model_applicability(models, supported):
    source = {'source_id': 's', 'source_type': 'official_service', 'applicable_models': models,
              'relevant_snippet': 'Đơn giá sạc: 3.858 VNĐ/kWh.'}
    claim = AnswerClaim(claim_key='price', value='3.858', unit='VNĐ/kWh', subject='VF8', source_ids=['s'])
    assert validate_answer_claims([claim], [source], [])['supported'] is supported


def test_tariff_request_cannot_use_charger_power_as_answer():
    source = source_registry()['SRC-006']
    rows = {'documents': [['Hướng dẫn sử dụng trạm sạc ô tô VinFast\nTrụ sạc siêu nhanh DC 250kW.']],
            'metadatas': [[{**source, 'source_id': 'SRC-006', 'applicable_models': 'ALL'}]],
            'distances': [[.2]], 'ids': [['charger-power']]}
    assert RAGService().filter_results(rows, query='Biểu phí sạc ô tô điện VinFast')['status'] == 'NO_SOURCE'


@pytest.mark.parametrize('variant,power', [('Plus', '150 kW'), ('Plus AWD', '260 kW')])
def test_technical_catalog_uses_scoped_canonical_power(variant, power):
    result = RAGService().retrieve(f'Công suất VF7 {variant}', vehicle_model='VF7', source_need='catalog')
    assert result['status'] == 'SUCCESS'
    assert len(result['citations']) == 1
    assert power in result['citations'][0]['relevant_snippet']
    assert result['citations'][0]['fact_scope']['drivetrain'] == ('AWD' if 'AWD' in variant else 'FWD')


@pytest.mark.parametrize('query', ['Cách xem lịch sử sạc trên ứng dụng?', 'Cách điều chỉnh điều hòa trên ứng dụng?'])
def test_app_goal_cannot_use_an_unrelated_guide_section(query):
    source = source_registry()['SRC-001']
    rows = {'documents': [['Hướng dẫn ứng dụng VinFast\nBước 1: Chọn mục đặt lịch bảo dưỡng.\nBước 2: Chọn xưởng dịch vụ.']],
            'metadatas': [[{**source, 'source_id': 'SRC-001', 'applicable_models': 'ALL'}]],
            'distances': [[.2]], 'ids': [['wrong-goal']]}
    assert RAGService().filter_results(rows, query=query)['status'] == 'NO_SOURCE'


def test_optional_memory_cannot_evict_complete_evidence():
    layers = ContextLayers('system safety', 'policy', task_context='task', user_context='question',
                           memory_context='old history ' * 100, retrieval_context='all steps and final condition',
                           required_memory_context='model VF8')
    messages = trim_context_layers(layers, max_bytes=350)
    rendered = '\n'.join(str(m.content) for m in messages)
    assert 'all steps and final condition' in rendered
    assert 'model VF8' in rendered and 'system safety' in rendered
    assert sum(utf8_size(str(m.content)) for m in messages) <= 350


def test_charging_policy_retrieval_includes_reviewed_service_sources(monkeypatch, tmp_path):
    from src.services import rag_service as module
    from src.config import get_settings
    path = tmp_path / 'index'
    path.mkdir()
    (path / 'chroma.sqlite3').touch()
    monkeypatch.setattr(get_settings(), 'chroma_persist_dir', str(path))
    service = source_registry()['SRC-006']

    class Collection:
        configuration = {}

        def count(self):
            return 1

        def query(self, *, where, **kwargs):
            permitted = where is None or 'SRC-006' in where['source_id']['$in']
            return {'documents': [['Biểu phí sạc ô tô điện VinFast: đơn giá sử dụng dịch vụ sạc 3.858 VNĐ/kWh theo chính sách.'] if permitted else []],
                    'metadatas': [[{**service, 'source_id': 'SRC-006', 'applicable_models': 'ALL'}] if permitted else []],
                    'distances': [[.2] if permitted else []], 'ids': [['tariff'] if permitted else []]}

    monkeypatch.setattr(module, 'get_collection', lambda _: Collection())
    result = RAGService().retrieve('Biểu phí sạc ô tô điện VinFast', source_need='policy', cost_subject='charging')
    assert result['status'] == 'SUCCESS'
    assert result['citations'][0]['source_id'] == 'SRC-006'


def test_purpose_ranking_prefers_tariff_over_warranty_at_similar_distance():
    rows = [('VF8 bảo hành pin. Giá dịch vụ được công bố.', {'source_type': 'official_policy'}, .1, 'warranty'),
            ('Biểu phí sạc: đơn giá sử dụng trạm sạc.', {'source_type': 'official_service'}, .2, 'tariff')]
    assert rank_candidates('Biểu phí sạc VF8', rows)[0][3] == 'tariff'


@pytest.mark.asyncio
async def test_unstated_numeric_placeholders_do_not_block_sourced_procedure(monkeypatch):
    node = importlib.import_module('src.agents.nodes.rag_node')
    source = {**source_registry()['SRC-001'], 'source_id': 'SRC-001', 'applicable_models': ['ALL'],
              'distance': .2, 'relevant_snippet': 'Lịch sử sạc\nBước 1: Chọn Lịch sử sạc để xem các phiên sạc trước đó.'}

    async def search(*args, **kwargs):
        return {'status': 'SUCCESS', 'citations': [source]}

    async def generate(*args, **kwargs):
        return node.GroundedAnswer(answer='Chọn Lịch sử sạc để xem các phiên sạc trước đó.',
                                   source_ids=['SRC-001'], supported=True,
                                   claims=[AnswerClaim(claim_key='charging_time', value='Không xác định', unit='phút',
                                                       subject='', source_ids=['SRC-001'])])

    monkeypatch.setattr(node, 'vinfast_manual_search', search)
    monkeypatch.setattr(node, 'structured_call', generate)
    result = await node.rag_node({'latest_user_message': 'Cách xem lịch sử sạc trên ứng dụng?', 'confidence_score': .9})
    assert not result['is_no_source']
    assert result['answer_claims'] == []
    assert result['rag_citations'][0]['source_id'] == 'SRC-001'


@pytest.mark.asyncio
async def test_mandatory_context_overflow_is_reported_before_generation(monkeypatch):
    from src.config import get_settings
    node = importlib.import_module('src.agents.nodes.rag_node')
    source = {**source_registry()['SRC-002'], 'source_id': 'SRC-002', 'applicable_models': ['ALL'],
              'distance': .2, 'relevant_snippet': 'Điều kiện bảo hành VF8: sử dụng đúng hướng dẫn và bảo dưỡng định kỳ.'}

    async def search(*args, **kwargs):
        return {'status': 'SUCCESS', 'citations': [source]}

    async def generate(*args, **kwargs):
        pytest.fail('Generation must not run when required context exceeds the prompt budget')

    monkeypatch.setattr(node, 'vinfast_manual_search', search)
    monkeypatch.setattr(node, 'structured_call', generate)
    monkeypatch.setattr(get_settings(), 'agent_context_max_bytes', 4000)
    result = await node.rag_node({'latest_user_message': 'Điều kiện bảo hành VF8?', 'confidence_score': .9,
                                  'captured_fields': {'confirmed_fact': 'x' * 4000}})
    assert result['is_no_source']
    assert result['rag_citations'] == []
    assert result['retrieval_diagnostics']['stage'] == 'prompt'
    assert result['retrieval_diagnostics']['category'] == 'context_budget_exceeded'


@pytest.mark.asyncio
@pytest.mark.parametrize('status,category,query', [
    ('NO_SOURCE', 'no_eligible_evidence', 'Thông số xe VF8?'),
    ('NO_SOURCE', 'no_eligible_evidence', 'Điều kiện bảo hành VF8?'),
    ('TIMEOUT', 'timeout', 'Thông số xe VF8?'),
    ('NO_SOURCE', 'context_budget_exceeded', 'Thông số xe VF8?'),
])
async def test_rag_failure_gives_customer_action_without_promising_handoff(monkeypatch, status, category, query):
    node = importlib.import_module('src.agents.nodes.rag_node')

    async def search(*args, **kwargs):
        return {'status': status, 'citations': [], 'diagnostics': {'category': category}}

    monkeypatch.setattr(node, 'vinfast_manual_search', search)
    result = await node.rag_node({'latest_user_message': query, 'confidence_score': .9})
    reply = result['response'].casefold()
    assert not any(phrase in reply for phrase in ('sẽ chuyển', 'sẽ ghi nhận', 'giới hạn xử lý', 'vượt giới hạn'))
    assert 'quý khách' in reply
    assert 'liên hệ' in reply or 'thử lại' in reply
    assert result['is_no_source']
    assert result['retrieval_diagnostics']['category'] == category
