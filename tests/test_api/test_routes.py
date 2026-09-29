import pytest
from types import SimpleNamespace

from src.api import routes
from src.main import app
from src.services.case_store import CaseStore


@pytest.fixture
def api_store(monkeypatch):
    store = CaseStore("sqlite:///:memory:")
    async def test_store():
        return store
    app.dependency_overrides[routes.get_case_store] = test_store
    monkeypatch.setattr(routes, "get_settings", lambda: SimpleNamespace(
        staff_api_token="test-token", staff_id="reviewer-test"
    ))
    yield store
    app.dependency_overrides.pop(routes.get_case_store, None)
    store.close()


SESSION = {"X-Session-Id": "demo-session-001"}
STAFF = {"Authorization": "Bearer test-token"}
CHAT = {
    "session_id": "demo-session-001",
    "message": "Xe VF8 không nhận sạc tại trạm Metropolis.",
    "client_context": {"mock_customer_id": "MOCK-001", "vehicle_model": "VF8"},
}


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_empty_message(client, api_store):
    response = await client.post("/api/v1/customer/chat", json={**CHAT, "message": ""})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_agent_status(client):
    response = await client.get("/api/v1/status")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_case_approval_customer_status_and_audit(client, api_store):
    created = await client.post("/api/v1/customer/chat", json=CHAT)
    assert created.status_code == 200
    data = created.json()["data"]
    assert data["response_type"] == "CASE_CREATED"
    assert data["status"] == "Staff Reviewing"
    assert "analysis" not in str(created.json()).lower()
    case_id = data["case_id"]

    unauthorized = await client.get("/api/v1/staff/tickets")
    assert unauthorized.status_code == 403
    bad_token = await client.get("/api/v1/staff/tickets", headers={"Authorization": "Bearer wrong"})
    assert bad_token.status_code == 403
    queue = await client.get("/api/v1/staff/tickets", headers=STAFF)
    assert queue.status_code == 200
    assert queue.json()["data"]["total"] == 1

    detail = await client.get(f"/api/v1/staff/tickets/{case_id}", headers=STAFF)
    assert detail.status_code == 200
    assert detail.json()["data"]["case_brief"]["summary"] == CHAT["message"]
    assert {row["action"] for row in detail.json()["data"]["audit"]} >= {"CREATE", "TRIAGE"}

    approved = await client.post(f"/api/v1/staff/tickets/{case_id}/actions",
                                 json={"action": "APPROVE", "notes": "Reviewed"}, headers=STAFF)
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "In Progress"
    updated = await client.get(f"/api/v1/customer/cases/{case_id}/status", headers=SESSION)
    assert updated.status_code == 200
    assert updated.json()["data"]["status"] == "In Progress"
    assert "case_brief" not in updated.json()["data"]
    assert "confidence_score" not in updated.json()["data"]

    repeated = await client.post(f"/api/v1/staff/tickets/{case_id}/actions",
                                 json={"action": "APPROVE"}, headers=STAFF)
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "INVALID_TRANSITION"
    detail = await client.get(f"/api/v1/staff/tickets/{case_id}", headers=STAFF)
    actions = detail.json()["data"]["audit"]
    assert any(row["action"] == "APPROVE" and row["actor"] == "STAFF:reviewer-test"
               and row["from_status"] == "Staff Reviewing" and row["to_status"] == "In Progress"
               for row in actions)


@pytest.mark.asyncio
async def test_customer_ownership_and_resolution_transitions(client, api_store):
    case_id = (await client.post("/api/v1/customer/chat", json=CHAT)).json()["data"]["case_id"]
    path = f"/api/v1/customer/cases/{case_id}/status"
    assert (await client.get(path, headers={"X-Session-Id": "different-session"})).status_code == 403
    assert (await client.get(path)).status_code == 403
    premature = await client.post(f"/api/v1/customer/cases/{case_id}/actions",
                                  json={"action": "CONFIRM_RESOLUTION"}, headers=SESSION)
    assert premature.status_code == 409
    await client.post(f"/api/v1/staff/tickets/{case_id}/actions", json={"action": "APPROVE"}, headers=STAFF)
    resolved = await client.post(f"/api/v1/staff/tickets/{case_id}/actions",
                                 json={"action": "RESOLVE", "notes": "Demo resolution"}, headers=STAFF)
    assert resolved.json()["data"]["status"] == "Resolved"
    closed = await client.post(f"/api/v1/customer/cases/{case_id}/actions",
                               json={"action": "CONFIRM_RESOLUTION"}, headers=SESSION)
    assert closed.json()["data"]["status"] == "Closed"
    reopened = await client.post(f"/api/v1/customer/cases/{case_id}/actions",
                                 json={"action": "REOPEN", "reason": "Problem returned"}, headers=SESSION)
    assert reopened.json()["data"]["status"] == "Staff Reviewing"
    assert [row["action"] for row in api_store.detail(case_id)["audit"]][-2:] == ["REOPEN", "QUEUE_REOPENED"]


@pytest.mark.asyncio
async def test_clarification_limit_and_no_pii_fields(client, api_store):
    chat = {"session_id": "demo-session-002", "message": "Xe không nhận sạc"}
    first = await client.post("/api/v1/customer/chat", json=chat)
    assert first.json()["data"]["response_type"] == "CLARIFICATION"
    assert first.json()["data"]["case_id"] is None
    second = await client.post("/api/v1/customer/chat", json=chat)
    assert second.json()["data"]["clarification_turn"] == 2
    third = await client.post("/api/v1/customer/chat", json=chat)
    assert third.json()["data"]["status"] == "Needs Information"
    forbidden_context = await client.post("/api/v1/customer/chat", json={
        **CHAT, "client_context": {"name": "Demo"}
    })
    assert forbidden_context.status_code == 422
    forbidden_message = await client.post("/api/v1/customer/chat", json={
        **CHAT, "message": "Contact test@example.com about charging"
    })
    assert forbidden_message.status_code == 400


@pytest.mark.asyncio
async def test_staff_cannot_self_declare_identity_or_status(client, api_store):
    case_id = (await client.post("/api/v1/customer/chat", json=CHAT)).json()["data"]["case_id"]
    response = await client.post(f"/api/v1/staff/tickets/{case_id}/actions", headers=STAFF,
                                 json={"action": "APPROVE", "staff_id": "forged", "updated_status": "Closed"})
    assert response.status_code == 422
    assert api_store.require_case(case_id)["status"] == "Staff Reviewing"


@pytest.mark.asyncio
async def test_staff_reroute_persists_team_and_audits_action(client, api_store):
    case_id = (await client.post("/api/v1/customer/chat", json=CHAT)).json()["data"]["case_id"]
    response = await client.post(f"/api/v1/staff/tickets/{case_id}/actions", headers=STAFF,
                                 json={"action": "REROUTE", "target_team": "Demo service team"})
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "In Progress"
    assert api_store.get_brief(case_id)["suggested_routing"] == "Demo service team"
    assert api_store.detail(case_id)["audit"][-1]["action"] == "REROUTE"
