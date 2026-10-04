import json
import subprocess
import sys


def approved_report():
    return {'gate_kind': 'acceptance', 'report_version': 1, 'metadata': {'label_status': 'approved',
            'provenance': {key: 'a' * 64 for key in ('kb', 'model', 'prompt', 'dataset', 'mapping', 'config')}},
            'coverage': {'critical': 10, 'sourced': 20, 'no_source': 10, 'evidence_labeled': 20},
            'metrics': {'evidence_recall_at_3': 1., 'evidence_precision_at_3': 1.,
                        'grounded_answer_rate': 1., 'no_source_compliance': 1., 'critical_safety_recall': 1.}}


def config():
    return {'report_version': 1, 'thresholds': {k: .8 for k in approved_report()['metrics']},
            'minimum_coverage': {k: 10 for k in approved_report()['coverage']}}


def test_draft_report_cannot_pass_acceptance():
    from eval.rag_measurement import check_acceptance
    report = approved_report()
    report['metadata']['label_status'] = 'draft'
    assert check_acceptance(report, config())


def test_missing_hash_or_nan_metric_fails_gate():
    from eval.rag_measurement import check_acceptance
    report = approved_report()
    assert check_acceptance(report, config()) == []
    report['metrics']['evidence_recall_at_3'] = float('nan')
    assert check_acceptance(report, config())
    report = approved_report()
    del report['metadata']['provenance']['mapping']
    assert check_acceptance(report, config())


def test_engineering_is_not_production_acceptance():
    from eval.rag_measurement import check_acceptance
    report = approved_report()
    report['gate_kind'] = 'engineering'
    assert check_acceptance(report, config())


def test_invalid_config_cannot_bypass_acceptance():
    from eval.rag_measurement import check_acceptance
    for invalid in ({'report_version': 1, 'thresholds': {}, 'minimum_coverage': {}},
                    {**config(), 'thresholds': {k: float('nan') for k in config()['thresholds']}}):
        assert check_acceptance(approved_report(), invalid)


def test_cli_rejects_draft_and_malformed(tmp_path):
    report = tmp_path / 'report.json'
    configuration = tmp_path / 'config.json'
    output = tmp_path / 'gate.json'
    configuration.write_text(json.dumps(config()), encoding='utf-8')
    report.write_text(json.dumps({'metadata': {'label_status': 'draft'}}), encoding='utf-8')
    args = [sys.executable, 'scripts/check_rag_quality.py', '--report', str(report), '--config', str(configuration), '--output', str(output)]
    assert subprocess.run(args, capture_output=True).returncode == 1
    report.write_text('{broken', encoding='utf-8')
    assert subprocess.run(args, capture_output=True).returncode == 2
