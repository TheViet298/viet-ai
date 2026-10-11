import asyncio
from contextlib import nullcontext

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize('body_fails', [False, True])
async def test_lifespan_cancels_worker_and_flushes_tracing(monkeypatch, tmp_path, body_fails):
    import src.main as main

    events = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, 'ensure_schema', lambda: events.append('schema'))
    monkeypatch.setattr(main, 'initialize_observability', lambda: events.append('tracing'))

    async def worker(interval_seconds):
        assert interval_seconds == 600
        events.append('worker')
        try:
            await asyncio.Event().wait()
        finally:
            events.append('cancelled')

    async def flush(shutdown):
        assert shutdown is True
        events.append('flushed')

    monkeypatch.setattr(main, 'auto_close_background_loop', worker)
    monkeypatch.setattr(main, 'flush_observability', flush)
    with pytest.raises(RuntimeError, match='request failed') if body_fails else nullcontext():
        async with main.lifespan(main.app):
            await asyncio.sleep(0)
            if body_fails:
                raise RuntimeError('request failed')
    assert events == ['schema', 'tracing', 'worker', 'cancelled', 'flushed']
