"""Run ten bridge/API acceptance regressions separately from single-turn eval."""
import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = [
    ('fact_correction_4_models', 'tests/test_agents/test_multiturn_quality.py', 4),
    ('two_clarification_limit', 'tests/test_agents/test_complete_agent.py::test_session_retains_facts_and_enforces_two_turns', 1),
    ('guest_quota_and_emergency', 'tests/test_api/test_graph_api_bridge.py::test_guest_quota_cannot_be_reset_with_request_session', 1),
    ('staff_in_progress', 'tests/test_agents/test_complete_agent.py::test_customer_update_preserves_staff_workflow_status', 1),
    ('explicit_old_case', 'tests/test_api/test_graph_api_bridge.py::test_explicit_old_case_is_rejected_instead_of_writing_to_current_case', 1),
    ('ownership', 'tests/test_api/test_graph_api_bridge.py::test_customer_case_is_saved_and_private', 1),
    ('storage_failure_emergency', 'tests/test_api/test_graph_api_bridge.py::test_emergency_alert_survives_storage_unavailability', 1),
]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')
    result = subprocess.run([sys.executable, '-m', 'pytest', *(s[1] for s in SCENARIOS), '-q', '-p', 'no:cacheprovider', f'--basetemp=.test-runs/multiturn-{stamp}'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (args.output_dir / 'pytest-output.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
    report = {'total_scenarios': sum(s[2] for s in SCENARIOS), 'exit_code': result.returncode, 'passed': result.returncode == 0, 'mode': 'offline-regression', 'scope': 'Real bridge/API and isolated SQLite; network disabled, storage failure injected. Six existing regressions and four new model-correction conversations; not an unseen holdout.', 'groups': [{'name': s[0], 'node_id': s[1], 'cases': s[2]} for s in SCENARIOS]}
    (args.output_dir / 'multiturn_results.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(result.stdout)
    sys.exit(result.returncode)
