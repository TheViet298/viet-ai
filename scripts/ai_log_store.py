"""Shared, private AI-log storage and locking (standard library only)."""
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from contextlib import contextmanager
from pathlib import Path


def repo_root(cwd=None):
    return Path(subprocess.check_output(
        ['git', '-C', str(cwd or Path.cwd()), 'rev-parse', '--show-toplevel'],
        text=True, stderr=subprocess.DEVNULL,
    ).strip()).resolve()


def load_env(root):
    path = Path(root) / '.env'
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line.startswith('export '):
            line = line[7:].lstrip()
        key, sep, value = line.partition('=')
        if not sep or not key or key.startswith('#'):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        else:
            value = value.split(' #', 1)[0].rstrip()
        os.environ.setdefault(key.strip(), value)


def log_dir(root):
    load_env(root)
    path = Path(os.environ.get('AI_LOG_DIR', '.ai-log'))
    return path if path.is_absolute() else Path(root) / path


@contextmanager
def locked(directory, name='.capture.lock', blocking=True):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    fd = os.open(directory / name, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, 'r+b') as stream:
        acquired = False
        try:
            if os.name == 'nt':
                import msvcrt
                if os.fstat(stream.fileno()).st_size == 0:
                    stream.write(b'0')
                    stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            acquired = True
            yield
        finally:
            if acquired:
                if os.name == 'nt':
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)


def entry_id(session, event, identifier):
    raw = json.dumps([session, event, identifier], ensure_ascii=False, sort_keys=True)
    return 'codex:' + hashlib.sha256(raw.encode('utf-8')).hexdigest()


def redact(value):
    secrets = [v for k, v in os.environ.items()
               if len(v) >= 8 and re.search(r'(API_KEY|ACCESS_TOKEN|REFRESH_TOKEN|PASSWORD|SECRET)$', k)]

    def clean(item):
        if isinstance(item, str):
            for secret in secrets:
                item = item.replace(secret, '[REDACTED]')
            return re.sub(r'\b(?:sk-(?:proj-|svcacct-)?|ghp_|github_pat_)[A-Za-z0-9_-]{16,}', '[REDACTED]', item)
        if isinstance(item, dict):
            return {k: '[REDACTED]' if re.fullmatch(
                r'(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|authorization|secret)', k, re.I
            ) else clean(v) for k, v in item.items()}
        if isinstance(item, list):
            return [clean(v) for v in item]
        return item
    return clean(value)


def _semantic(row):
    if row.get('tool') != 'codex':
        return None
    if row.get('prompt') and not row.get('tool_name'):
        return (row.get('session_id', ''), 'prompt', row.get('turn_id', ''), row['prompt'])
    if row.get('response'):
        return (row.get('session_id', ''), 'response', row.get('turn_id', ''), row['response'])
    return None


def append_entries(directory, entries):
    """Deduplicate native hooks, transcript sweeps and already submitted archives."""
    entries = [redact(e) for e in entries]
    if not entries:
        return 0
    with locked(directory):
        paths = [Path(directory) / 'session.jsonl']
        paths += sorted(Path(directory).glob('session.pending.*.jsonl'))
        paths += sorted((Path(directory) / 'archive').glob('*.jsonl'))
        ids, legacy = set(), Counter()
        for path in paths:
            if not path.exists():
                continue
            with path.open(encoding='utf-8') as stream:
                for line in stream:
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    if row.get('entry_id'):
                        ids.add(row['entry_id'])
                    if row.get('capture_method') != 'transcript':
                        key = _semantic(row)
                        if key:
                            legacy[key] += 1
        new = []
        for row in entries:
            key = _semantic(row)
            # Consume legacy/native matches in transcript order, so repeated
            # identical user prompts still retain their separate message IDs.
            legacy_key = key
            if key and not legacy[key]:
                legacy_key = (key[0], key[1], '', key[3])
            if row.get('capture_method') == 'transcript' and legacy_key and legacy[legacy_key]:
                legacy[legacy_key] -= 1
                if row.get('entry_id'):
                    ids.add(row['entry_id'])
                continue
            if row.get('entry_id') and row['entry_id'] in ids:
                continue
            if row.get('entry_id'):
                ids.add(row['entry_id'])
            new.append(row)
        if new:
            fd = os.open(Path(directory) / 'session.jsonl', os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
            with os.fdopen(fd, 'a', encoding='utf-8') as stream:
                for row in new:
                    stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        return len(new)
