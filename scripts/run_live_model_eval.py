"""Ten live API/model checks, including dashboard and exterior image recognition."""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_cases():
    return [json.loads(line) for line in (ROOT / 'eval/datasets/live_model_cases_v1.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]


def expected_live_case(case, settings):
    if case['kind'] == 'chat':
        return {**case, 'expected_model': settings.model_name, 'expected_prompt': 'general'}
    model = settings.vision_model if case['image_kind'] == 'exterior' or settings.vision_provider == 'openai' else settings.dashboard_vision_model
    return {**case, 'expected_model': model, 'expected_prompt': 'vision.' + case['image_kind']}


def evaluate_live(case, result, rows):
    from eval.model_evidence import model_matches
    from scripts.langfuse_cloud_evidence import summarize_trace

    successful = [r for r in rows if r.get('type') == 'GENERATION' and r.get('level') != 'ERROR' and r.get('endTime')]
    if case.get('expected_model'):
        successful = [r for r in successful if model_matches(case['expected_model'], r.get('model'))]
    if case.get('expected_prompt'):
        successful = [r for r in successful if ((r.get('metadata') or {}).get('prompt_name') or r.get('name')) == case['expected_prompt']]
    if not successful or summarize_trace(successful)['known_total_tokens'] <= 0:
        return {'status': 'BLOCKED', 'reasons': ['successful_live_generation_with_usage_missing']}
    if result['http_status'] != 200:
        return {'status': 'FAIL', 'reasons': [f"http_{result['http_status']}"]}
    data = result['response'].get('data', result['response'])
    reasons = []
    if case['kind'] == 'chat':
        outcomes = [(r.get('metadata') or {}).get('outcome', r.get('statusMessage')) for r in rows
                    if r.get('name') == 'llm.outcome' and (not case.get('expected_prompt') or
                       (r.get('metadata') or {}).get('prompt_name') == case['expected_prompt'])]
        if not outcomes or 'parsed' not in outcomes:
            return {'status': 'BLOCKED', 'reasons': ['application_generation_not_parsed']}
        if not (data.get('response') or data.get('reply')):
            reasons.append('answer_missing')
    else:
        signals = data.get('detected_signals') or {}
        if signals.get('analysis_error'):
            return {'status': 'BLOCKED', 'reasons': [signals['analysis_error']]}
        if data.get('analysis_status') != 'ANALYZED':
            reasons.append('upload_not_analyzed')
        if case['image_kind'] == 'dashboard' and case['expected_symptom'] not in signals.get('symptom_keys', []):
            reasons.append('expected_visual_symptom_missing')
        if case['image_kind'] == 'exterior':
            evidence = signals.get('vehicle_evidence') or {}
            if evidence.get('model_label') != case['expected_model_label']:
                reasons.append('invented_model_for_synthetic_image')
            if evidence.get('requires_user_confirmation') is not True:
                reasons.append('user_confirmation_contract_missing')
    return {'status': 'FAIL' if reasons else 'PASS', 'reasons': reasons}


def image_fixture(case):
    from PIL import Image, ImageDraw
    from scripts.check_langfuse_matrix import synthetic_image

    data = synthetic_image(case['image_kind'])
    if case['variant'] == 'low_pressure' or case['variant'] == 'generic_vehicle':
        return data
    image = Image.open(io.BytesIO(data)).convert('RGB')
    draw = ImageDraw.Draw(image)
    if case['variant'] == 'sensor_fault':
        draw.rectangle((100, 440, 870, 530), fill='#080a0d')
        draw.text((160, 465), 'Tire pressure sensor fault', fill='#ffcd00', font_size=34)
    else:
        draw.rectangle((0, 0, 960, 640), fill='#e4e8ef')
        draw.rectangle((260, 180, 700, 460), fill='#4b5563')
        draw.text((270, 90), 'SYNTHETIC - NO VEHICLE', fill='#111827', font_size=28)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')


def write_report(output, manifest, results):
    usage = manifest['cloud_usage']
    lines = ['# 10 ca model thật, gồm nhận diện ảnh', '', f"Run ID: `{manifest['run_id']}`.",
             f"Chat: `{manifest['chat_model']}`. Vision: `{manifest['vision_model']}`.", '',
             f"Kết quả: `{manifest['verdicts']}`. Đã đối chiếu điểm Cloud: `{manifest['scores_verified']}`.",
             f"Generation: {usage['generation_count']}; token đã biết: {usage['known_total_tokens']}; chi phí đã biết: ${usage['known_cost_usd']:.10f}.", '',
             '| Ca | Nội dung | Trạng thái | Latency (s) | Token | Cost (USD) | Trace |',
             '| --- | --- | --- | ---: | ---: | ---: | --- |']
    for result in results:
        evidence = result['evidence']
        lines.append(f"| {result['id']} | {result['topic']} | {result['status']} | {result['duration_s']:.3f} | {evidence['known_total_tokens']} | {evidence['known_cost_usd']:.10f} | [Mở]({result['trace_url']}) |")
    lines += ['', 'Latency là thời gian một yêu cầu API, không gồm gửi/đọc Cloud. Chi phí là số Cloud ghi nhận, chưa đối chiếu hóa đơn.',
              'Ảnh là mô phỏng để kiểm tra tích hợp, OCR và xử lý không chắc chắn; không phải benchmark độ chính xác trên ảnh xe thực.',
              'Không có ảnh/media raw trên Langfuse; mở các file PNG trong thư mục này để xem đầu vào ảnh. Output root trace có kết quả phân tích.',
              '', 'Chi tiết hiệu năng: [metrics.md](metrics.md). Từng ca: [case-metrics.csv](case-metrics.csv).',
              '', 'Ảnh test: [áp suất thấp](LIVE-07.png), [lỗi cảm biến](LIVE-08.png), [xe mô phỏng](LIVE-09.png), [không có xe](LIVE-10.png).']
    (output / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


async def run(output):
    from scripts.check_langfuse_matrix import isolate, preflight, seed_validation_user

    for attempt in range(3):
        checks = await preflight()
        if checks.get('cloud_http_status') == 200:
            break
        print(json.dumps({'preflight_attempt': attempt + 1, 'cloud_status': checks.get('cloud_status', checks.get('cloud_http_status'))}), flush=True)
        if attempt < 2:
            await asyncio.sleep(5)
    if checks.get('cloud_http_status') != 200 or not checks.get('llm_enabled') or not checks.get('openai_key_present'):
        raise RuntimeError('Cloud and configured chat/vision provider must be available')
    paths = isolate(output)
    os.environ['LANGFUSE_TRACING_ENABLED'] = 'true'
    os.environ['LANGFUSE_TRACING_ENVIRONMENT'] = 'p142-live-models'
    os.environ.setdefault('LANGFUSE_TIMEOUT', '30')
    from src.main import app
    from src.config import get_settings
    from src.db import SessionLocal
    from src.services.auth import create_token
    from src.services import observability as obs
    from src.services.agent_llm import reset_circuits
    from scripts.langfuse_cloud_evidence import collect_observations, summarize_trace, write_observations
    from scripts.run_golden_cloud_eval import cloud_reader, read_cloud_pages
    from eval.golden_metrics import write_metrics
    import httpx

    run_id = 'p142-live-models-' + datetime.now(UTC).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:6]
    started = datetime.now(UTC).isoformat()
    settings = get_settings()
    results = []
    async with app.router.lifespan_context(app):
        if not obs.is_langfuse_available():
            raise RuntimeError('Cloud tracing initialization failed')
        with SessionLocal() as db:
            seed_validation_user(db)
        token = create_token('lf-synthetic-user', 'CUSTOMER')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://live-eval') as api:
            for case in load_cases():
                reset_circuits()
                case_id = case['id']
                with obs.validation_context(run_id, case_id):
                    with obs.observation(f'p142.live.{case_id}') as root:
                        trace_id = getattr(root, 'trace_id', None)
                        obs.update_observation(root, input={'message': case.get('message'), 'image_kind': case.get('image_kind'),
                                                           'fixture': f'{case_id}.png' if case['kind'] == 'upload' else None})
                        begin = time.monotonic()
                        try:
                            if case['kind'] == 'upload':
                                data = image_fixture(case)
                                (output / f'{case_id}.png').write_bytes(data)
                                response = await api.post('/api/v1/customer/attachments', headers={'Authorization': f'Bearer {token}'},
                                    data={'image_kind': case['image_kind']}, files={'file': (f'{case_id}.png', data, 'image/png')})
                            else:
                                response = await api.post('/api/v1/chat', headers={'Authorization': f'Bearer {settings.customer_demo_token}'},
                                    json={'session_id': f'{run_id}-{case_id}', 'message': case['message']})
                            body = response.json()
                            status = response.status_code
                        except Exception as error:
                            from src.services.agent_llm import classify_provider_error
                            status, body = 0, {'request_outcome': classify_provider_error(error)}
                        elapsed = round(time.monotonic() - begin, 3)
                        obs.update_observation(root, output=body)
                results.append({'id': case_id, 'kind': case['kind'], 'topic': case['topic'], 'trace_id': trace_id,
                                'http_status': status, 'response': obs.mask_telemetry(data=body), 'duration_s': elapsed})
                save(output / 'results.json', results)
                print(json.dumps({'id': case_id, 'http_status': status, 'duration_s': elapsed}), flush=True)
        await obs.flush_observability()
        rows = await collect_observations(run_id, from_time=started, expected_cases=10)
        case_map = {c['id']: expected_live_case(c, settings) for c in load_cases()}
        for result in results:
            selected = [r for r in rows if r.get('traceId') == result['trace_id']]
            result.update(evaluate_live(case_map[result['id']], result, selected))
            result['evidence'] = summarize_trace(selected)
            result['trace_url'] = f"https://cloud.langfuse.com/project/{checks['project_id']}/traces/{result['trace_id']}"
            for name, value in [('live_model_pass', int(result['status'] == 'PASS')), ('agent_latency_s', result['duration_s'])]:
                obs._client.create_score(name=name, value=value, trace_id=result['trace_id'],
                    score_id=uuid5(NAMESPACE_URL, f'{run_id}:{result["id"]}:{name}').hex,
                    data_type='BOOLEAN' if name == 'live_model_pass' else 'NUMERIC',
                    comment='Live API/provider check; synthetic images. ' + ','.join(result['reasons']))
        await obs.flush_observability()
        score_rows = []
        with cloud_reader() as reader:
            for attempt in range(8):
                score_rows = read_cloud_pages(reader, '/api/public/v3/scores', {
                    'traceId': ','.join(r['trace_id'] for r in results), 'name': 'live_model_pass,agent_latency_s', 'fields': 'subject', 'limit': 100})
                if len(score_rows) >= 20:
                    break
                await asyncio.sleep(3)
        score_values = {(s.get('subject', {}).get('traceId', s.get('subject', {}).get('id')), s['name']): s['value'] for s in score_rows}
        scores_verified = all(
            score_values.get((r['trace_id'], 'live_model_pass')) == (r['status'] == 'PASS')
            and abs(score_values.get((r['trace_id'], 'agent_latency_s'), -1) - r['duration_s']) < 1e-9 for r in results)
        save(output / 'results.json', results)
        save(output / 'cloud-scores.json', score_rows)
        write_observations(output, rows)
        metrics = write_metrics(output, [{'id': r['id'], 'trace_id': r['trace_id'],
            'output': {'duration_s': r['duration_s'], 'turns': [r['response']]}} for r in results], rows)
        manifest = {'run_id': run_id, 'started_at': started, 'finished_at': datetime.now(UTC).isoformat(),
                    'environment': 'p142-live-models', 'chat_model': settings.model_name, 'vision_model': settings.vision_model,
                    'project_id': checks['project_id'], 'total': len(results),
                    'verdicts': {s: sum(r['status'] == s for r in results) for s in ('PASS','FAIL','BLOCKED')},
                    'scores_verified': scores_verified, 'cloud_usage': summarize_trace(rows),
                    'latency': metrics['latency'], 'isolation': paths, 'synthetic_images': True}
        save(output / 'manifest.json', manifest)
        write_report(output, manifest, results)
        return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', required=True)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    output = (args.output_dir or ROOT / '.test-runs/live-models' / uuid4().hex[:12]).resolve()
    manifest = asyncio.run(run(output))
    print(json.dumps({'output': str(output), **{k:manifest[k] for k in ('run_id','verdicts','scores_verified')}}, indent=2))
    if not manifest['scores_verified'] or manifest['verdicts']['BLOCKED']:
        raise SystemExit(2)
    if manifest['verdicts']['FAIL']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
