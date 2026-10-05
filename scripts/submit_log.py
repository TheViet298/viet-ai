#!/usr/bin/env python3
"""Submit private AI logs in batches; archive only acknowledged records.

Capture and submission use separate locks: new hook events can be recorded
while the POST is in flight. Failed batches are restored for the next retry.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from ai_log_store import locked, log_dir, redact, repo_root

try:
    ROOT = repo_root()
except (OSError, subprocess.CalledProcessError):
    ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = log_dir(ROOT)
SERVER_URL = os.environ.get('AI_LOG_SERVER', '')
API_KEY = os.environ.get('AI_LOG_API_KEY', '')
LOG_FILE = LOG_DIR / 'session.jsonl'
ARCHIVE_DIR = LOG_DIR / 'archive'
BATCH_LIMIT = 500
BATCH_BYTES = 256 * 1024


def wire_entry(entry):
    """The ingestion API requires tool payload fields to be strings."""
    row = dict(entry)
    for key in ('tool_input', 'tool_response'):
        if key in row and not isinstance(row[key], str):
            row[key] = json.dumps(row[key], ensure_ascii=False)
    return row


def _restore_pending(pending):
    if not pending.exists():
        return
    if LOG_FILE.exists():
        tmp = LOG_DIR / f'session.merge.{time.time_ns()}.jsonl'
        with tmp.open('wb') as out:
            for path in (pending, LOG_FILE):
                with path.open('rb') as source:
                    shutil.copyfileobj(source, out)
        os.replace(tmp, LOG_FILE)
        pending.unlink()
    else:
        pending.rename(LOG_FILE)


def _archive(lines):
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    fd = os.open(ARCHIVE_DIR / f'{today}.jsonl', os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
    with os.fdopen(fd, 'a', encoding='utf-8') as target:
        target.writelines(lines)


def _receipt(status, count, body):
    try:
        response = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        response = {'body_available': bool(body)}
    record = redact({'ts': datetime.now(timezone.utc).isoformat(), 'status_code': status,
                     'submitted': count, 'response': response})
    fd = os.open(LOG_DIR / 'receipts.jsonl', os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
    with os.fdopen(fd, 'a', encoding='utf-8') as out:
        out.write(json.dumps(record, ensure_ascii=False) + '\n')


def _submit_one():
    with locked(LOG_DIR):
        if not LOG_FILE.exists() or not LOG_FILE.stat().st_size:
            return 0, True
        pending = LOG_DIR / f'session.pending.{os.getpid()}.{time.time_ns()}.jsonl'
        LOG_FILE.rename(pending)
    lines, entries = [], []
    invalid_line = None
    with pending.open(encoding='utf-8') as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if not isinstance(entry, dict):
                    raise ValueError('Expected an object')
            except ValueError:
                invalid_line = number
                break
            lines.append(line if line.endswith('\n') else line + '\n')
            entries.append(entry)
    if invalid_line is not None:
        with locked(LOG_DIR):
            _restore_pending(pending)
        print(f'[ai-log] Invalid JSON record at line {invalid_line}; all logs kept locally.', file=sys.stderr)
        return 0, False
    if not entries:
        pending.unlink()
        return 0, True
    count, size = 0, 0
    for entry in entries[:BATCH_LIMIT]:
        length = len(json.dumps(entry, ensure_ascii=False).encode('utf-8'))
        if count and size + length > BATCH_BYTES:
            break
        size += length
        count += 1
    try:
        request = urllib.request.Request(SERVER_URL,
            data=json.dumps({'entries': [wire_entry(e) for e in entries[:count]]}, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {API_KEY}'}, method='POST')
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status, body = response.status, response.read(65536)
                    if not 200 <= status < 300:
                        raise ValueError('Unexpected response status')
                break
            except urllib.error.HTTPError as error:
                if error.code != 429 or attempt == 3:
                    raise
                retry_after = error.headers.get('Retry-After', '')
                try:
                    delay = min(60, max(1, float(retry_after)))
                except ValueError:
                    delay = 5 * (attempt + 1)
                print(f'[ai-log] Rate limited; retrying in {delay:g}s.', file=sys.stderr)
                time.sleep(delay)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        with locked(LOG_DIR):
            _restore_pending(pending)
        code = getattr(error, 'code', None)
        detail = f'HTTP {code}' if code else type(error).__name__
        print(f'[ai-log] Submit failed ({detail}); logs kept locally.', file=sys.stderr)
        return 0, False
    with locked(LOG_DIR):
        _archive(lines[:count])
        if count < len(lines):
            pending.write_text(''.join(lines[count:]), encoding='utf-8')
            _restore_pending(pending)
        else:
            pending.unlink()
        _receipt(status, count, body)
    print(f'[ai-log] Submitted {count} entries → {status}', file=sys.stderr)
    return count, True


def submit_all(all_batches=True):
    if not SERVER_URL or not API_KEY:
        print('[ai-log] AI_LOG_SERVER or AI_LOG_API_KEY not set; logs kept locally.', file=sys.stderr)
        return False
    with locked(LOG_DIR, '.submission.lock'):
        # Recover batches left by a terminated uploader before taking a new one.
        with locked(LOG_DIR):
            for pending in sorted(LOG_DIR.glob('session.pending.*.jsonl'), reverse=True):
                _restore_pending(pending)
        total = 0
        while True:
            count, success = _submit_one()
            if not success:
                return False
            total += count
            if not count or not all_batches:
                break
        if not total:
            print('[ai-log] No logs to submit.', file=sys.stderr)
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true', help='Drain every pending batch instead of only the first')
    args = parser.parse_args()
    return 0 if submit_all(args.all) else 1


if __name__ == '__main__':
    sys.exit(main())
