import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import gps_agent_workflow as workflow
import setup_gps_agent_permissions as permissions

READY = {'status': 'ready', 'plan': 'GPS scope: consent, watch cleanup, manual fallback. ' * 4, 'blockers': []}
COMPLETE = {'status': 'complete', 'summary': 'Changed GPS only', 'tests': [], 'blockers': []}
PASS = {'verdict': 'pass', 'findings': []}
FAIL = {'verdict': 'fail', 'findings': ['src/location: clear watch on unmount']}


class ValidationTests(unittest.TestCase):
    def test_changed_configuration_is_rejected_before_verification(self):
        with patch.object(workflow, 'git', return_value='.codex/config.toml\n'):
            with self.assertRaises(workflow.WorkflowError):
                workflow.review_context(Path('/unused'))

    def test_untracked_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / 'frontend').mkdir()
            (repo / 'frontend/leak').symlink_to('/etc/passwd')
            with patch.object(workflow, 'git', side_effect=['', '', 'frontend/leak\n']):
                with self.assertRaises(workflow.WorkflowError):
                    workflow.review_context(repo)

    def test_verifier_continues_after_timeout_and_returns_failure(self):
        original = Path(__file__).resolve().parents[2] / 'scripts/verify-gps.sh'
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / 'scripts').mkdir()
            (repo / 'bin').mkdir()
            (repo / 'frontend/node_modules/.bin').mkdir(parents=True)
            verifier = repo / 'scripts/verify-gps.sh'
            verifier.write_text(original.read_text())
            log = repo / 'calls'
            for name in ('npm', 'node', 'python'):
                stub = repo / 'bin' / name
                stub.write_text('#!/bin/bash\necho "' + name + ' $*" >> "$GPS_TEST_CALLS"\n' +
                                ('if [[ "$*" == *lint* ]]; then /bin/sleep 2; fi\n' if name == 'npm' else ''))
                stub.chmod(0o700)
            tsc = repo / 'frontend/node_modules/.bin/tsc'
            tsc.write_text('#!/bin/bash\necho tsc >> "$GPS_TEST_CALLS"\n')
            tsc.chmod(0o700)
            env = dict(os.environ, PATH=str(repo / 'bin') + ':' + os.environ['PATH'],
                       PYTHON=str(repo / 'bin/python'), GPS_CHECK_TIMEOUT_SECONDS='1', GPS_TEST_CALLS=str(log))
            result = subprocess.run(['bash', str(verifier)], env=env, text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertIn('exit 124', result.stderr)
            self.assertEqual(len(log.read_text().splitlines()), 7)
            self.assertIn('PASS: Frontend build', result.stdout)

    def test_soft_denial_success_is_rejected(self):
        raw = json.dumps({'status': 'SUCCESS', 'structured_output': PASS, 'denied_actions': ['command(test)']})
        with self.assertRaises(workflow.WorkflowError):
            workflow.agy_result(raw, '', workflow.REVIEW)

    def test_timeout_success_is_rejected(self):
        raw = json.dumps({'status': 'SUCCESS', 'structured_output': PASS})
        with self.assertRaises(workflow.WorkflowError):
            workflow.agy_result(raw, '[agy] print timeout with turn in progress', workflow.REVIEW)

    def test_missing_output_blocked_and_contradictions_are_rejected(self):
        for value in (None, {'verdict': 'fail', 'findings': []},
                      {'verdict': 'blocked', 'findings': ['API choice']}):
            with self.subTest(value=value), self.assertRaises(workflow.WorkflowError):
                workflow.validate(value, workflow.REVIEW)

    def test_pass_with_informational_findings_matches_review_contract(self):
        value = {'verdict': 'pass', 'findings': ['Research is ready; no blocking issue found']}
        raw = json.dumps({'status': 'SUCCESS', 'structured_output': value})
        self.assertEqual(workflow.agy_result(raw, '', workflow.REVIEW), value)

    def test_real_subprocess_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(workflow.WorkflowError):
                workflow.run_process([sys.executable, '-c', 'import time; time.sleep(60)'],
                                     directory, Path(directory) / 'timeout', 0.05)

    def test_permissions_preserve_existing_and_are_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            original = {'other': {'keep': True}, 'permissions': {'allow': ['command(ls)'], 'deny': ['command(sudo)']}}
            path.write_text(json.dumps(original))
            with contextlib.redirect_stdout(io.StringIO()):
                permissions.configure(path, Path(directory), True)
                first = path.read_text()
                permissions.configure(path, Path(directory), True)
            self.assertEqual(first, path.read_text())
            updated = json.loads(first)
            self.assertEqual(updated['other'], original['other'])
            self.assertEqual(updated['permissions']['deny'], ['command(sudo)'])
            self.assertNotIn('command(*)', updated['permissions']['allow'])


class HandoffTests(unittest.TestCase):
    def run_pipeline(self, reviews, dirty=False, smoke=False, verify_failure=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        repo = Path(directory.name)
        (repo / 'docs/gps_plans').mkdir(parents=True)
        (repo / 'scripts').mkdir()
        for name in ('AGENTS.md', 'docs/gps_plans/location-feature.md', 'scripts/verify-gps.sh'):
            (repo / name).touch()
        run_dir = repo / 'artifacts'
        run_dir.mkdir()
        def fake_git(_repo, *args):
            if args == ('status', '--porcelain'):
                return ' M existing.py\n' if dirty else ''
            if args == ('diff', '--cached', '--name-only'):
                return ''
            return 'feature/ai-khoi\n' if args[0] == 'branch' else 'HEAD\n'
        def verify(command, cwd, prefix, seconds, stdin=None):
            if verify_failure:
                raise workflow.WorkflowError('verify exit=124')
            prefix.with_suffix('.stdout').write_text('PASS: independent checks\n')
            return '', ''
        with patch.object(workflow.Path, 'cwd', return_value=repo), \
             patch.object(workflow.shutil, 'which', return_value='/fake/cli'), \
             patch.object(workflow, 'git', side_effect=fake_git), \
             patch.object(workflow.tempfile, 'mkdtemp', return_value=str(run_dir)), \
             patch.object(workflow.subprocess, 'run') as git_run, \
             patch.object(workflow, 'agy', side_effect=[READY, *reviews]) as agy, \
             patch.object(workflow, 'codex', return_value=COMPLETE) as codex, \
             patch.object(workflow, 'run_process', side_effect=verify), \
             patch.object(workflow, 'review_context', return_value='scoped diff'), \
             contextlib.redirect_stdout(io.StringIO()):
            git_run.return_value.stdout = 'origin/feature/ai-khoi\n'
            try:
                code = workflow.main(['--smoke'] if smoke else [])
            except workflow.WorkflowError:
                code = 1
        state = json.loads((run_dir / 'result.json').read_text()) if (run_dir / 'result.json').exists() else None
        return code, state, codex, agy

    def test_fail_feedback_reaches_codex_and_one_repair_passes(self):
        code, state, codex, agy = self.run_pipeline([FAIL, PASS])
        self.assertEqual(code, 0)
        self.assertEqual(state['repairs'], 1)
        self.assertEqual(codex.call_count, 2)
        self.assertIn(FAIL['findings'][0], codex.call_args_list[1].args[3])
        self.assertIn('PASS: independent checks', agy.call_args.args[3])

    def test_repair_limit_stops_after_second_failure(self):
        code, state, codex, _ = self.run_pipeline([FAIL, FAIL])
        self.assertEqual((code, state['status'], codex.call_count), (1, 'fail', 2))

    def test_verification_failure_never_calls_reviewer(self):
        code, state, codex, agy = self.run_pipeline([], verify_failure=True)
        self.assertEqual((code, state['status']), (1, 'blocked'))
        self.assertEqual(agy.call_count, 1)

    def test_dirty_workspace_never_starts_implementation(self):
        code, state, codex, agy = self.run_pipeline([], dirty=True)
        self.assertEqual(code, 1)
        self.assertIsNone(state)
        codex.assert_not_called()
        agy.assert_not_called()

    def test_smoke_passes_plan_and_critique_between_agents_read_only(self):
        code, state, codex, agy = self.run_pipeline([PASS], dirty=True, smoke=True)
        self.assertEqual((code, state['status']), (0, 'research_pass'))
        self.assertTrue(codex.call_args.args[-1])
        self.assertIn(READY['plan'], codex.call_args.args[3])
        self.assertIn(COMPLETE['summary'], agy.call_args.args[3])


if __name__ == '__main__':
    unittest.main()
