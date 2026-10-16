"""Safe failure categories and session queue timing, without error payloads."""
import asyncio
import sqlite3
import time
from contextlib import asynccontextmanager

import httpx


def failure_details(error: BaseException) -> dict:
    details = {'error_type': type(error).__name__, 'failure_kind': 'error'}
    cause = error
    seen = set()
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        for error_type, phase in [(httpx.PoolTimeout, 'pool'), (httpx.ConnectTimeout, 'connect'),
                                  (httpx.ReadTimeout, 'read'), (httpx.WriteTimeout, 'write')]:
            if isinstance(cause, error_type):
                return {**details, 'failure_kind': 'timeout', 'timeout_phase': phase}
        cause = cause.__cause__ or cause.__context__
    if isinstance(error, (TimeoutError, httpx.TimeoutException)) or type(error).__name__ == 'APITimeoutError':
        return {**details, 'failure_kind': 'timeout', 'timeout_phase': 'deadline' if isinstance(error, TimeoutError) else 'provider_unspecified'}
    if isinstance(error, asyncio.CancelledError):
        return {**details, 'failure_kind': 'cancelled'}
    if isinstance(error, sqlite3.OperationalError) or type(error).__name__ == 'OperationalError':
        busy = any(term in str(error).casefold() for term in ('locked', 'busy'))
        return {**details, 'failure_layer': 'database', 'failure_kind': 'database_busy' if busy else 'database_error'}
    return details


@asynccontextmanager
async def observed_lock(lock: asyncio.Lock, scope: str):
    from src.services import observability as obs

    with obs.observation(scope + '.wait', metadata={'layer': 'queue', 'lock_scope': scope}) as span:
        begin = time.monotonic()
        try:
            await lock.acquire()
        finally:
            obs.update_observation(span, metadata={'layer': 'queue', 'lock_scope': scope,
                                                  'queue_wait_ms': round((time.monotonic() - begin) * 1000, 3)})
    try:
        yield
    finally:
        lock.release()
