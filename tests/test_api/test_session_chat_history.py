import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, get_db
from src.main import app
from src.models.db_models import User
from src.services.auth import create_token

@pytest.fixture
def history_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'history.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user1 = User(id="user-1-id", username="user1@vinfast.vn", password_hash="hash1", role="CUSTOMER")
        user2 = User(id="user-2-id", username="user2@vinfast.vn", password_hash="hash2", role="CUSTOMER")
        db.add_all([user1, user2])
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        yield db
    app.dependency_overrides.clear()
    engine.dispose()

@pytest.mark.asyncio
async def test_get_session_history_authenticated_user(client, history_db):
    token = create_token(user_id="user-1-id", role="CUSTOMER")
    headers = {"Authorization": f"Bearer {token}"}
    session_id = "cust-session-001"

    # Gửi tin nhắn 1
    res1 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "Xin chào trợ lý",
    }, headers=headers)
    assert res1.status_code == 200

    # Gửi tin nhắn 2
    res2 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "VF5 bảo hành bao lâu?",
    }, headers=headers)
    assert res2.status_code == 200

    # Lấy lịch sử chat
    history_res = await client.get(f"/api/v1/customer/sessions/{session_id}/history", headers=headers)
    assert history_res.status_code == 200
    body = history_res.json()
    assert body["success"] is True
    data = body["data"]
    assert data["session_id"] == session_id
    assert len(data["messages"]) >= 4
    # Thứ tự turn: CUSTOMER -> AGENT -> CUSTOMER -> AGENT
    senders = [m["sender"] for m in data["messages"][:4]]
    assert senders == ["CUSTOMER", "AGENT", "CUSTOMER", "AGENT"]

@pytest.mark.asyncio
async def test_get_session_history_forbidden_for_other_user(client, history_db):
    token1 = create_token(user_id="user-1-id", role="CUSTOMER")
    token2 = create_token(user_id="user-2-id", role="CUSTOMER")
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}
    session_id = "user1-private-session"

    # User 1 chat
    res = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "Xe của tôi cần bảo dưỡng",
    }, headers=headers1)
    assert res.status_code == 200

    # User 2 cố tình truy cập lịch sử của User 1
    history_res = await client.get(f"/api/v1/customer/sessions/{session_id}/history", headers=headers2)
    assert history_res.status_code == 403

@pytest.mark.asyncio
async def test_get_session_history_guest_denied_for_registered_session(client, history_db):
    token1 = create_token(user_id="user-1-id", role="CUSTOMER")
    headers1 = {"Authorization": f"Bearer {token1}"}
    session_id = "user1-registered-session"

    await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "Tin nhắn bảo mật",
    }, headers=headers1)

    # Guest không truyền auth token
    history_res = await client.get(f"/api/v1/customer/sessions/{session_id}/history")
    assert history_res.status_code in {401, 403}
