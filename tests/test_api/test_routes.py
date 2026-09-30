import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_empty_message(client):
    response = await client.post("/api/v1/chat", json={"message": ""})
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_chat_valid_message(client):
    response = await client.post(
        "/api/v1/chat",
        json={"message": "Thời hạn bảo hành xe VinFast VF 8 là bao lâu?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0
    assert "citations" in data
    assert "intent" in data


@pytest.mark.asyncio
async def test_customer_chat_envelope_contract(client):
    """Kiểm tra tuân thủ Response Envelope Format theo docs/architecture/api-contract.md."""
    response = await client.post(
        "/api/v1/customer/chat",
        json={
            "session_id": "sess_demo_01",
            "message": "Hướng dẫn đặt lịch bảo dưỡng xe trên app VinFast"
        }
    )
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert "data" in res
    assert "meta" in res
    assert "timestamp" in res["meta"]
    assert res["data"]["response_type"] in ("FAQ_ANSWER", "CLARIFICATION", "NO_SOURCE")
    assert "citations" in res["data"]


@pytest.mark.asyncio
async def test_customer_chat_emergency_safety(client):
    """Kiểm tra an toàn khẩn cấp qua endpoint /customer/chat."""
    response = await client.post(
        "/api/v1/customer/chat",
        json={
            "session_id": "sess_demo_emergency",
            "message": "Xe đang chạy trên đường bốc khói đen và khét lẹt dưới gầm!"
        }
    )
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert res["data"]["is_safety_trigger"] is True
    assert res["data"]["priority"] == "critical"
    assert res["data"]["response_type"] == "SAFETY_ALERT"
    assert "1900-232389" in res["data"]["message"]


@pytest.mark.asyncio
async def test_agent_status(client):
    response = await client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
