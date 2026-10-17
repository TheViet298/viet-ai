"""Reproducible API audit with an isolated synthetic account and database.

Offline measures routing/memory contracts, not grounded answer correctness.
Live uses the configured index/provider; it never modifies the serving DB.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_cases(dataset: dict, contexts: list[str]) -> list[dict]:
    cases = []
    for group in dataset['groups']:
        for index, question in enumerate(group['variants']):
            for context in contexts:
                warmup = ['Giá lăn bánh VF8 Plus tại Hà Nội?'] if context == 'after_quote' else []
                case = {**group, 'id': f'{group["id"]}-{index}-{context}', 'group': group['id'],
                        'context': context, 'turns': [*warmup, question]}
                case.update(group.get('expectations', {}).get(str(index), {}))
                # Bare model names are intentionally allowed to complete quote slots.
                case['forbid_quote'] = context == 'after_quote' and group['domain'] not in {'price', 'charging_network', 'scope'}
                cases.append(case)
    cases.extend({**case, 'group': case['id'], 'context': 'scenario'} for case in dataset['scenarios'])
    return cases


def check_contract(case: dict, row: dict) -> dict[str, bool]:
    data, context, turn = row.get('data') or {}, row.get('context') or {}, row.get('understanding') or {}
    checks = {'http': row.get('http_status') == 200, 'schema': bool(data.get('message'))}
    if not checks['schema']:
        return checks
    if 'goal' in case:
        checks['goal'] = context.get('active_goal') in case['goal']
    if case.get('cards'):
        checks['card_scope'] = bool(data.get('vehicle_cards')) == (case['cards'] == 'required')
    if case.get('kind'):
        checks['request_kind'] = (row.get('classification') or {}).get('request_kind') == case['kind']
    if 'emergency' in case:
        checks['emergency'] = (data.get('priority') == 'CRITICAL' and bool(data.get('show_emergency_banner'))) == case['emergency']
    elif case['domain'] not in {'incident', 'safety'}:
        checks['no_false_emergency'] = data.get('priority') != 'CRITICAL' and not data.get('show_emergency_banner')
    if case.get('forbid_quote'):
        checks['topic_switch'] = context.get('active_goal') != 'quote' and 'chi-phi-lan-banh' not in data['message']
    if case.get('move'):
        checks['move'] = turn.get('move') == case['move']
    if case.get('subject'):
        checks['subject'] = context.get('subject') == case['subject']
    for key, value in case.get('facts', {}).items():
        checks['fact_' + key] = (context.get('facts', {}).get(key) or {}).get('value') == value
    for key in case.get('unknown_facts', []):
        checks['unknown_' + key] = (context.get('facts', {}).get(key) or {}).get('status') == 'unknown'
    if case.get('no_completed_action'):
        progress = row.get('progress') or {}
        from src.services.conversation_context import normalized
        claimed = bool(re.search(r'(?:da dat lich thanh cong|lich da duoc xac nhan|da hoan tat dat lich)', normalized(data['message'])))
        checks['no_fabricated_action'] = bool(progress.get('action_receipt')) or (progress.get('state') != 'action_completed' and not claimed)
    if case.get('cost_subject') == 'charging':
        from src.services.chat_normalization import fold_text
        answer = fold_text(data['message'])
        checks['answer_cost_subject'] = not bool(re.search(
            r'gia (?:niem yet|cong bo|ban tu)|du toan lan banh', answer))
    return checks


async def audit(cases: list[dict], output: Path, mode: str) -> list[dict]:
    os.environ['DATABASE_URL'] = 'sqlite:///' + (output / 'audit.db').as_posix()
    os.environ['LANGFUSE_TRACING_ENABLED'] = 'false'
    if mode == 'offline':
        os.environ['AGENT_LLM_ENABLED'] = 'false'
        os.environ['CHROMA_PERSIST_DIR'] = str(output / 'missing-index')
    sys.path.insert(0, str(ROOT))
    from dataclasses import asdict
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.orm import Session
    from src.config import get_settings
    from src.db import Base, engine, get_db
    from src.main import app
    from src.models.db_models import ChatSession, User
    from src.services.auth import get_optional_user, require_customer
    from src.services.chat_classification import classify_chat_context
    from src.services.chat_normalization import normalize_chat_text
    from src.services.session_store import get_store

    settings = get_settings()
    (output / 'environment.json').write_text(json.dumps({
        'mode': mode, 'python': sys.version.split()[0], 'llm_enabled': settings.agent_llm_enabled,
        'model': settings.model_name, 'index': settings.chroma_persist_dir,
        'database': str(output / 'audit.db'), 'tracing': False,
        'answer_correctness': 'NOT_MEASURED_OFFLINE' if mode == 'offline' else 'REQUIRES_EVIDENCE_REVIEW',
        'provider_timeout_s': settings.agent_llm_timeout_s, 'turn_timeout_s': settings.agent_turn_timeout_s,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    Base.metadata.create_all(engine)
    records = []
    with Session(engine) as db:
        user = User(id='context-audit-synthetic', username='context-audit-synthetic', password_hash='unused', role='CUSTOMER')
        db.add(user)
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_optional_user] = lambda: user
        app.dependency_overrides[require_customer] = lambda: user
        try:
            async with AsyncClient(transport=ASGITransport(app, raise_app_exceptions=False), base_url='http://context-audit') as client:
                for index, case in enumerate(cases):
                    session_id = f'context-audit-{index}'
                    turns = []
                    for number, question in enumerate(case['turns'], 1):
                        started = time.monotonic()
                        row = {'input': question, 'turn': number}
                        try:
                            response = await asyncio.wait_for(client.post('/api/v1/customer/chat', json={
                                'session_id': session_id, 'message': question, 'request_id': f'{session_id}-{number}',
                            }), timeout=50)
                            row['http_status'] = response.status_code
                            try:
                                row['data'] = response.json().get('data') or {}
                            except (ValueError, AttributeError):
                                row['data'] = {}
                            db.expire_all()
                            session = db.get(ChatSession, session_id)
                            state = (session.memory_states or {}).get(session_id, {}) if session else {}
                            row.update(context=state.get('conversation_context') or {},
                                       understanding=state.get('turn_understanding') or {},
                                       progress=state.get('conversation_progress') or {},
                                       route=state.get('conversation_route'), retrieval=state.get('conversation_retrieval') or {})
                            row['classification'] = asdict(classify_chat_context(question))
                            row['normalized'] = normalize_chat_text(question)
                            events = get_store().replay(session_id)
                            row['llm_outcomes'] = [{'prompt': e['node'], 'outcome': e['gate_decision']}
                                                   for e in events if e.get('kind') == 'llm'][-5:]
                        except Exception as error:
                            db.rollback()
                            row.update(http_status=None, error=type(error).__name__, data={})
                        row['latency_s'] = round(time.monotonic() - started, 3)
                        turns.append(row)
                    checks = check_contract(case, turns[-1])
                    result = {'id': case['id'], 'group': case.get('group'), 'domain': case['domain'],
                              'context': case['context'], 'expected': {k: v for k, v in case.items() if k not in {'variants', 'turns'}},
                              'turns': turns, 'checks': checks, 'passed': all(checks.values())}
                    semantic = {k: v for k, v in checks.items() if k.startswith('answer_')}
                    result.update(contract_result=all(v for k, v in checks.items() if not k.startswith('answer_')),
                                  answer_assessment=('FAIL' if not all(semantic.values()) else 'PARTIALLY_MEASURED')
                                  if semantic else 'NOT_MEASURED', not_measured=['grounding_review'], blocked=[])
                    records.append(result)
                    with (output / 'results.jsonl').open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(result, ensure_ascii=False) + '\n')
                    print(f'{index + 1}/{len(cases)} {case["id"]}: {"PASS" if result["passed"] else "FAIL"}', flush=True)
        finally:
            app.dependency_overrides.clear()
    return records


def write_summary(records: list[dict], output: Path) -> dict:
    domains = {}
    for row in records:
        counts = domains.setdefault(row['domain'], {'total': 0, 'passed': 0, 'failed': 0})
        counts['total'] += 1
        counts['passed' if row['passed'] else 'failed'] += 1
    summary = {'total': len(records), 'passed': sum(r['passed'] for r in records),
               'failed': sum(not r['passed'] for r in records),
               'turns': sum(len(r['turns']) for r in records), 'domains': domains,
               'failed_checks': dict(Counter(k for r in records for k, passed in r['checks'].items() if not passed))}
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Context equivalence API audit', '', json.dumps(summary, ensure_ascii=False, indent=2), '',
             '| Case | Domain | Context | Failed checks |', '| --- | --- | --- | --- |']
    for row in records:
        lines.append('| ' + row['id'] + ' | ' + row['domain'] + ' | ' + row['context'] + ' | '
                     + (', '.join(k for k, passed in row['checks'].items() if not passed) or 'PASS') + ' |')
    (output / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', default=str(ROOT / 'eval/datasets/context_equivalence_v1.json'))
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--mode', choices=['offline', 'live'], default='offline')
    parser.add_argument('--contexts', default='fresh,after_quote')
    parser.add_argument('--ids', default='', help='Comma-separated exact case IDs to select')
    args = parser.parse_args()
    from audit_natural_conversations import validate_output_directory
    output = validate_output_directory(args.output_dir)
    cases = build_cases(json.loads(Path(args.dataset).read_text(encoding='utf-8')), args.contexts.split(','))
    if args.ids:
        selected = set(args.ids.split(','))
        cases = [case for case in cases if case['id'] in selected]
        if {case['id'] for case in cases} != selected:
            parser.error('Unknown case IDs')
    if not cases:
        parser.error('No cases selected')
    output.mkdir(parents=True)
    (output / 'cases.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding='utf-8')
    records = asyncio.run(audit(cases, output, args.mode))
    print(json.dumps(write_summary(records, output), ensure_ascii=False))


if __name__ == '__main__':
    main()
