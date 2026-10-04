import pytest

from src.api.auth import Principal, optional_principal
from src.main import app


@pytest.mark.asyncio
async def test_guest_quota_cannot_be_reset_with_request_session(client):
    for i in range(5):
        response = await client.post("/api/v1/chat", json={"message": "Chào bạn", "session_id": f"arbitrary-{i}"})
        assert response.status_code == 200
        assert response.json()["remaining_guest_messages"] == 4 - i
    response = await client.post("/api/v1/chat", json={"message": "Chào bạn", "session_id": "new-id"})
    assert response.status_code == 429
    emergency = await client.post("/api/v1/chat", json={"message": "Xe cháy"})
    assert emergency.status_code == 200
    assert "1900-232389" in emergency.json()["response"]


@pytest.mark.asyncio
async def test_customer_cannot_spoof_role_in_body(client):
    response = await client.post("/api/v1/agent/customer/chat", json={"message": "Xe cháy"})
    assert response.status_code == 401
    response = await client.post("/api/v1/chat", json={"message": "Xe cháy", "user_role": "customer"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_customer_case_is_saved_and_private(client):
    app.dependency_overrides[optional_principal] = lambda: Principal("c1", "customer")
    try:
        response = await client.post(
            "/api/v1/agent/customer/chat", json={"message": "VF8 mất phanh", "session_id": "customer1"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["analysis"] == ""
        assert data["response_type"] == "EMERGENCY_ALERT"
        cid = data["case_id"]
        assert cid
        assert (await client.get(f"/api/v1/agent/customer/cases/{cid}")).status_code == 200
        app.dependency_overrides[optional_principal] = lambda: Principal("c2", "customer")
        assert (await client.get(f"/api/v1/agent/customer/cases/{cid}")).status_code == 403
        assert (await client.get("/api/v1/agent/staff/tickets")).status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_resolve_and_customer_confirmation(client):
    app.dependency_overrides[optional_principal] = lambda: Principal("c1", "customer")
    try:
        created = await client.post("/api/v1/agent/customer/chat", json={"message": "Xe mất phanh"})
        cid = created.json()["case_id"]
        app.dependency_overrides[optional_principal] = lambda: Principal("s1", "staff")
        for action in ["APPROVE", "RESOLVE"]:
            response = await client.post(f"/api/v1/agent/staff/tickets/{cid}/actions", json={"action": action})
            assert response.status_code == 200
        app.dependency_overrides[optional_principal] = lambda: Principal("c1", "customer")
        response = await client.post(
            f"/api/v1/agent/customer/cases/{cid}/confirmation", json={"action": "RESOLVED_CONFIRMED"}
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "Closed"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_explicit_old_case_is_rejected_instead_of_writing_to_current_case(client):
    app.dependency_overrides[optional_principal] = lambda: Principal("c1", "customer")
    try:
        body = {"message": "VF8 không sạc được tại nhà lỗi E001", "session_id": "case-selection"}
        first = (await client.post("/api/v1/agent/customer/chat", json=body)).json()["case_id"]
        app.dependency_overrides[optional_principal] = lambda: Principal("s1", "staff")
        for action in ["APPROVE", "RESOLVE"]:
            assert (
                await client.post(f"/api/v1/agent/staff/tickets/{first}/actions", json={"action": action})
            ).status_code == 200
        app.dependency_overrides[optional_principal] = lambda: Principal("c1", "customer")
        second = (await client.post("/api/v1/agent/customer/chat", json=body)).json()["case_id"]
        assert second != first
        response = await client.post("/api/v1/agent/customer/chat", json={**body, "case_id": first})
        assert response.status_code == 409
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_emergency_alert_survives_storage_unavailability(client, monkeypatch):
    import src.agents.chatbot_agent as bridge

    def unavailable():
        raise OSError("Storage unavailable")

    monkeypatch.setattr(bridge, "get_store", unavailable)
    response = await client.post("/api/v1/chat", json={"message": "Xe VF8 mất phanh"})
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == "EMERGENCY_ALERT"
    assert "1900-232389" in data["response"]
    assert data["case_id"] is None
