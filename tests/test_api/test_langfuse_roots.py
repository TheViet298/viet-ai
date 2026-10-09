import pytest

from src.services import observability as obs
from tests.test_observability import FakeClient


@pytest.mark.asyncio
@pytest.mark.parametrize('route', ['/api/v1/chat', '/api/v1/public/chat'])
async def test_each_legacy_request_has_one_root_even_for_emergency(client, monkeypatch, route):
    capture = FakeClient()
    monkeypatch.setattr(obs, '_client', capture)
    monkeypatch.setattr('src.agents.chatbot_agent.get_tracer_callbacks', lambda **kwargs: [])
    result = await client.post(route, json={'message': 'Xe đang bốc khói và có mùi khét!'})
    assert result.status_code == 200
    assert result.json()['is_safety_trigger'] is True
    roots = [r for r in capture.records if r.fields.get('name') == 'p142.chat.legacy']
    assert len(roots) == 1
    assert roots[0].fields['session_id'] == result.json()['session_id']
    assert roots[0].fields['metadata']['outcome'] == 'completed'


@pytest.mark.asyncio
async def test_root_decorator_preserves_business_http_error(monkeypatch):
    from fastapi import HTTPException
    capture = FakeClient()
    monkeypatch.setattr(obs, '_client', capture)

    @obs.trace_endpoint('p142.chat.customer')
    async def handler():
        raise HTTPException(403, 'private internal detail')

    with pytest.raises(HTTPException) as error:
        await handler()
    assert error.value.status_code == 403
    assert len(capture.records) == 1
    assert 'private internal detail' not in str(capture.records[0].fields)
