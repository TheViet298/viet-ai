"""Regression checks for missing captures, duplicate recovery and batch loss."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))

import ai_log_store as store
import log_antigravity
import log_codex
import submit_log


class CaptureTests(unittest.TestCase):
    def test_antigravity_captures_prompt_tools_and_final_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'transcript.jsonl'
            records = [
                {'type':'USER_INPUT','source':'USER_EXPLICIT','step_index':0,
                 'created_at':'2026-10-04T00:00:00Z','content':'<USER_REQUEST>Xin chào</USER_REQUEST>'},
                {'type':'PLANNER_RESPONSE','source':'MODEL','step_index':1,
                 'created_at':'2026-10-04T00:00:01Z','content':'private reasoning',
                 'tool_calls':[{'name':'run_command','args':{'Cwd':'K:\\vinai\\P-142','CommandLine':'git status'}}]},
                {'type':'GENERIC','source':'MODEL','step_index':2,
                 'created_at':'2026-10-04T00:00:02Z','content':'private tool output'},
                {'type':'PLANNER_RESPONSE','source':'MODEL','status':'DONE','step_index':3,
                 'created_at':'2026-10-04T00:00:03Z','content':'Đã hoàn thành.'},
            ]
            path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
            entries=list(log_antigravity.activity_entries(path,'conversation',None,
                ('P-142','main','1234567','synthetic')))
            self.assertEqual([e['event'] for e in entries],['UserPrompt'])
            self.assertNotIn('private reasoning',json.dumps(entries))
            self.assertNotIn('private tool output',json.dumps(entries))
            self.assertEqual(entries[0]['prompt'],'Xin chào')

    def test_ingestion_tool_payloads_are_lossless_strings(self):
        entry = {'tool_input': {'question': 'pin'}, 'tool_response': [{'text': 'Đã kiểm tra'}]}
        wire = submit_log.wire_entry(entry)
        for key in entry:
            self.assertEqual(json.loads(wire[key]), entry[key])
        self.assertIsInstance(entry['tool_response'], list)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.context = {'origin': 'https://example.invalid/team/P-142.git', 'repo': 'P-142',
                        'student': 'synthetic', 'branch': 'feature/test', 'commit': '1234567'}

    def transcript(self, payloads, cwd=None):
        path = self.root / 'rollout.jsonl'
        rows = [{'type': 'session_meta', 'payload': {'id': 'session-test', 'cwd': str(cwd or self.root)}}]
        rows += [{'type': 'turn_context', 'payload': {'turn_id': 'turn-test', 'model': 'model-test'}}]
        rows += [{'type': 'response_item', 'timestamp': '2026-09-30T04:00:00Z', 'payload': d} for d in payloads]
        path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
        return path

    def message(self, role, body, identifier='msg-1', phase=None):
        return {'type': 'message', 'id': identifier, 'role': role, 'phase': phase,
                'content': [{'type': 'input_text' if role == 'user' else 'output_text', 'text': body}],
                'internal_chat_message_metadata_passthrough': {'turn_id': 'turn-test'}}

    def test_full_unicode_prompt_public_responses_and_excluded_private_records(self):
        prompt = 'Chăm sóc khách hàng và pin. ' * 200
        path = self.transcript([
            self.message('user', '<environment_context>environment only</environment_context>', 'env'),
            self.message('user', prompt), self.message('developer', 'private instructions', 'dev'),
            {'type': 'reasoning', 'summary': 'private reasoning'},
            self.message('assistant', 'Đang kiểm tra dữ liệu.', 'comment', 'commentary'),
            self.message('assistant', 'Đã xử lý.', 'final', 'final_answer'),
            {'type': 'custom_tool_call', 'call_id': 'call-1', 'name': 'functions.exec', 'input': 'text("activity")'},
            {'type': 'custom_tool_call_output', 'call_id': 'call-1', 'output': 'activity'},
        ])
        with path.open('a') as out:
            out.write(json.dumps({'type': 'event_msg', 'payload': {'type': 'turn_aborted', 'turn_id': 'turn-test'}}) + '\n')
            out.write('{"incomplete":')
        entries = log_codex.transcript_entries(path, self.root, self.context)
        self.assertEqual(next(e['prompt'] for e in entries if e['event'] == 'UserPrompt'), prompt)
        self.assertEqual({e['event'] for e in entries}, {'UserPrompt'})
        self.assertNotIn('private instructions', json.dumps(entries))
        self.assertNotIn('private reasoning', json.dumps(entries))

    def test_other_project_is_not_exported(self):
        path = self.transcript([self.message('user', 'Other project')], cwd=str(self.root) + '-other')
        self.assertEqual(log_codex.transcript_entries(path, self.root, self.context), [])

    def test_legacy_event_format_and_new_message_mirror_not_duplicated(self):
        path = self.transcript([self.message('user', 'Same user prompt')])
        with path.open('a') as out:
            out.write(json.dumps({'type':'event_msg','payload':{'type':'user_message','turn_id':'turn-test','message':'Same user prompt'}})+'\n')
            out.write(json.dumps({'type':'event_msg','payload':{'type':'user_message','turn_id':'turn-old','message':'Legacy prompt'}})+'\n')
        entries = log_codex.transcript_entries(path, self.root, self.context)
        self.assertEqual([e['prompt'] for e in entries], ['Same user prompt','Legacy prompt'])

    def test_repeated_identical_prompts_remain_distinct_and_archive_dedup_is_idempotent(self):
        path = self.transcript([self.message('user','Again','a'), self.message('user','Again','b')])
        entries = log_codex.transcript_entries(path, self.root, self.context)
        directory = self.root / '.ai-log'
        directory.mkdir()
        # Old logs lack entry_id/turn_id. One old prompt is already submitted.
        (directory/'archive').mkdir()
        (directory/'archive/2026-09-30.jsonl').write_text(json.dumps({'tool':'codex','session_id':'session-test','prompt':'Again'})+'\n')
        self.assertEqual(store.append_entries(directory, entries), 1)
        self.assertEqual(store.append_entries(directory, entries), 0)
        self.assertEqual(len((directory/'session.jsonl').read_text().splitlines()), 1)

    def test_secret_values_redacted_without_truncating_the_prompt(self):
        secret = 'synthetic-secret-value-123456'
        with patch.dict(os.environ, {'AI_LOG_API_KEY':secret}):
            result = store.redact({'prompt':'Dữ liệu '+secret+' tiếp tục '*300, 'tool_input':{'password':'never upload'}})
        self.assertNotIn(secret, json.dumps(result))
        self.assertTrue(result['prompt'].endswith(' tiếp tục '*300))
        self.assertEqual(result['tool_input']['password'], '[REDACTED]')

    def test_concurrent_recovery_does_not_duplicate_entries(self):
        directory = self.root / '.ai-log'
        code = ('import sys; sys.path.insert(0,sys.argv[1]); from ai_log_store import append_entries; '
                'append_entries(sys.argv[2],[{"entry_id":"parallel","tool":"codex","prompt":"test"}])')
        children = [subprocess.Popen([sys.executable,'-c',code,str(SCRIPTS),str(directory)]) for _ in range(4)]
        for child in children:
            self.assertEqual(child.wait(timeout=10), 0)
        self.assertEqual(len((directory/'session.jsonl').read_text().splitlines()), 1)

    def test_native_prompt_hook_writes_full_prompt_and_only_json_to_stdout(self):
        directory = self.root / '.ai-log'
        prompt = 'Câu hỏi dài. '*200
        payload = {'hook_event_name':'UserPromptSubmit','session_id':'native-test','turn_id':'turn-test','prompt':prompt}
        result = subprocess.run([sys.executable,str(SCRIPTS/'log_hook.py'),'--tool=codex'],
            input=json.dumps(payload),text=True,capture_output=True,
            cwd=SCRIPTS.parent,env={**os.environ,'AI_LOG_DIR':str(directory)},timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{})
        logged_entry = json.loads((directory/'session.jsonl').read_text(encoding='utf-8'))
        self.assertEqual(logged_entry['prompt'],prompt)
        self.assertEqual(logged_entry['event'],'UserPrompt')


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.path = self.directory/'session.jsonl'
        for name,value in {'LOG_DIR':self.directory,'LOG_FILE':self.path,'ARCHIVE_DIR':self.directory/'archive',
                           'SERVER_URL':'https://example.invalid/api/ingest','API_KEY':'synthetic','BATCH_LIMIT':2}.items():
            patcher = patch.object(submit_log,name,value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def write(self, values):
        self.path.write_text(''.join(json.dumps({'entry_id':str(v),'prompt':str(v)})+'\n' for v in values))

    def read(self, path):
        return [json.loads(l)['entry_id'] for l in path.read_text().splitlines()]

    def response(self):
        response=MagicMock()
        response.status=202
        response.read.return_value=b'{"accepted":true}'
        response.__enter__.return_value=response
        return response

    def archived(self):
        return [entry for path in (self.directory/'archive').glob('*.jsonl') for entry in self.read(path)]

    def test_only_sent_batch_archived_and_concurrent_events_preserved(self):
        self.write(range(5))
        def send(request, timeout):
            self.assertEqual(len(json.loads(request.data)['entries']),2)
            store.append_entries(self.directory,[{'entry_id':'new','prompt':'new'}])
            return self.response()
        with patch.object(submit_log.urllib.request,'urlopen',side_effect=send):
            self.assertTrue(submit_log.submit_all(False))
        self.assertEqual(self.archived(),['0','1'])
        self.assertEqual(self.read(self.path),['2','3','4','new'])

    def test_all_batches_drain_without_duplicate_archive_records(self):
        self.write(range(5))
        with patch.object(submit_log.urllib.request,'urlopen',return_value=self.response()) as send:
            self.assertTrue(submit_log.submit_all())
        self.assertEqual(send.call_count,3)
        self.assertEqual(self.archived(),['0','1','2','3','4'])
        self.assertFalse(self.path.exists())

    def test_failed_post_restores_entire_batch_and_live_events(self):
        self.write(range(5))
        def fail(*args,**kwargs):
            store.append_entries(self.directory,[{'entry_id':'new','prompt':'new'}])
            raise urllib.error.URLError('synthetic outage')
        with patch.object(submit_log.urllib.request,'urlopen',side_effect=fail):
            self.assertFalse(submit_log.submit_all())
        self.assertEqual(self.read(self.path),['0','1','2','3','4','new'])
        self.assertEqual(self.archived(),[])

    def test_interrupted_upload_recovered_and_invalid_record_not_discarded(self):
        pending=self.directory/'session.pending.old.jsonl'
        pending.write_text('{"entry_id":"old","prompt":"old"}\ninvalid json\n')
        self.write(['new'])
        with patch.object(submit_log.urllib.request,'urlopen') as send:
            self.assertFalse(submit_log.submit_all())
        self.assertFalse(send.called)
        self.assertIn('invalid json',self.path.read_text())
        self.assertIn('new',self.path.read_text())
        self.assertEqual(self.archived(),[])


if __name__ == '__main__':
    unittest.main()
