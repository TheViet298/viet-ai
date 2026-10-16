def test_matrix_has_ten_cases_and_session_pair():
    from scripts.langfuse_matrix_cases import matrix_cases
    cases = matrix_cases()
    assert len(cases) == 10
    assert {c['case_id'] for c in cases} == {f'LF-{n:02}' for n in range(1, 11)}
    assert cases[3]['session_group'] == cases[4]['session_group']
    assert cases[5]['kind'] == cases[6]['kind'] == 'upload'


def test_http_200_fallback_is_not_live_success():
    from scripts.langfuse_matrix_cases import evaluate_case
    assert evaluate_case('LF-01', 200, {'response': 'fallback'}, [])['status'] == 'BLOCKED'
    assert evaluate_case('LF-06', 200, {'data': {'detected_signals': {'analysis_error': 'inference_failed'}}}, [
        {'type': 'SPAN', 'isRootObservation': True, 'id': 'root'}])['status'] == 'BLOCKED'


def test_no_source_case_rejects_fabricated_citations():
    from scripts.langfuse_matrix_cases import evaluate_case
    root = {'id': 'root', 'type': 'SPAN', 'isRootObservation': True}
    assert evaluate_case('LF-03', 200, {'is_no_source': True, 'citations': [{'source_id': 'fake'}]}, [root])['status'] == 'FAIL'


def test_runner_imports_database_only_after_isolation(tmp_path):
    import json
    import subprocess
    import sys
    import shutil
    from uuid import uuid4
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    probe_dir = root / '.test-runs' / f'probe-{uuid4().hex[:8]}'
    try:
        result = subprocess.run([sys.executable, str(root / 'scripts/check_langfuse_matrix.py'),
                                 '--probe-isolation', '--output-dir', str(probe_dir)],
                                cwd=root, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr[-1000:]
        data = json.loads(result.stdout)
        for path in data.values():
            assert Path(path).resolve().is_relative_to(probe_dir.resolve())
    finally:
        if probe_dir.exists():
            shutil.rmtree(probe_dir, ignore_errors=True)


def test_validation_user_passes_real_upload_rbac(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from src.db import Base
    from src.services.auth import require_customer
    from scripts.check_langfuse_matrix import seed_validation_user
    engine = create_engine('sqlite:///' + (tmp_path / 'auth.db').as_posix())
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = seed_validation_user(db)
        assert require_customer(user).id == 'lf-synthetic-user'
    engine.dispose()


def test_completed_provider_with_parse_error_cannot_pass_live_case():
    from scripts.langfuse_matrix_cases import evaluate_case
    evidence = [{'id': 'r', 'type': 'SPAN', 'isRootObservation': True},
                {'id': 'g', 'type': 'GENERATION', 'endTime': 'now', 'level': 'DEFAULT'},
                {'id': 'o', 'name': 'llm.outcome', 'metadata': {'outcome': 'parse_error'}}]
    assert evaluate_case('LF-01', 200, {'response': 'fallback'}, evidence)['status'] == 'FAIL'


def test_live_chat_requires_application_parse_evidence():
    from scripts.langfuse_matrix_cases import evaluate_case
    evidence = [{'id': 'r', 'isRootObservation': True},
                {'id': 'g', 'type': 'GENERATION', 'endTime': 'now', 'level': 'DEFAULT'}]
    assert evaluate_case('LF-01', 200, {}, evidence)['status'] == 'BLOCKED'
