"""Opt-in release gate against independently reviewed, frozen holdout bytes."""
import copy
from hashlib import sha256
import json
import os
import time
from pathlib import Path

import pytest
from src.config import Settings, get_settings
from src.models.db_models import ChatSession
from eval.answer_quality import audit_config_file, audit_index_dir, index_identity, load_reviewed_holdout, grade_holdout_row, summarize_outputs

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv('ANSWER_QUALITY_HOLDOUT') != '1', reason='Reviewed holdout and configured provider required')
async def test_reviewed_frozen_holdout(client, customer_db, monkeypatch, tmp_path):
    path = ROOT / 'eval/datasets/answer_quality_holdout_v1.jsonl'
    cases = load_reviewed_holdout(path)
    frozen_hash = sha256(path.read_bytes()).hexdigest()
    settings = get_settings()
    configured = Settings(_env_file=audit_config_file())
    for name in ('openai_api_key', 'openai_base_url', 'google_api_key', 'model_name', 'normalization_model',
                 'agent_turn_timeout_s', 'agent_llm_timeout_s', 'normalization_timeout_s',
                 'rag_retrieval_timeout_s', 'rag_max_distance', 'rag_context_max_bytes', 'agent_context_max_bytes'):
        monkeypatch.setattr(settings, name, getattr(configured, name))
    monkeypatch.setattr(settings, 'chroma_persist_dir', str(audit_index_dir()))
    monkeypatch.setattr(settings, 'agent_llm_enabled', True)
    from src.services import agent_llm
    agent_llm.reset_circuits()
    outcomes = []
    original = agent_llm.record_outcome
    def recorded(state, prompt, decision, *args, **kwargs):
        outcomes.append({'prompt': prompt, 'decision': decision})
        return original(state, prompt, decision, *args, **kwargs)
    monkeypatch.setattr(agent_llm, 'record_outcome', recorded)
    rows = []
    for case in cases:
        outcomes.clear()
        session = 'holdout-' + case['id']
        started = time.monotonic()
        response = await client.post('/api/v1/customer/chat', json={'session_id': session,
            'message': case['question'], 'language': 'vi' if case['language'] == 'en' else 'en'})
        assert response.status_code == 200, case['id']
        data = response.json()['data']
        customer_db.expire_all()
        state = customer_db.get(ChatSession, session).memory_states[session]
        output = {'id': case['id'], 'category': case['category'], 'question': case['question'],
                  'latency_ms': round((time.monotonic() - started) * 1000, 2),
                  'response': data['message'], 'language': data['language'], 'sources': data.get('citations') or [],
                  'answer_status': state.get('final_diagnostics', {}).get('answer_status'),
                  'final_diagnostics': state.get('final_diagnostics', {}),
                  'retrieval': state.get('conversation_retrieval', {}), 'llm_outcomes': copy.deepcopy(outcomes)}
        output['grade'] = grade_holdout_row(case, output)
        rows.append(output)
        report = {'holdout_sha256': sha256(path.read_bytes()).hexdigest(),
                  'index_identity': index_identity(audit_index_dir()), 'model': settings.model_name,
                  'metrics': summarize_outputs(rows), 'turns': rows,
                  'answerable_pass': sum(r['grade']['passed'] for r in rows if r['category'] == 'answerable'),
                  'boundary_pass': sum(r['grade']['passed'] for r in rows if r['category'] == 'boundary')}
        (tmp_path / 'holdout-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert sha256(path.read_bytes()).hexdigest() == frozen_hash, 'Holdout bytes changed during run; invalidate results'
    assert report['answerable_pass'] >= 29, [(r['id'],r['grade']) for r in rows if not r['grade']['passed']]
    assert report['boundary_pass'] == 10, [(r['id'],r['grade']) for r in rows if not r['grade']['passed']]
