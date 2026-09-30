#!/usr/bin/env python3
"""Capture this repository's saved Codex activity; never export reasoning/system context.

Native hooks are the primary path. --auto is an idempotent pre-push recovery
path. --watch --submit also covers an already running session whose hook
definitions have not been reloaded/reviewed yet.
"""
import argparse
import json
import os
import sys
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ai_log_store import append_entries, entry_id, locked, log_dir, repo_root


def text_content(content):
    if isinstance(content, str):
        return content
    return '\n'.join(part.get('text', '') for part in content or []
                     if isinstance(part, dict) and part.get('type') in {'input_text', 'output_text', 'text'})


def read_records(path):
    with path.open(encoding='utf-8') as stream:
        for number, line in enumerate(stream, 1):
            try:
                value = json.loads(line)
            except ValueError:
                # A running Codex process may not have completed its last line.
                # It remains in the source transcript and is retried next time.
                continue
            if isinstance(value, dict):
                yield number, value


def _url_key(url):
    return str(url or '').removesuffix('.git').rstrip('/').replace('git@github.com:', 'https://github.com/').casefold()


def in_scope(meta, root, origin):
    cwd = meta.get('cwd')
    if cwd:
        try:
            if Path(cwd).resolve().is_relative_to(root):
                return True
        except (OSError, ValueError):
            pass
    remote = (meta.get('git') or {}).get('repository_url')
    return bool(remote and origin and _url_key(remote) == _url_key(origin))


def transcript_entries(path, root, context):
    records = list(read_records(path))
    if not records:
        return []
    meta = next((r.get('payload', {}) for _, r in records if r.get('type') == 'session_meta'), {})
    if not in_scope(meta, root, context.get('origin', '')):
        return []
    session = meta.get('id') or meta.get('session_id') or path.stem
    git_meta = meta.get('git') or {}
    models, directories = {}, {}
    for _, r in records:
        if r.get('type') == 'turn_context':
            d = r.get('payload', {})
            models[d.get('turn_id', '')] = d.get('model', '')
            directories[d.get('turn_id', '')] = d.get('cwd')
    # Newer transcripts duplicate public messages in item_completed or event_msg.
    # response_item is authoritative when available for the same turn/text.
    primary = set()
    for _, r in records:
        d = r.get('payload', {})
        if r.get('type') == 'response_item' and d.get('type') == 'message':
            md = d.get('internal_chat_message_metadata_passthrough') or {}
            primary.add((d.get('role'), md.get('turn_id', ''), text_content(d.get('content'))))
    result, current_turn, current_model = [], '', ''
    for number, r in records:
        d = r.get('payload', {})
        if not isinstance(d, dict):
            continue
        if r.get('type') == 'turn_context':
            current_turn = d.get('turn_id', current_turn)
            current_model = d.get('model', current_model)
            continue
        if r.get('type') == 'event_msg' and d.get('type') == 'task_started':
            current_turn = d.get('turn_id', current_turn)
            continue
        md = d.get('internal_chat_message_metadata_passthrough') or {}
        turn = md.get('turn_id') or d.get('turn_id') or current_turn
        cwd = directories.get(turn)
        # Do not export a later turn that explicitly moved to an unrelated repo.
        if cwd and not in_scope({'cwd': cwd}, root, ''):
            # A different worktree of the same repository is still in scope.
            # An explicit turn in another repository is not.
            try:
                turn_root = repo_root(cwd)
                if _url_key(repo_context(turn_root)['origin']) != _url_key(context['origin']):
                    continue
            except (OSError, ValueError, subprocess.CalledProcessError):
                continue
        row = {
            'ts': r.get('timestamp') or meta.get('timestamp') or datetime.now(timezone.utc).isoformat(),
            'tool': 'codex', 'session_id': session, 'turn_id': turn,
            'model': models.get(turn) or current_model,
            'repo': context['repo'], 'student': context['student'],
            'branch': git_meta.get('branch', context['branch']),
            'commit': git_meta.get('commit_hash', context['commit'])[:7],
            'git_context_source': 'session_start', 'capture_method': 'transcript',
            'transcript_path': str(path),
        }
        identifier = d.get('id') or d.get('call_id') or f'{number}:{r.get("timestamp", "")}'
        if r.get('type') == 'response_item':
            kind = d.get('type')
            if kind == 'message':
                text = text_content(d.get('content'))
                if not text or d.get('channel') == 'analysis' or d.get('phase') == 'analysis':
                    continue
                if d.get('role') == 'user':
                    if text.lstrip().startswith('<environment_context>'):
                        continue
                    row.update(event='UserPromptSubmit', prompt=text)
                elif d.get('role') == 'assistant':
                    event = 'Stop' if d.get('phase') == 'final_answer' else 'AssistantMessage'
                    row.update(event=event, response=text, response_summary=text[:500])
                else:
                    continue
            elif kind in {'function_call', 'custom_tool_call'}:
                identifier = d.get('call_id') or identifier
                row.update(event='PreToolUse', tool_name=d.get('name', ''),
                           tool_use_id=d.get('call_id', ''), tool_input=d.get('arguments', d.get('input')))
            elif kind in {'function_call_output', 'custom_tool_call_output'}:
                identifier = d.get('call_id') or identifier
                row.update(event='PostToolUse', tool_use_id=d.get('call_id', ''), tool_response=d.get('output'))
            else:
                continue  # reasoning, developer/system messages, encrypted state
        elif r.get('type') == 'event_msg':
            kind = d.get('type')
            if kind in {'user_message', 'agent_message'}:
                text = d.get('message', '')
                role = 'user' if kind == 'user_message' else 'assistant'
                if not text or (role, turn, text) in primary:
                    continue
                if role == 'user':
                    if text.lstrip().startswith('<environment_context>'):
                        continue
                    row.update(event='UserPromptSubmit', prompt=text)
                else:
                    row.update(event='AssistantMessage', response=text, response_summary=text[:500])
            elif kind == 'turn_aborted':
                row.update(event='Interrupt', activity='Turn interrupted')
            elif kind == 'item_completed' and isinstance(d.get('item'), dict):
                item = d['item']
                if item.get('type') not in {'CommandExecution', 'FileChange', 'WebSearch', 'McpToolCall', 'DynamicToolCall'}:
                    continue
                identifier = item.get('id') or identifier
                row.update(event='ToolActivity', tool_name=item['type'], activity=item)
            else:
                continue
        else:
            continue
        row['entry_id'] = entry_id(session, row['event'], identifier)
        result.append(row)
    return result


def repo_context(root):
    import subprocess
    def git(*args):
        try:
            return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.DEVNULL).strip()
        except subprocess.CalledProcessError:
            return ''
    return {'origin': git('remote', 'get-url', 'origin'), 'repo': root.name,
            'student': git('config', 'user.email'), 'branch': git('branch', '--show-current'),
            'commit': git('rev-parse', '--short', 'HEAD')}


def capture(root, paths=None, dry_run=False):
    context = repo_context(root)
    if not context['origin']:
        raise ValueError('No repository origin; refusing unscoped transcript capture')
    if paths is None:
        home = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))
        paths = sorted({p for folder in ['sessions', 'archived_sessions']
                        for p in (home / folder).rglob('*.jsonl')})
    entries = []
    matched = 0
    for path in paths:
        # Filter on the header before reading another project's conversation.
        first = next(read_records(path), None)
        if not first or first[1].get('type') != 'session_meta':
            continue
        if not in_scope(first[1].get('payload', {}), root, context['origin']):
            continue
        matched += 1
        entries.extend(transcript_entries(path, root, context))
    if dry_run:
        print(json.dumps({'scoped_sessions': matched, 'events': dict(Counter(e['event'] for e in entries)),
                          'total_records': len(entries)}))
        return 0
    count = append_entries(log_dir(root), entries)
    if count:
        print(f'[codex-log] Captured {count} new activity records from {matched} repo-scoped sessions.', file=sys.stderr)
    return count


def watch(root, interval, submit):
    directory = log_dir(root)
    try:
        with locked(directory, '.watch.lock', blocking=False):
            (directory / 'codex-watch.pid').write_text(str(os.getpid()), encoding='ascii')
            print('[codex-log] Background capture started for ' + str(root), file=sys.stderr, flush=True)
            last_submit = 0
            while True:
                try:
                    capture(root)
                    if submit and time.monotonic() - last_submit >= 15:
                        from submit_log import submit_all
                        submit_all()
                        last_submit = time.monotonic()
                except (OSError, ValueError) as error:
                    print(f'[codex-log] Capture retry required: {type(error).__name__}', file=sys.stderr, flush=True)
                time.sleep(interval)
    except (BlockingIOError, PermissionError):
        print('[codex-log] A repository capture watcher is already running.', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--auto', action='store_true', help='Recover all saved activity for this repository')
    parser.add_argument('--transcript', type=Path)
    parser.add_argument('--dry-run', action='store_true', help='Print counts only; never print conversations')
    parser.add_argument('--watch', action='store_true', help='Continue capturing while this process runs')
    parser.add_argument('--submit', action='store_true', help='Submit pending logs periodically in watch mode')
    parser.add_argument('--interval', type=float, default=3)
    args = parser.parse_args()
    root = repo_root()
    if args.watch:
        watch(root, max(1, args.interval), args.submit)
    else:
        capture(root, [args.transcript] if args.transcript else None, args.dry_run)


if __name__ == '__main__':
    main()
