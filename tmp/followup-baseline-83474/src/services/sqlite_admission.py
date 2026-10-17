"""Nonblocking admission for SQLite's single writer, shared across API workers."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from weakref import WeakValueDictionary

from fastapi import HTTPException
from filelock import AsyncFileLock, Timeout

_LOCKS = WeakValueDictionary()


@asynccontextmanager
async def chat_writer(db):
    engine = db.get_bind()
    if engine.dialect.name != 'sqlite':
        yield
        return
    database = engine.url.database
    key = str(Path(database).resolve()) if database and database != ':memory:' else str(id(engine))
    lock = _LOCKS.setdefault(key, asyncio.Lock())
    # shortcut: SQLite queues whole atomic chat transactions; use PostgreSQL
    # when chat and staff need concurrent write throughput.
    try:
        await asyncio.wait_for(lock.acquire(), timeout=45)
    except TimeoutError as error:
        raise HTTPException(503, 'Hệ thống đang bận. Quý khách vui lòng thử lại sau ít phút.') from error
    try:
        if not database or database == ':memory:':
            yield
            return
        file_lock = AsyncFileLock(key + '.chat.lock', timeout=45, poll_interval=0.02,
                                  run_in_executor=True, preserve_lock_file=True,
                                  fallback_to_soft=False)
        try:
            await file_lock.acquire()
        except Timeout as error:
            raise HTTPException(503, 'Hệ thống đang bận. Quý khách vui lòng thử lại sau ít phút.') from error
        try:
            yield
        finally:
            await file_lock.release()
    finally:
        lock.release()
