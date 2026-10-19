"""Opt-in measurement; a passing probe is NOT an assertion of answer correctness."""
import copy
import json
import os
from pathlib import Path

import pytest

from src.config import Settings, get_settings
from src.models.db_models import ChatSession
from src.services.rag_service import RAGService

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']
pytestmark = pytest.mark.skipif(os.getenv('ANSWER_GAP_AUDIT') != '1', reason='Explicit answer-quality audit only')
ROOT = Path(__file__).resolve().parents[2]
LONG = json.loads((ROOT / 'eval/datasets/long_multitopic_memory_v1.json').read_text(encoding='utf-8'))
RAG = [json.loads(line) for line in (ROOT / 'eval/datasets/rag_test_v1.jsonl').read_text(encoding='utf-8').splitlines()]
EXTRA = [
    'Tư vấn VF8', 'So sánh VF8 Plus với VF3 Plus', 'Giá lăn bánh VF8 Plus ở Hà Nội?',
    'Chính sách bảo hành pin và lịch bảo dưỡng định kỳ', 'Biểu phí sạc tại trạm sạc công cộng',
    'Ứng dụng VinFast có tính năng gì?', 'VF7 Plus có màu gì?', 'VF8 Plus có màu gì?',
    'Bảo hành pin cao áp VF8 bao lâu?', 'Bảo hành ắc quy 12V VF8 bao lâu?',
    'VF8 chạy dịch vụ thương mại được bảo hành thế nào?', 'Xe bị ngập nước có được bảo hành không?',
    'Lịch bảo dưỡng định kỳ VF8 là gì?', 'VF3 bảo dưỡng lần đầu ở bao nhiêu km?',
    'VF5 bảo dưỡng mỗi bao nhiêu km?', 'Chi phí bảo dưỡng VF8 bao nhiêu?',
    'VF8 Eco đi được bao xa một lần sạc?', 'VF8 đi được bao xa một lần sạc?',
    'Dung lượng pin VF8 Plus là bao nhiêu?', 'Dung lượng pin VF8 là bao nhiêu?',
    'Dung lượng pin VF3 là bao nhiêu?', 'VF8 Plus sạc nhanh bao lâu?',
    'Tôi quên mật khẩu ứng dụng VinFast thì làm sao?', 'Hướng dẫn đặt lịch bảo dưỡng qua ứng dụng',
    'Mobile Service hỗ trợ những gì?', 'Tìm trạm sạc gần tôi', 'Tìm xưởng dịch vụ ở Hà Nội',
    'Xe VF5 của tôi không sạc được, báo CC01', 'Xe VF5 đang bốc khói',
    'Tôi muốn khiếu nại thái độ nhân viên showroom', 'Tôi muốn đăng ký lái thử VF8 ở Hà Nội',
    'Thời tiết ngày mai thế nào?', 'SOH là gì?',
    'What colors are available for the VF8 Plus?', 'How long is the VF8 warranty?',
    'Please explain battery warranty and scheduled maintenance.',
    'Please explain public charging, charging fees and VinFast app features.',
]
LIVE = [
    'Bảo hành pin cao áp VF8 bao lâu?', 'Lịch bảo dưỡng định kỳ VF8 là gì?',
    'VF8 Plus có màu gì?', 'VF8 Eco đi được bao xa một lần sạc?',
    'What colors are available for the VF8 Plus?', 'How long is the VF8 warranty?',
    'What is the maintenance schedule for the VF8?', 'Tôi quên mật khẩu ứng dụng VinFast thì làm sao?',
]


def fallback_kind(message):
    patterns = {
        'presentation_failed': ['could not prepare a reliable English answer'],
        'generation_failed': ['chưa hoàn tất được việc tạo câu trả lời'],
        'retrieval_unavailable': ['chưa tra cứu được'],
        'insufficient_evidence': ['chưa tìm được tài liệu chính thức', 'chưa tìm được đủ nguồn',
                                  'chưa đối chiếu đủ', 'chưa đối chiếu đầy đủ', 'chưa xác minh được thông tin',
                                  'chưa có đủ thông tin để xác nhận'],
    }
    return next((key for key, values in patterns.items() if any(v in message for v in values)), None)


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['isolated', 'indexed'])
@pytest.mark.parametrize('scenario', ['broad', *[case['id'] for case in LONG]])
async def test_measure_answer_coverage(client, customer_db, tmp_path, monkeypatch, mode, scenario):
    await measure(client, customer_db, tmp_path, monkeypatch, mode, scenario)


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv('ANSWER_GAP_LIVE') != '1', reason='Live provider audit requires explicit opt-in')
async def test_measure_configured_provider_sample(client, customer_db, tmp_path, monkeypatch):
    await measure(client, customer_db, tmp_path, monkeypatch, 'live', 'live-sample')


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv('ANSWER_GAP_LIVE') != '1', reason='Explicit provider audit only')
async def test_measure_configured_incident(client, customer_db, tmp_path, monkeypatch):
    await measure(client, customer_db, tmp_path, monkeypatch, 'live', 'live-incident')


@pytest.mark.asyncio
@pytest.mark.parametrize('case', ['informational_adas', 'vietnamese_hazardous_question'])
async def test_semantic_output_contract(client, customer_db, case, tmp_path):
    question = ('Hệ thống hỗ trợ người lái ADAS trên xe VF 8 bao gồm những tính năng cơ bản nào?'
                if case == 'informational_adas' else
                'Cách tự đấu dây điện để can thiệp tăng công suất pin xe điện tại nhà?')
    response = await client.post('/api/v1/customer/chat', json={'session_id': case, 'message': question})
    assert response.status_code == 200
    data = response.json()['data']
    customer_db.expire_all()
    state = customer_db.get(ChatSession, case).memory_states[case]
    (tmp_path / 'semantic-output.json').write_text(json.dumps({'case': case, 'question': question,
        'response': data, 'context': state['conversation_context']}, ensure_ascii=False, indent=2), encoding='utf-8')
    if case == 'informational_adas':
        assert state['conversation_context']['active_goal'] != 'incident'
    else:
        assert data['language'] == 'vi'


async def measure(client, db, tmp_path, monkeypatch, mode, scenario):
    settings = get_settings()
    if mode in {'indexed', 'live'}:
        monkeypatch.setattr(settings, 'chroma_persist_dir', str(ROOT / '.test-runs/answer-gap-index'))
    if mode == 'live':
        configured = Settings(_env_file=Path('D:/142.AI20K/P-142/.env'))
        for name in ('openai_api_key', 'openai_base_url', 'google_api_key', 'model_name', 'normalization_model',
                     'agent_turn_timeout_s', 'agent_llm_timeout_s', 'normalization_timeout_s',
                     'rag_retrieval_timeout_s', 'rag_max_distance', 'rag_context_max_bytes', 'agent_context_max_bytes'):
            monkeypatch.setattr(settings, name, getattr(configured, name))
        assert settings.openai_api_key or settings.google_api_key, 'No configured provider'
        monkeypatch.setattr(settings, 'agent_llm_enabled', True)
    from src.services.agent_llm import reset_circuits
    reset_circuits()
    original, searches, outcomes = RAGService.retrieve, [], []
    from src.services import agent_llm
    record_outcome = agent_llm.record_outcome

    def recorded(state, prompt, decision, *args, **kwargs):
        diagnostics = kwargs.get('diagnostics') or {}
        outcomes.append({'prompt': prompt, 'decision': decision,
                         'failure': {k: diagnostics[k] for k in ('error_type', 'failure_kind', 'timeout_phase') if k in diagnostics}})
        return record_outcome(state, prompt, decision, *args, **kwargs)

    monkeypatch.setattr(agent_llm, 'record_outcome', recorded)

    def traced(self, query, *args, **kwargs):
        result = original(self, query, *args, **kwargs)
        searches.append({'query': query, 'model': kwargs.get('vehicle_model'), 'status': result['status'],
                         'source_ids': [c['source_id'] for c in result.get('citations', [])],
                         'diagnostics': copy.deepcopy(result.get('diagnostics', {}))})
        return result

    monkeypatch.setattr(RAGService, 'retrieve', traced)
    if scenario == 'broad':
        steps = [{'message': row['query'], 'benchmark_id': row['id'],
                  'expected_keywords': row.get('expected_answer_keywords', [])} for row in RAG]
        steps += [{'message': question} for question in EXTRA if question not in {row['query'] for row in RAG}]
    elif scenario == 'live-sample':
        steps = [{'message': row['query'], 'benchmark_id': row['id'],
                  'expected_keywords': row.get('expected_answer_keywords', [])} for row in RAG]
        steps += [{'message': question} for question in EXTRA if question not in {row['query'] for row in RAG}]
        steps += [{'message': question, 'session_group': 'live-context'} for question in (
            'Tư vấn VF8', 'Ứng dụng VinFast có tính năng gì?', 'Biểu phí sạc tại trạm sạc công cộng',
            'Chính sách bảo hành pin và lịch bảo dưỡng định kỳ')]
    elif scenario == 'live-incident':
        steps = [{'message': question} for question in (
            'Xe VF5 của tôi không sạc được, mã lỗi CC01', 'Trụ P01 tại Vincom Metropolis',
            'Xe báo lỗi CC01, pin còn 35%', 'Tôi đã nói rồi, còn thiếu gì?',
            'Không phải trụ P01, trụ P02', 'Xe không còn báo CC01 nữa', 'Tôi đã dừng ở nơi an toàn')]
    else:
        steps = next(case['turns'] for case in LONG if case['id'] == scenario)
    rows = []
    for number, step in enumerate(steps, 1):
        searches.clear()
        outcomes.clear()
        session = f'{mode}-{scenario}-{number}' if scenario in {'broad', 'live-sample'} else f'{mode}-{scenario}'
        session = step.get('session_group', session)
        payload = {'session_id': session, 'message': step['message']}
        if step.get('language'):
            payload['language'] = 'en' if step['language'] == 'vi' else 'vi'
        result = await client.post('/api/v1/customer/chat', json=payload)
        assert result.status_code == 200, result.text
        data = result.json()['data']
        db.expire_all()
        state = db.get(ChatSession, session).memory_states[session]
        keywords = step.get('expected_keywords', [])
        rows.append({'number': number, 'input': step['message'], 'response': data['message'],
                     'fallback_kind': fallback_kind(data['message']), 'sources': data.get('citations') or [],
                     'context': state.get('conversation_context'), 'retrieval': state.get('conversation_retrieval'),
                     'searches': copy.deepcopy(searches), 'llm_outcomes': copy.deepcopy(outcomes),
                     'final_diagnostics': state.get('final_diagnostics'),
                     'benchmark_id': step.get('benchmark_id'), 'expected_keywords': keywords,
                     'keyword_match_only': all(k.casefold() in data['message'].casefold() for k in keywords) if keywords else None})
        (tmp_path / 'answer-coverage.json').write_text(json.dumps({'mode': mode, 'scenario': scenario,
            'model_enabled': settings.agent_llm_enabled, 'turns': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
    assert len(rows) == len(steps)
