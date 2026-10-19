"""Configured-provider regression for the exact fourteen previously unanswered probes."""
import json
import os
from pathlib import Path
import pytest
from src.config import Settings, get_settings
from src.models.db_models import ChatSession
from eval.answer_quality import audit_config_file, audit_index_dir

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv('ANSWER_GAP_14_LIVE') != '1', reason='Explicit configured-provider gate')
@pytest.mark.parametrize('language', ['vi', 'en'])
async def test_exact_fourteen_through_customer_api(client, customer_db, monkeypatch, tmp_path, language):
    settings = get_settings()
    configured = Settings(_env_file=audit_config_file())
    for name in ('openai_api_key', 'openai_base_url', 'google_api_key', 'model_name', 'normalization_model',
                 'agent_turn_timeout_s', 'agent_llm_timeout_s', 'normalization_timeout_s',
                 'rag_retrieval_timeout_s', 'rag_max_distance', 'rag_context_max_bytes', 'agent_context_max_bytes'):
        monkeypatch.setattr(settings, name, getattr(configured, name))
    monkeypatch.setattr(settings, 'chroma_persist_dir', str(audit_index_dir()))
    monkeypatch.setattr(settings, 'agent_llm_enabled', True)
    from src.services.agent_llm import reset_circuits
    reset_circuits()
    cases = json.loads((ROOT / 'eval/datasets/answer_gap_14_v1.json').read_text(encoding='utf-8'))
    outputs = []
    traces = []
    from src.services.rag_service import RAGService
    original = RAGService.retrieve
    def traced(self, query, *args, **kwargs):
        result = original(self, query, *args, **kwargs)
        traces.append({'query': query, 'result': result})
        return result
    monkeypatch.setattr(RAGService, 'retrieve', traced)
    for case in cases:
        traces.clear()
        session = 'gap14-' + language + '-' + case['id']
        result = await client.post('/api/v1/customer/chat', json={
            'session_id': session, 'message': case['question_en'] if language == 'en' else case['question'],
            'language': 'vi' if language == 'en' else 'en'})
        assert result.status_code == 200
        data = result.json()['data']
        customer_db.expire_all()
        state = customer_db.get(ChatSession, session).memory_states[session]
        status = state.get('final_diagnostics', {}).get('answer_status')
        output = {**case, 'actual_status': status, 'response': data['message'],
                  'traces': list(traces), 'payload': data,
                  'language': data['language'], 'sources': data.get('citations') or [],
                  'diagnostics': state.get('final_diagnostics', {})}
        output['passed'] = (status == case['expected_status'] and data['language'] == language
            and all(term.casefold() in data['message'].casefold() for term in case['required_en' if language == 'en' else 'required'])
            and (case['expected_status'] == 'needs_clarification' or bool(output['sources'])))
        outputs.append(output)
        (tmp_path / 'answer-gap-14-results.json').write_text(
            json.dumps(outputs, ensure_ascii=False, indent=2), encoding='utf-8')
    assert all(row['passed'] for row in outputs), [(r['id'], r['actual_status'], r['response']) for r in outputs if not r['passed']]
