"""Sequential live audit using a synthetic principal and an isolated database."""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_output_directory(value: str) -> Path:
    path = Path(value).resolve()
    allowed = (ROOT / '.test-runs').resolve()
    if not path.is_relative_to(allowed) or path == allowed or path.exists():
        raise ValueError('Output must be a new directory inside .test-runs')
    return path


def load_cases(path: Path) -> list[dict]:
    cases = json.loads(path.read_text(encoding='utf-8'))
    for case in cases:
        turns = case.get('turns') or [case.get('first'), case.get('followup')]
        if not case.get('id') or not turns or not all(isinstance(t, str) and t.strip() for t in turns):
            raise ValueError('Each case needs an id and nonempty sequential turns')
        case['turns'] = turns
    return cases


async def audit(cases: list[dict], output: Path, repetitions: int) -> list[dict]:
    # Configure isolation before importing app/config/db; no external booking
    # connectors are configured. Each repetition has fresh sessions.
    os.environ['DATABASE_URL'] = 'sqlite:///' + (output / 'audit.db').as_posix()
    os.environ['LANGFUSE_TRACING_ENABLED'] = 'false'
    sys.path.insert(0, str(ROOT))
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.orm import Session

    from src.config import get_settings
    from src.db import Base, engine, get_db
    from src.main import app
    from src.models.db_models import ChatSession, User
    from src.services.auth import get_optional_user, require_customer

    Base.metadata.create_all(engine)
    results = []
    with Session(engine) as db:
        user = User(id='natural-audit-synthetic', username='natural-audit-synthetic', password_hash='unused', role='CUSTOMER')
        db.add(user)
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_optional_user] = lambda: user
        app.dependency_overrides[require_customer] = lambda: user
        try:
            async with AsyncClient(transport=ASGITransport(app), base_url='http://audit') as client:
                for repetition in range(1, repetitions + 1):
                    for case in cases:
                        session_id = f'natural-audit-{repetition}-{case["id"]}'
                        for turn_number, message in enumerate(case['turns'], 1):
                            start = time.monotonic()
                            response = await client.post('/api/v1/customer/chat', json={
                                'session_id': session_id, 'message': message,
                                'request_id': f'{session_id}-{turn_number}',
                            })
                            if response.status_code != 200:
                                raise RuntimeError(f'HTTP {response.status_code}: {case["id"]} turn {turn_number}')
                            payload = response.json()
                            if not payload.get('success') or not payload.get('data', {}).get('message'):
                                raise RuntimeError(f'Invalid response: {case["id"]} turn {turn_number}')
                            db.expire_all()
                            state = db.get(ChatSession, session_id).memory_states[session_id]
                            result = {'repetition': repetition, 'case': case['id'], 'turn': turn_number,
                                      'input': message, 'data': payload['data'],
                                      'latency_s': round(time.monotonic() - start, 3),
                                      'llm_enabled': get_settings().agent_llm_enabled,
                                      'understanding': state.get('turn_understanding'),
                                      'context': state.get('conversation_context'),
                                      'progress': state.get('conversation_progress'),
                                      'route': state.get('conversation_route'),
                                      'retrieval_diagnostics': state.get('conversation_retrieval') or state.get('retrieval_diagnostics')}
                            results.append(result)
                            (output / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
                        print(f'Completed repetition {repetition}: {case["id"]}', flush=True)
        finally:
            app.dependency_overrides.clear()
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--repetitions', type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 10:
        parser.error('repetitions must be between 1 and 10')
    try:
        output = validate_output_directory(args.output_dir)
        cases = load_cases(Path(args.cases))
    except (ValueError, OSError) as error:
        parser.error(str(error))
    output.mkdir(parents=True)
    results = asyncio.run(audit(cases, output, args.repetitions))
    lines = ['# Natural conversation audit', '', f'{len(cases)} cases, {len(results)} sequential turns. HTTP/schema validated; semantic acceptance requires review.', '']
    for result in results:
        lines.extend([f'## Run {result["repetition"]} · {result["case"]} · Turn {result["turn"]}',
                      '', '**Customer:** ' + result['input'], '', result['data']['message'], '',
                      f'Move: {result["understanding"]["move"]}; goal: {result["context"]["active_goal"]}; progress: {result["progress"]["state"]}; latency: {result["latency_s"]}s.', ''])
    (output / 'report.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
