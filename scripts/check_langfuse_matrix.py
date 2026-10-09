"""Run the ten-case matrix in a fresh local sandbox, then reconcile Cloud evidence.

Examples: python scripts/check_langfuse_matrix.py --preflight
          python scripts/check_langfuse_matrix.py --run
The script never starts live calls on import.
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def isolate(output: Path) -> dict:
    output = output.resolve()
    if not output.is_relative_to(ROOT / '.test-runs'):
        raise ValueError('output_must_be_inside_project_test_runs')
    if output.exists() and any(output.iterdir()):
        raise ValueError('output_must_be_new_or_empty')
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=False)
    output.mkdir(parents=True, exist_ok=True)
    os.environ['DATABASE_URL'] = 'sqlite:///' + (output / 'app.db').as_posix()
    os.environ['CHROMA_PERSIST_DIR'] = str(output / 'chroma')
    os.environ['SERVICE_POINTS_FILE'] = str(ROOT / 'fixtures/service_points.demo.json')
    os.environ['APP_ENV'] = 'test'
    os.environ['CARDD_ENABLED'] = 'false'
    os.environ['CUSTOMER_DEMO_TOKEN'] = uuid4().hex
    os.environ['LANGFUSE_TRACING_ENVIRONMENT'] = 'p142-validation'
    os.chdir(output)
    from src.config import get_settings
    get_settings.cache_clear()
    from src.db import engine
    from src.services.session_store import get_store
    return {'database': str(Path(engine.url.database).resolve()),
            'session_store': str(get_store().path.resolve()),
            'attachments': str(output / 'data/attachments'),
            'chroma': str(output / 'chroma')}


def seed_rag_fixture() -> dict:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from src.config import get_settings
    from src.services.multilingual_embeddings import MultilingualE5
    from src.services.rag_service import source_registry
    records = [json.loads(line) for line in (ROOT / 'data/processed/chunks.jsonl').read_text(encoding='utf-8').splitlines()]
    records = [r for r in records if r['source_id'] == 'SRC-002']
    registry = source_registry()['SRC-002']
    # Real local embedding and retrieval over a fixed, existing official-source fixture.
    encoder = MultilingualE5()
    collection = chromadb.PersistentClient(path=get_settings().chroma_persist_dir,
                                           settings=ChromaSettings(anonymized_telemetry=False)).create_collection(
        'vinfast_knowledge_base', embedding_function=encoder, configuration={'hnsw': {'space': 'l2'}})
    metadata = {k: ','.join(v) if isinstance(v, list) else v for k, v in registry.items()
                if isinstance(v, (str, int, float, bool, list)) and k != 'approved_urls'}
    metadata['source_id'] = 'SRC-002'
    collection.add(ids=[r['chunk_id'] for r in records], documents=[r['content'] for r in records],
                   metadatas=[{**metadata, 'section': r.get('section', 'Policy')} for r in records])
    return {'source_id': 'SRC-002', 'document_count': len(records), 'embedding': encoder.name(),
            'kind': 'official_source_fixture_real_local_retrieval'}


def synthetic_image(kind: str) -> bytes:
    from PIL import Image, ImageDraw
    image = Image.new('RGB', (960, 640), '#17191e')
    draw = ImageDraw.Draw(image)
    if kind == 'dashboard':
        draw.rounded_rectangle((80, 60, 880, 550), radius=50, fill='#080a0d', outline='#717783', width=8)
        draw.ellipse((120, 160, 370, 410), outline='#e5e7eb', width=12)
        draw.ellipse((590, 160, 840, 410), outline='#e5e7eb', width=12)
        draw.text((390, 220), '0 km/h', fill='white', font_size=40)
        draw.text((300, 460), 'Tire pressure low', fill='#ffcd00', font_size=35)
        draw.text((350, 80), 'SYNTHETIC TEST', fill='white', font_size=25)
    else:
        draw.rectangle((0, 420, 960, 640), fill='#777d86')
        draw.polygon([(100, 400), (160, 290), (320, 290), (380, 170), (620, 170), (720, 290), (840, 330), (860, 460), (100, 460)], fill='#dbe3ec')
        draw.polygon([(330, 290), (400, 190), (600, 190), (690, 290)], fill='#32485e')
        for x in (260, 730):
            draw.ellipse((x-65, 395, x+65, 525), fill='#121316', outline='#aab2bd', width=12)
        draw.text((130, 65), 'SYNTHETIC EXTERIOR - NO MODEL CLAIM', fill='white', font_size=25)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


async def preflight() -> dict:
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=False)
    from src.config import get_settings
    import httpx
    settings = get_settings()
    result = {'cloud_keys_present': bool(os.getenv('LANGFUSE_PUBLIC_KEY') and os.getenv('LANGFUSE_SECRET_KEY')),
              'openai_key_present': bool(settings.openai_api_key), 'google_key_present': bool(settings.google_api_key),
              'model': settings.model_name, 'vision_model': settings.vision_model,
              'vision_provider': settings.vision_provider, 'llm_enabled': settings.agent_llm_enabled,
              'local_embedding_model_present': (ROOT / 'data/models/multilingual-e5-small/onnx/model_quantized.onnx').is_file()}
    if result['cloud_keys_present']:
        try:
            async with httpx.AsyncClient(timeout=20, auth=(os.environ['LANGFUSE_PUBLIC_KEY'], os.environ['LANGFUSE_SECRET_KEY'])) as client:
                response = await client.get(os.getenv('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com').rstrip('/') + '/api/public/projects')
                result['cloud_http_status'] = response.status_code
                if response.status_code == 200:
                    result['project_id'] = response.json()['data'][0]['id']
        except httpx.HTTPError:
            result['cloud_status'] = 'transport_error'
    return result


def seed_validation_user(db):
    from src.models.db_models import User, UserRole
    from src.services.auth import hash_password
    user = User(id='lf-synthetic-user', username='lf-synthetic-user', role=UserRole.CUSTOMER.value,
                password_hash=hash_password(uuid4().hex), mock_customer_id='CUST-LF-SYNTHETIC')
    db.add(user)
    db.commit()
    return user


async def run_matrix(output: Path, run_id: str) -> dict:
    checks = await preflight()
    output = output.resolve()
    if checks.get('cloud_http_status') != 200 or not checks.get('llm_enabled'):
        return {'status': 'BLOCKED', 'preflight': checks}
    paths = isolate(output)
    # src modules with Settings constants are imported only after isolate.
    from src.main import app
    from src.config import get_settings
    from src.db import SessionLocal
    from src.models.db_models import User
    from src.services.auth import hash_password, create_token
    from src.services import observability as obs
    from src.services.session_store import get_store
    from src.services.agent_llm import reset_circuits
    from scripts.langfuse_matrix_cases import matrix_cases, evaluate_case
    from scripts.langfuse_cloud_evidence import collect_observations, summarize_trace, write_evidence, CloudEvidenceError
    import src.services.llm as llm_module
    import httpx
    fixture = seed_rag_fixture()
    release = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--short', 'HEAD'], text=True).strip()
    os.environ['LANGFUSE_RELEASE'] = release
    started = datetime.now(UTC).isoformat()
    results = []
    settings = get_settings()
    async with app.router.lifespan_context(app):
        with SessionLocal() as db:
            seed_validation_user(db)
        upload_token = create_token('lf-synthetic-user', 'CUSTOMER')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://validation') as client:
            for case in matrix_cases():
                case_id = case['case_id']
                session_id = f'{run_id}-{case.get("session_group", case_id)}'
                begin = time.monotonic()
                original = llm_module.get_llm
                if case.get('fault_injected'):
                    class FaultChain:
                        def with_structured_output(self, *args, **kwargs):
                            return self
                        async def ainvoke(self, *args, **kwargs):
                            raise TimeoutError('validation_fault_injection')
                    llm_module.get_llm = lambda: FaultChain()
                try:
                    with obs.validation_context(run_id, case_id, fault_injected=bool(case.get('fault_injected'))):
                        if case['kind'] == 'upload':
                            image = synthetic_image(case['image_kind'])
                            (output / f'{case_id}-synthetic.png').write_bytes(image)
                            response = await client.post('/api/v1/customer/attachments',
                                headers={'Authorization': f'Bearer {upload_token}'},
                                data={'image_kind': case['image_kind']},
                                files={'file': (f'{case_id}-synthetic.png', image, 'image/png')})
                        else:
                            payload = {'session_id': session_id, 'message': case['message']}
                            if case.get('vehicle_model'):
                                payload['client_context'] = {'vehicle_model': case['vehicle_model']}
                            response = await client.post('/api/v1/chat', json=payload,
                                headers={'Authorization': f'Bearer {settings.customer_demo_token}'})
                    body = response.json()
                    if case_id in {'LF-04', 'LF-05'} and response.status_code == 200:
                        state = get_store().read_existing_state(session_id, 'customer-demo', 'customer')
                        body['_session_turn'] = state.get('turn')
                        body['_vehicle_model'] = state.get('vehicle_model')
                    results.append({'case_id': case_id, 'session_id': session_id, 'http_status': response.status_code,
                                    'response': body, 'duration_s': round(time.monotonic() - begin, 3),
                                    'fault_injected': bool(case.get('fault_injected'))})
                except Exception as exc:
                    from src.services.agent_llm import classify_provider_error
                    results.append({'case_id': case_id, 'http_status': 0, 'response': {},
                                    'request_outcome': classify_provider_error(exc),
                                    'duration_s': round(time.monotonic() - begin, 3)})
                finally:
                    llm_module.get_llm = original
                    reset_circuits()
                print(json.dumps({'case_id': case_id, 'http_status': results[-1]['http_status'],
                                  'duration_s': results[-1]['duration_s']}), flush=True)
                # LF-10 is deliberately exported only by lifespan shutdown.
                if case_id != 'LF-10':
                    await obs.flush_observability()
                write_evidence(output, results)
    cloud_status = 'read_ok'
    try:
        rows = await collect_observations(run_id, from_time=started)
    except CloudEvidenceError as exc:
        cloud_status, rows = str(exc), []
    for result in results:
        selected = [r for r in rows if (r.get('metadata') or {}).get('test_case_id') == result['case_id']]
        summary = summarize_trace(selected)
        verdict = evaluate_case(result['case_id'], result['http_status'], result['response'], selected)
        result.update(verdict)
        result['evidence'] = summary
        result['trace_urls'] = [f'https://cloud.langfuse.com/project/{checks["project_id"]}/traces/{tid}'
                                for tid in summary['trace_ids']]
    write_evidence(output, results)
    (output / 'observations.json').write_text(json.dumps(obs.mask_telemetry(data=rows), ensure_ascii=False, indent=2), encoding='utf-8')
    manifest = {'run_id': run_id, 'started_at': started, 'finished_at': datetime.now(UTC).isoformat(),
                'release': release, 'dirty_at_run': bool(subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True)),
                'preflight': checks, 'isolation': paths, 'rag_fixture': fixture,
                'cloud_status': cloud_status, 'summary': summarize_trace(rows),
                'verdicts': {s: sum(r['status'] == s for r in results) for s in ['PASS', 'FAIL', 'BLOCKED']}}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--preflight', action='store_true')
    actions.add_argument('--run', action='store_true')
    actions.add_argument('--probe-isolation', action='store_true')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    run_id = 'p142-' + datetime.now(UTC).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:6]
    output = args.output_dir or ROOT / '.test-runs/langfuse' / run_id
    if args.probe_isolation:
        os.environ['LANGFUSE_TRACING_ENABLED'] = 'false'
        result = isolate(output)
    elif args.preflight:
        result = asyncio.run(preflight())
    else:
        result = asyncio.run(run_matrix(output, run_id))
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
