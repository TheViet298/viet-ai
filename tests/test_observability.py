import asyncio
import json
from contextlib import contextmanager

import pytest

from src.services import observability as obs


def test_missing_credentials_keeps_business_exception(monkeypatch):
    monkeypatch.setenv('LANGFUSE_TRACING_ENABLED', 'false')
    assert obs.initialize_observability() is False
    assert obs.get_tracer_callbacks() == []
    with pytest.raises(ValueError, match='business'):
        with obs.observation('test'):
            raise ValueError('business')


def test_mask_removes_credentials_images_and_private_state():
    value = obs.mask_telemetry(data={
        'authorization': 'Bearer secret-fixture', 'api_key': 'private-fixture',
        'messages': [{'content': 'data:image/png;base64,private-image'}],
        'usage': {'input': 3, 'output': 2},
        'inlineData': {'mimeType': 'image/png', 'data': 'raw-image'},
        'error': 'provider includes secret-fixture',
    })
    encoded = json.dumps(value)
    assert not any(v in encoded for v in ['secret-fixture', 'private-fixture', 'private-image', 'raw-image'])
    assert value['usage'] == {'input': 3, 'output': 2}


class FakeSpan:
    trace_id = 'a' * 32

    def __init__(self):
        self.fields = {}

    def update(self, **fields):
        self.fields.update(fields)

    def update_trace(self, **fields):
        self.fields.update(fields)


class FakeClient:
    def __init__(self):
        self.records = []
        self.lifecycle = []

    @contextmanager
    def start_as_current_observation(self, **fields):
        span = FakeSpan()
        span.fields.update(fields)
        self.records.append(span)
        yield span

    def flush(self):
        self.lifecycle.append('flush')

    def shutdown(self):
        self.lifecycle.append('shutdown')


@pytest.mark.asyncio
async def test_parallel_roots_keep_identity_separate(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(obs, '_client', client)

    async def request(sid):
        with obs.observation('root'):
            obs.update_trace_identity(session_id=sid, user_id='private-user')
            await asyncio.sleep(0)
            with obs.observation('child') as child:
                assert obs.current_trace_id() == 'a' * 32
                return child

    a, b = await asyncio.gather(request('session-a'), request('session-b'))
    assert a.fields['metadata']['session_id'] == 'session-a'
    assert b.fields['metadata']['session_id'] == 'session-b'
    assert 'private-user' not in str(client.records[0].fields)
    assert obs.current_trace_id() is None


@pytest.mark.asyncio
async def test_shutdown_flushes_then_closes(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(obs, '_client', client)
    await obs.flush_observability(shutdown=True)
    assert client.lifecycle == ['flush', 'shutdown']


def test_exporter_failure_does_not_change_business_result(monkeypatch):
    class Broken:
        def start_as_current_observation(self, **fields):
            raise RuntimeError('export failure')

    monkeypatch.setattr(obs, '_client', Broken())
    with obs.observation('test') as handle:
        obs.update_observation(handle, output={'ok': True})
        result = 42
    assert result == 42
