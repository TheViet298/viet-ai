import httpx
import pytest


def test_cost_and_usage_missing_are_not_reported_as_complete_zero():
    from scripts.langfuse_cloud_evidence import summarize_trace
    summary = summarize_trace([
        {'id': 'root', 'traceId': 'trace', 'type': 'SPAN', 'isRootObservation': True},
        {'id': 'g1', 'traceId': 'trace', 'type': 'GENERATION', 'usageDetails': {'input': 12, 'output': 5, 'total': 17}, 'totalCost': 0},
        {'id': 'g2', 'traceId': 'trace', 'type': 'GENERATION', 'usageDetails': {}, 'totalCost': None},
    ])
    assert summary['known_total_tokens'] == 17
    assert summary['missing_usage_count'] == 1
    assert summary['known_cost_usd'] == 0
    assert summary['missing_cost_count'] == 1
    assert summary['generation_count'] == 2


@pytest.mark.asyncio
async def test_cloud_reader_follows_cursor_and_does_not_mix_runs():
    from scripts.langfuse_cloud_evidence import collect_observations
    calls = []
    def handler(request):
        calls.append(request.url)
        if request.url.params.get('cursor') == 'page2':
            return httpx.Response(200, json={'data': [{'id': 'child', 'traceId': 't', 'metadata': {'run_id': 'run'}}], 'meta': {}})
        return httpx.Response(200, json={'data': [
            {'id': 'root', 'traceId': 't', 'metadata': {'run_id': 'run'}},
            {'id': 'other', 'traceId': 'x', 'metadata': {'run_id': 'else'}}], 'meta': {'cursor': 'page2'}})
    async with httpx.AsyncClient(base_url='https://example.invalid', transport=httpx.MockTransport(handler)) as client:
        rows = await collect_observations('run', timeout_s=0, client=client)
    assert {r['id'] for r in rows} == {'root', 'child'}
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_cloud_reader_does_not_treat_http_410_as_empty_success():
    from scripts.langfuse_cloud_evidence import collect_observations, CloudEvidenceError
    async with httpx.AsyncClient(base_url='https://example.invalid', transport=httpx.MockTransport(
        lambda _: httpx.Response(410, json={'message': 'private-provider-message'}))) as client:
        with pytest.raises(CloudEvidenceError, match='cloud_http_410'):
            await collect_observations('run', timeout_s=0, client=client)
