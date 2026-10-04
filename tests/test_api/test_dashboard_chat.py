import pytest

from src.models.db_models import Case, CaseBrief

pytest_plugins = ["tests.test_api.test_customer_chat_regressions"]


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["VF8", "VF 5 Plus", "VF e34"])
async def test_low_pressure_uses_model_dataset(client, customer_db, model):
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "tpms", "message": "Táp-lô báo áp suất lốp thấp",
        "client_context": {"vehicle_model": model},
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["response_type"] == "FAQ_ANSWER"
    assert data["priority"] == "MEDIUM"
    assert data["citations"][0]["url"].startswith("https://vinfastauto.com/")
    assert data["citations"][0]["verified_at"] is None
    assert "áp suất" in data["safe_guidance"]
    assert customer_db.query(Case).count() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("text,priority", [
    ("VF e34 báo rò rỉ áp suất lốp nhanh", "HIGH"),
    ("VF e34 đèn cảnh báo hệ thống phanh đỏ", "CRITICAL"),
])
async def test_dashboard_escalation_persists_evidence(client, customer_db, text, priority):
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "danger", "message": text,
        "client_context": {"vehicle_model": "VF8"},
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["response_type"] == "CASE_CREATED"
    assert data["priority"] == priority
    case = customer_db.get(Case, data["case_id"])
    assert case.vehicle_model == "VFE34"
    brief = customer_db.query(CaseBrief).filter_by(case_id=case.id).one()
    assert brief.captured_fields["dashboard_warning_ids"]
    assert data["citations"]


@pytest.mark.asyncio
@pytest.mark.parametrize("message,context", [
    ("Táp-lô báo áp suất lốp thấp", {"vehicle_model": "VF9"}),
    ("Táp-lô báo áp suất lốp thấp", {}),
    ("Táp-lô sáng đèn TPMS", {"vehicle_model": "VF8"}),
    ("VF8 báo áp suất lốp thấp và áp suất lốp quá cao", {}),
])
async def test_uncertain_dashboard_asks_then_hands_off(client, customer_db, message, context):
    payload = {"session_id": "unknown", "message": message, "client_context": context}
    for turn in (1, 2):
        data = (await client.post("/api/v1/customer/chat", json=payload)).json()["data"]
        assert data["response_type"] == "CLARIFICATION"
        assert data["clarification_turn"] == turn
        assert "trạm sạc" not in data["message"].lower()
    data = (await client.post("/api/v1/customer/chat", json=payload)).json()["data"]
    assert data["response_type"] == "CASE_CREATED"
    assert data["priority"] != "LOW"
    assert not data["citations"]


@pytest.mark.asyncio
async def test_model_answer_resolves_pending_dashboard_warning(client, customer_db):
    first = await client.post("/api/v1/customer/chat", json={
        "session_id": "followup", "message": "Táp-lô báo áp suất lốp thấp",
    })
    assert first.json()["data"]["response_type"] == "CLARIFICATION"
    second = await client.post("/api/v1/customer/chat", json={
        "session_id": "followup", "message": "VF e34",
    })
    data = second.json()["data"]
    assert data["response_type"] == "FAQ_ANSWER"
    assert data["citations"][0]["source_id"] == "vfe34-tpms-low-pressure"


@pytest.mark.asyncio
@pytest.mark.parametrize("message", [
    "VF9 đèn phanh đỏ", "VF e34 đèn phanh đỏ và áp suất lốp thấp",
])
async def test_unresolved_danger_escalates_without_model_claim(client, customer_db, message):
    data = (await client.post("/api/v1/customer/chat", json={
        "session_id": "unknown-danger", "message": message,
    })).json()["data"]
    assert data["response_type"] == "CASE_CREATED"
    assert data["priority"] == "CRITICAL"
    assert not data["citations"]


@pytest.mark.asyncio
async def test_multiple_models_need_clarification(client, customer_db):
    data = (await client.post("/api/v1/customer/chat", json={
        "session_id": "models", "message": "VF8 hay VF e34 báo áp suất lốp thấp",
    })).json()["data"]
    assert data["response_type"] == "CLARIFICATION"
    assert not data["citations"]
    data = (await client.post("/api/v1/customer/chat", json={
        "session_id": "models", "message": "Xe tôi là VF e34",
    })).json()["data"]
    assert data["citations"][0]["source_id"] == "vfe34-tpms-low-pressure"


@pytest.mark.asyncio
async def test_unknown_brief_keeps_clarification_evidence(client, customer_db, monkeypatch):
    from datetime import UTC, datetime
    from itertools import count
    from uuid import UUID

    import src.api.customer as api
    import src.models.db_models as models

    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2030, 1, 1, tzinfo=UTC).astimezone(tz)

    ids = count()
    monkeypatch.setattr(api, "datetime", FixedClock)
    monkeypatch.setattr(models, "datetime", FixedClock)
    monkeypatch.setattr(api.uuid, "uuid4", lambda: UUID(int=(1 << 128) - 1 - next(ids)))
    for message in ("Táp-lô báo cảnh báo lạ", "VF e34", "Đèn vàng liên tục"):
        data = (await client.post("/api/v1/customer/chat", json={
            "session_id": "evidence", "message": message,
        })).json()["data"]
    brief = customer_db.query(CaseBrief).filter_by(case_id=data["case_id"]).one()
    assert "cảnh báo lạ" in brief.captured_fields["raw_inquiry"]
    assert "VF e34" in brief.captured_fields["raw_inquiry"]
