import json
from pathlib import Path

import pytest


def test_live_audit_requires_explicit_config_and_index(monkeypatch, tmp_path):
    from eval.answer_quality import audit_config_file, audit_index_dir
    monkeypatch.delenv('AUDIT_CONFIG_FILE', raising=False)
    with pytest.raises(ValueError, match='AUDIT_CONFIG_FILE'):
        audit_config_file()
    config = tmp_path / 'test.env'
    config.write_text('AGENT_LLM_ENABLED=false', encoding='utf-8')
    monkeypatch.setenv('AUDIT_CONFIG_FILE', str(config))
    monkeypatch.setenv('AUDIT_INDEX_DIR', str(tmp_path / 'candidate'))
    assert audit_config_file() == config
    assert audit_index_dir() == tmp_path / 'candidate'


def test_metrics_do_not_certify_factual_quality_from_http_or_citations():
    from eval.answer_quality import summarize_outputs
    rows = [{'final_diagnostics': {'answer_status': value}, 'llm_outcomes': [{'decision': 'parsed'}]}
            for value in ['answered', 'partial', 'needs_data', 'refused', 'external_action_required', 'error']]
    result = summarize_outputs(rows)
    assert result['answer_status_counts'] == {value: 1 for value in [
        'answered', 'partial', 'needs_data', 'refused', 'external_action_required', 'error']}
    assert result['model_parsed_events'] == 6
    assert result['factual_certification'] == 'NOT_REVIEWED'


def test_unreviewed_holdout_cannot_be_an_acceptance_oracle(tmp_path):
    from eval.answer_quality import load_reviewed_holdout
    path = tmp_path / 'holdout.jsonl'
    path.write_text(json.dumps({'id': 'case1', 'review_status': 'pending_review'}) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='review'):
        load_reviewed_holdout(path)
