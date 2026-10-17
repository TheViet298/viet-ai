import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db import Base, get_db
from src.main import app
from src.models.db_models import User, Message, ChatRequestRecord, ChatSession
from src.services.auth import get_optional_user, require_customer


@pytest.mark.asyncio
async def test_slow_flushed_turn_does_not_block_another_sqlite_session(tmp_path):
    from src.services.chat_turns import run_chat_turn
    from src.models.schemas import ApiResponse, ChatResponseData, CustomerChatRequest
    engine = create_engine(f'sqlite:///{tmp_path / "slow.db"}', connect_args={'timeout': 0.01})
    Base.metadata.create_all(engine)
    started, release = asyncio.Event(), asyncio.Event()

    async def handler(payload, user, db):
        db.add(Message(id=payload.session_id, session_id=payload.session_id,
                       sender_type='CUSTOMER', content=payload.message))
        db.flush()
        if payload.session_id == 'slow':
            started.set()
            await release.wait()
        return ApiResponse(data=ChatResponseData(response_type='FAQ_ANSWER', message='Dạ chào Quý khách!'))

    async def send(session_id):
        with Session(engine) as db:
            return await run_chat_turn(CustomerChatRequest(session_id=session_id, message='Xin chào'), None, db, handler)

    first = asyncio.create_task(send('slow'))
    await asyncio.wait_for(started.wait(), 3)
    second = asyncio.create_task(send('other'))
    try:
        done, _ = await asyncio.wait([second], timeout=0.05)
        assert not done, 'The second writer must wait asynchronously rather than fail with database locked'
    finally:
        release.set()
        results = await asyncio.gather(first, second, return_exceptions=True)
        engine.dispose()
    assert all(not isinstance(result, BaseException) for result in results)


@pytest.mark.asyncio
async def test_ten_sessions_and_duplicate_request_are_isolated(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "concurrency.db"}')
    Base.metadata.create_all(engine)
    user = User(id='parallel-synthetic', username='parallel-synthetic', password_hash='unused', role='CUSTOMER')
    with Session(engine) as db:
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
    def database():
        with Session(engine) as db:
            yield db
    app.dependency_overrides.update({get_db:database, get_optional_user:lambda:user, require_customer:lambda:user})
    try:
        async with AsyncClient(transport=ASGITransport(app), base_url='http://isolated-test') as client:
            payloads = [{'session_id':f'parallel-{i}', 'message':f'Tư vấn VF{7 if i % 2 else 8}',
                         'request_id':f'request-{i}'} for i in range(10)]
            results = await asyncio.gather(*(client.post('/api/v1/customer/chat', json=p) for p in [*payloads, payloads[0], payloads[0]]))
            assert all(r.status_code == 200 for r in results)
            for p, r in zip([*payloads, payloads[0], payloads[0]], results, strict=True):
                expected = 'VF7' if 'VF7' in p['message'] else 'VF8'
                assert {c['model'] for c in r.json()['data']['vehicle_cards']} == {expected}
            assert results[0].json() == results[-1].json() == results[-2].json()
        with Session(engine) as db:
            assert db.query(ChatRequestRecord).count() == 10
            assert db.query(Message).filter_by(session_id='parallel-0').count() == 2
            assert db.query(ChatSession).count() == 10
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
