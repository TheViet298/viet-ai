"""Bounded observations-v2 reads and explicit partial usage/cost summaries."""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx


class CloudEvidenceError(RuntimeError):
    pass


async def collect_observations(run_id: str, *, timeout_s: float = 60, client=None,
                               from_time: str | None = None, expected_cases: int = 10) -> list[dict]:
    owned = client is None
    if owned:
        client = httpx.AsyncClient(base_url=os.getenv('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com'),
                                   auth=(os.environ['LANGFUSE_PUBLIC_KEY'], os.environ['LANGFUSE_SECRET_KEY']), timeout=20)
    start = from_time or (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    deadline, previous = time.monotonic() + timeout_s, None
    try:
        while True:
            cursor, seen, rows = None, set(), {}
            while True:
                params = {'fields': 'core,basic,usage,metadata,model,io,trace_context,time', 'limit': 1000,
                          'fromStartTime': start, 'toStartTime': datetime.now(UTC).isoformat()}
                if cursor:
                    params['cursor'] = cursor
                try:
                    response = await client.get('/api/public/v2/observations', params=params)
                except httpx.HTTPError as exc:
                    raise CloudEvidenceError('cloud_transport_error') from None
                if response.status_code != 200:
                    raise CloudEvidenceError(f'cloud_http_{response.status_code}')
                body = response.json()
                for row in body.get('data', []):
                    if (row.get('metadata') or {}).get('run_id') == run_id:
                        rows[row['id']] = row
                cursor = body.get('meta', {}).get('cursor')
                if not cursor:
                    break
                if cursor in seen:
                    raise CloudEvidenceError('cloud_repeated_cursor')
                seen.add(cursor)
            result = list(rows.values())
            roots = [o for o in result if o.get('name', '').startswith('p142.') and o.get('endTime')]
            signature = {(o['id'], o.get('endTime')) for o in result}
            if time.monotonic() >= deadline or (len(roots) >= expected_cases and signature == previous):
                return result
            previous = signature
            await asyncio.sleep(min(5, max(0, deadline - time.monotonic())))
    finally:
        if owned:
            await client.aclose()


def summarize_trace(observations: list[dict]) -> dict:
    generations = {o['id']: o for o in observations if o.get('type') == 'GENERATION'}
    input_count = output_count = total_count = 0
    known_cost = 0.0
    missing_usage = missing_cost = 0
    for gen in generations.values():
        usage = gen.get('usageDetails') or {}
        input_tokens = usage.get('input', gen.get('inputUsage'))
        output_tokens = usage.get('output', gen.get('outputUsage'))
        total = usage.get('total', gen.get('totalUsage'))
        reported = bool(usage) or (gen.get('metadata') or {}).get('usage_status') == 'reported'
        if reported and isinstance(total, (int, float)):
            input_count += input_tokens or 0
            output_count += output_tokens or 0
            total_count += total
        else:
            missing_usage += 1
        cost = gen.get('totalCost')
        if isinstance(cost, (int, float)) and (reported or cost > 0):
            known_cost += cost
        else:
            missing_cost += 1
    trace_ids = sorted({o['traceId'] for o in observations if o.get('traceId')})
    return {'trace_ids': trace_ids, 'observation_ids': sorted({o['id'] for o in observations}),
            'root_count': sum(bool(o.get('isRootObservation')) for o in observations),
            'generation_count': len(generations), 'known_input_tokens': input_count,
            'known_output_tokens': output_count, 'known_total_tokens': total_count,
            'known_cost_usd': round(known_cost, 10), 'missing_usage_count': missing_usage,
            'missing_cost_count': missing_cost, 'totals_complete': not (missing_usage or missing_cost)}


def write_evidence(output_dir: Path, results: list[dict]) -> Path:
    from src.services.observability import mask_telemetry
    target = output_dir / 'results.json'
    target.write_text(json.dumps(mask_telemetry(data=results), ensure_ascii=False, indent=2), encoding='utf-8')
    return target
