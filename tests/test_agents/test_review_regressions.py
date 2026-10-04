import pytest

from scripts.run_agent_eval import grounded_answer
from src.agents.nodes.triage_node import classify_request_kind
from src.services.rag_service import RAGService, select_supported_evidence, source_registry


@pytest.mark.parametrize('query', ['VF8 không mở được cửa, làm thế nào?', 'Màn hình VF8 bị đen, làm thế nào?'])
def test_actual_failure_precedes_question_marker(query):
    assert classify_request_kind(query) == 'incident'


def test_instruction_selection_retains_all_steps():
    text = 'Đặt lịch dịch vụ\n' + '\n'.join(f'Bước {i}: thao tác {i}' for i in range(1, 6))
    assert 'Bước 5' in select_supported_evidence('Cách đặt lịch dịch vụ?', [{'relevant_snippet': text}])[0]['relevant_snippet']


def test_numeric_grounding_has_boundaries():
    assert not grounded_answer({'expected_source_id': 'SRC-002', 'expected_answer_keywords': ['160.000 km']}, {'response_type': 'FAQ_ANSWER', 'response': '1160000 km', 'rag_citations': [{'source_id': 'SRC-002'}]})


@pytest.mark.parametrize('query,text', [('Dung lượng pin VF7 bao nhiêu?', 'VF7 Eco 59 kWh'), ('Dung lượng pin VF7 Plus đời 2026 bao nhiêu?', 'VF7 Plus 2023: 70 kWh')])
def test_catalog_applicability_is_resolved(query, text):
    meta = {**source_registry()['SRC-009'], 'source_id': 'SRC-009', 'applicable_models': 'VF7'}
    result = {'documents': [[text]], 'metadatas': [[meta]], 'distances': [[0.2]], 'ids': [['spec']]}
    assert RAGService().filter_results(result, 'VF7', query)['status'] == 'NO_SOURCE'


def test_warranty_for_other_component_is_not_an_answer():
    meta = {**source_registry()['SRC-002'], 'source_id': 'SRC-002', 'applicable_models': 'ALL'}
    result = {'documents': [['Gỉ sét VF5: 7 năm']], 'metadatas': [[meta]], 'distances': [[0.2]], 'ids': [['rust']]}
    assert RAGService().filter_results(result, 'VF5', 'Bảo hành hệ thống truyền động VF5 bao lâu?')['status'] == 'NO_SOURCE'


def test_source_title_cannot_substitute_for_answer_text():
    meta = {**source_registry()['SRC-005'], 'source_id': 'SRC-005', 'applicable_models': 'ALL'}
    result = {'documents': [['Thông tin địa chỉ công ty và người đại diện.']], 'metadatas': [[meta]], 'distances': [[0.2]], 'ids': [['footer']]}
    assert RAGService().filter_results(result, None, 'VinFast có Mobile Service không?')['status'] == 'NO_SOURCE'


@pytest.mark.asyncio
@pytest.mark.parametrize('query', ['VF8 không mở được cửa, làm thế nào?', 'Màn hình VF8 bị đen, làm thế nào?'])
async def test_incident_cannot_bypass_review_with_available_faq(monkeypatch, query):
    from src.agents.graph import agent
    from src.services.rag_service import rag_service
    citation = {**source_registry()['SRC-002'], 'source_id': 'SRC-002', 'applicable_models': ['ALL'], 'distance': 0.2, 'relevant_snippet': 'Điều kiện bảo hành chính thức.'}
    monkeypatch.setattr(rag_service, 'retrieve', lambda *a, **k: {'status': 'SUCCESS', 'citations': [citation]})
    out = await agent.ainvoke({'query': query, 'user_role': 'customer', 'clarification_turn': 2})
    assert out['needs_staff_review']
    assert out['response_type'] != 'FAQ_ANSWER'


def test_charging_procedure_cannot_answer_service_appointment():
    meta = {**source_registry()['SRC-001'], 'source_id': 'SRC-001', 'applicable_models': 'ALL'}
    result = {'documents': [['Hướng dẫn tính năng pin và sạc trên ứng dụng VinFast\nBước 1: Chọn lịch sạc để kiểm tra các lịch sạc trong ứng dụng.']], 'metadatas': [[meta]], 'distances': [[0.2]], 'ids': [['charging-procedure']]}
    out = RAGService().filter_results(result, None, 'Cách đặt lịch dịch vụ bảo dưỡng trên ứng dụng VinFast?')
    assert out['status'] == 'NO_SOURCE'
    assert out['diagnostics']['candidates'][0]['reason'] == 'procedure_goal_mismatch'
