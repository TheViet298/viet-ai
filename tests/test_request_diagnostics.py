import asyncio
from contextlib import contextmanager

import httpx
import pytest


@pytest.mark.parametrize('error,phase', [(httpx.PoolTimeout('private'), 'pool'),
    (httpx.ConnectTimeout('private'), 'connect'), (httpx.ReadTimeout('private'), 'read'),
    (httpx.WriteTimeout('private'), 'write'), (TimeoutError('private'), 'deadline')])
def test_transport_timeouts_keep_their_phase_without_private_payload(error, phase):
    from src.services.request_diagnostics import failure_details
    from src.services.agent_llm import classify_provider_error

    details = failure_details(error)
    assert details['timeout_phase'] == phase
    assert details['failure_kind'] == 'timeout'
    assert 'private' not in str(details)
    assert classify_provider_error(error) == 'timeout'


@pytest.mark.asyncio
async def test_same_session_contention_has_wait_span_and_does_not_leak_lock_on_cancel(monkeypatch):
    from src.services.request_diagnostics import observed_lock
    from src.services import observability as obs

    spans = []
    @contextmanager
    def capture(name, **kwargs):
        row = {'name': name, **kwargs}
        spans.append(row)
        yield row
    monkeypatch.setattr(obs, 'observation', capture)
    monkeypatch.setattr(obs, 'update_observation', lambda row, **fields: row.update(fields))
    lock = asyncio.Lock()
    await lock.acquire()
    entered = asyncio.Event()
    async def waiter():
        async with observed_lock(lock, 'application.session_lock'):
            entered.set()
    task = asyncio.create_task(waiter())
    await asyncio.sleep(0)
    assert not entered.is_set()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert lock.locked(), 'cancelled waiter must not release another request lock'
    lock.release()
    async with observed_lock(lock, 'application.session_lock'):
        assert lock.locked()
    assert not lock.locked()
    assert all(s['name'] == 'application.session_lock.wait' for s in spans)


def test_failed_observation_labels_stage_and_transport_phase(monkeypatch):
    from src.services import observability as obs

    captured = []
    class Span:
        trace_id = 'a' * 32
        def update(self, **fields):
            captured.append(fields)
    class Client:
        @contextmanager
        def start_as_current_observation(self, **kwargs):
            yield Span()
    monkeypatch.setattr(obs, '_client', Client())
    with pytest.raises(httpx.ReadTimeout):
        with obs.observation('llm.call', metadata={'layer': 'model', 'timeout_s': 12}):
            raise httpx.ReadTimeout('secret provider payload')
    metadata = [row['metadata'] for row in captured if row.get('level') == 'ERROR'][-1]
    assert metadata['failure_stage'] == 'llm.call'
    assert metadata['timeout_phase'] == 'read'
    assert metadata['elapsed_ms'] >= 0
    assert 'secret provider payload' not in str(captured)


@pytest.mark.asyncio
async def test_ten_concurrent_model_timeouts_are_identified_independently(monkeypatch):
    from pydantic import BaseModel
    from src.config import get_settings
    from src.services import observability as obs, llm, agent_llm
    from tests.test_observability import FakeClient

    class Answer(BaseModel):
        answer: str
    class SlowProvider:
        def with_structured_output(self, *args, **kwargs):
            return self
        async def ainvoke(self, *args, **kwargs):
            await asyncio.sleep(0)
            raise httpx.ReadTimeout('private upstream payload')
    settings = get_settings()
    monkeypatch.setattr(settings, 'agent_llm_enabled', True)
    monkeypatch.setattr(settings, 'openai_api_key', 'synthetic-key')
    monkeypatch.setattr(llm, 'get_llm', SlowProvider)
    capture = FakeClient()
    monkeypatch.setattr(obs, '_client', capture)
    agent_llm.reset_circuits()
    async def request(index):
        with obs.validation_context('concurrent-fixture', str(index)):
            state = {'query': 'Xin chào VinFast', 'session_id': f'concurrent-{index}'}
            result = await agent_llm.structured_call(state, 'general', Answer)
            assert result is None and state['last_llm_outcome'] == 'timeout'
    await asyncio.gather(*(request(index) for index in range(10)))
    failures = [s.fields for s in capture.records if s.fields.get('name') == 'llm.call']
    assert len(failures) == 10
    assert {f['metadata']['test_case_id'] for f in failures} == {str(i) for i in range(10)}
    assert all(f['metadata']['layer'] == 'model' and f['metadata']['timeout_phase'] == 'read' for f in failures)
    assert all(f['metadata']['timeout_s'] > 0 for f in failures)
    assert 'private upstream payload' not in str(failures)
    from src.services.tracer import replay_session
    for index in range(10):
        event = replay_session(f'concurrent-{index}')[-1]
        assert event['metadata']['diagnostics']['timeout_phase'] == 'read'
        assert event['metadata']['diagnostics']['failure_stage'] == 'llm.call'
