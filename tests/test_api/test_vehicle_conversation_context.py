import pytest

from src.models.db_models import Case, CaseBrief

pytest_plugins = ["tests.test_api.test_customer_chat_regressions"]


@pytest.mark.asyncio
async def test_web_remembers_vehicle_and_topic_without_ui_context(client, customer_db, monkeypatch):
    import src.api.customer as api

    calls = []

    async def answer(text, **kwargs):
        calls.append((text, kwargs["client_context"].get("vehicle_model")))
        return {"reply": "Thông tin kiểm thử", "citations": []}

    monkeypatch.setattr(api, "process_chat_message", answer)
    monkeypatch.setattr(api, "answer_sales_question", answer)
    for text in ["VF5 bảo hành bao lâu?", "Pin thì sao?", "Còn VF8?", "So sánh VF5 và VF8"]:
        response = await client.post("/api/v1/customer/chat", json={"session_id": "remember-model", "message": text})
        assert response.status_code == 200
    assert [model for _, model in calls] == ["VF5", "VF5", "VF8", None]
    assert "bảo hành" in calls[1][0].lower()
    assert "bảo hành" in calls[2][0].lower()
    assert "VF5" not in calls[2][0]
    await client.post("/api/v1/customer/chat", json={"session_id": "fresh-model", "message": "Pin bảo hành bao lâu?"})
    assert calls[-1][1] is None


@pytest.mark.asyncio
async def test_advice_vehicle_does_not_become_incident_vehicle(client, customer_db, monkeypatch):
    import src.api.customer as api

    async def answer(*args, **kwargs):
        return {"reply": "Thông tin kiểm thử", "citations": []}

    monkeypatch.setattr(api, "process_chat_message", answer)
    monkeypatch.setattr(api, "answer_sales_question", answer)
    await client.post("/api/v1/customer/chat", json={"session_id": "advice-incident", "message": "Giá VF9 bao nhiêu?"})
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "advice-incident", "message": "Xe tôi không nhận sạc tại trụ P01 mã lỗi CC01",
    })
    data = response.json()["data"]
    assert data["response_type"] == "CLARIFICATION"
    assert "dòng xe" in data["message"].lower()
    assert customer_db.query(Case).filter_by(session_id="advice-incident").count() == 0


@pytest.mark.asyncio
async def test_explicit_incident_model_survives_next_turn(client, customer_db):
    await client.post("/api/v1/customer/chat", json={"session_id": "incident-model", "message": "Xe VF5 của tôi không nhận sạc"})
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "incident-model", "message": "Trụ P01 báo lỗi CC01",
    })
    cid = response.json()["data"]["case_id"]
    assert cid
    assert customer_db.get(Case, cid).vehicle_model == "VF5"
    assert customer_db.query(CaseBrief).filter_by(case_id=cid).first().captured_fields["vehicle_model"] == "VF5"


@pytest.mark.asyncio
async def test_model_answer_completes_incident_without_losing_prior_details(client, customer_db):
    first = await client.post("/api/v1/customer/chat", json={
        "session_id": "fill-model", "message": "Xe tôi không nhận sạc tại trụ P01 mã lỗi CC01",
        "client_context": {},
    })
    assert first.json()["data"]["response_type"] == "CLARIFICATION"
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "fill-model", "message": "VF5", "client_context": {},
    })
    data = response.json()["data"]
    assert data["response_type"] == "CASE_CREATED"
    assert customer_db.get(Case, data["case_id"]).vehicle_model == "VF5"


@pytest.mark.asyncio
async def test_vehicle_memory_is_scoped_to_customer(client, customer_db, monkeypatch):
    import src.api.customer as api
    from src.main import app
    from src.models.db_models import User
    from src.services.auth import get_optional_user

    calls = []

    async def answer(text, **kwargs):
        calls.append(kwargs["client_context"].get("vehicle_model"))
        return {"reply": "Thông tin kiểm thử", "citations": []}

    monkeypatch.setattr(api, "process_chat_message", answer)
    await client.post("/api/v1/customer/chat", json={"session_id": "shared-name", "message": "VF5 bảo hành bao lâu?"})
    other = User(id="other-customer", username="other", password_hash="unused", role="CUSTOMER")
    customer_db.add(other)
    customer_db.commit()
    app.dependency_overrides[get_optional_user] = lambda: other
    response = await client.post("/api/v1/customer/chat", json={"session_id": "shared-name", "message": "Pin bảo hành bao lâu?"})
    assert response.status_code == 403
    assert calls == ["VF5"]


@pytest.mark.asyncio
async def test_incident_slot_followup_keeps_model_and_previous_error(client, customer_db):
    await client.post("/api/v1/customer/chat", json={
        "session_id": "incident-slots", "message": "Xe VF5 của tôi không nhận sạc, mã lỗi CC01",
    })
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "incident-slots", "message": "Trụ P01",
    })
    data = response.json()["data"]
    assert data["response_type"] == "CASE_CREATED"
    brief = customer_db.query(CaseBrief).filter_by(case_id=data["case_id"]).first()
    assert brief.captured_fields["vehicle_model"] == "VF5"
    assert brief.captured_fields["error_code"] == "CC01"


@pytest.mark.asyncio
async def test_model_completion_preserves_station_across_incident_turns(client, customer_db):
    for text in ["Xe tôi không nhận sạc tại Vincom Metropolis", "Trụ P01 báo lỗi CC01", "VF5"]:
        response = await client.post("/api/v1/customer/chat", json={
            "session_id": "retain-station", "message": text,
        })
    data = response.json()["data"]
    brief = customer_db.query(CaseBrief).filter_by(case_id=data["case_id"]).first()
    assert "Metropolis" in brief.captured_fields["station_location"]
    assert brief.captured_fields["vehicle_model"] == "VF5"
