import json
import subprocess
import sys


def test_engineering_runner_checks_real_failures():
    from eval.rag_engineering import run_engineering
    result = run_engineering()
    assert result['passed']
    assert result['production_acceptance'] is False
    assert {'wrong_model', 'wrong_variant', 'unsafe', 'budget', 'negation', 'wrong_number', 'parent'} <= set(result['checks'])


def test_engineering_failure_returns_nonzero(monkeypatch, tmp_path):
    from eval import rag_engineering
    from scripts.check_rag_quality import main
    monkeypatch.setattr(rag_engineering, 'run_engineering', lambda: {
        'passed': False, 'production_acceptance': False, 'gate_kind': 'engineering', 'failure_reasons': ['wrong_model']})
    assert main(['--engineering', '--output', str(tmp_path / 'report.json')]) == 1


def test_engineering_cli_without_private_data(tmp_path):
    output = tmp_path / 'report.json'
    result = subprocess.run([sys.executable, 'scripts/check_rag_quality.py', '--engineering', '--output', str(output)], capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding='utf-8'))['production_acceptance'] is False
