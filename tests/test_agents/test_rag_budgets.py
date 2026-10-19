import pytest
from pydantic import ValidationError

from src.agents.context_manager import ContextLayers, trim_context_layers
from src.config import Settings, get_settings
from src.services.rag_service import RAGService, source_registry


def test_app_procedure_keeps_complete_4811_bytes_after_car_history():
    from src.agents.context_manager import build_7_layer_context, load_prompt, utf8_size
    start = 'Quên mật khẩu ứng dụng\nBước 1: Chọn Quên mật khẩu.\nBước 2: Nhập mã xác nhận.\n'
    end = '\nChỉ áp dụng cho tài khoản đã xác minh.'
    document = start + 'x' * (4811 - utf8_size(start + end)) + end
    assert utf8_size(document) == 4811
    layers = build_7_layer_context({
        'latest_user_message': 'Cách lấy lại mật khẩu ứng dụng?',
        'memory_summary': 'Tư vấn VF8. ' * 700,
        'rag_citations': [{'source_id': 'SRC-001', 'relevant_snippet': document}],
    }, load_prompt('rag_qa'))
    messages = trim_context_layers(layers, max_bytes=8000)
    rendered = '\n'.join(str(message.content) for message in messages)
    assert document in rendered
    assert layers.system_context in rendered and layers.policy_context in rendered
    assert 'Tư vấn VF8.' not in rendered
    assert sum(utf8_size(str(message.content)) for message in messages) <= 8000


def evidence(text):
    meta = {**source_registry()['SRC-002'], 'source_id': 'SRC-002', 'applicable_models': 'ALL'}
    return {'documents': [[text]], 'metadatas': [[meta]], 'distances': [[0.2]], 'ids': [['p1']]}


def test_complete_3285_byte_evidence_can_fit():
    text = 'Điều kiện bảo hành chính thức. ' + 'a' * 3243
    assert len(text.encode('utf-8')) == 3285
    out = RAGService().filter_results(evidence(text), 'VF8')
    assert out['status'] == 'SUCCESS'
    assert out['citations'][0]['relevant_snippet'] == text
    assert out['diagnostics']['context_bytes_used'] == 3285


def test_budget_never_cuts_final_condition():
    text = 'Thông tin chính thức. ' * 400 + 'Chỉ áp dụng khi đủ điều kiện.'
    out = RAGService().filter_results(evidence(text), 'VF8')
    assert out['citations'] == []
    assert out['diagnostics']['category'] == 'context_budget_exceeded'


def test_prompt_preserves_pinned_and_question():
    layers = ContextLayers('system', 'policy', user_context='câu hỏi', retrieval_context='x' * 500)
    messages = trim_context_layers(layers, max_bytes=100)
    assert 'system' in str(messages[0].content)
    assert 'policy' in str(messages[0].content)
    assert 'câu hỏi' in str(messages[-1].content)
    assert sum(len(str(m.content).encode('utf-8')) for m in messages) <= 100


def test_vietnamese_budget_uses_bytes():
    layers = ContextLayers('s', 'p', user_context='ắ' * 30)
    with pytest.raises(ValueError, match='budget'):
        trim_context_layers(layers, max_bytes=60)


def test_invalid_budget_configuration_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, rag_context_max_bytes=9000, agent_context_max_bytes=8000)
    assert get_settings().rag_context_max_bytes > 3285
