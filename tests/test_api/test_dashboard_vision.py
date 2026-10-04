import io
import json

import httpx
import pytest
from PIL import Image

from src.config import get_settings
from src.models.db_models import Attachment, User

pytest_plugins = ["tests.test_api.test_customer_chat_regressions"]


def image_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), "white").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def gemini(monkeypatch):
    import src.services.dashboard_vision_service as vision

    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", True)
    monkeypatch.setattr(settings, "google_api_key", "test-key")
    monkeypatch.setattr(settings, "dashboard_vision_model", "gemini-3.5-flash")
    result = {
        "is_dashboard": True, "ocr_text": "Tire pressure low",
        "symptom_keys": ["low_pressure", "seatbelt_warning", "ready_mode_indicator"],
        "confidence": 0.95, "wheel_position": "rear_right", "observations": ["red rear right wheel"],
    }
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": json.dumps(result)}],
        }}]})

    monkeypatch.setattr(vision, "AsyncClient", lambda **kwargs: httpx.AsyncClient(
        transport=httpx.MockTransport(handler), **kwargs,
    ))
    return result, requests


@pytest.mark.asyncio
async def test_image_content_drives_upload_and_chat(client, customer_db, gemini):
    result, requests = gemini
    response = await client.post("/api/v1/customer/attachments", files={
        "file": ("charger_cc01_turtle.png", image_bytes(), "image/png"),
    })
    assert response.status_code == 200
    attachment = response.json()["data"]
    assert attachment["ocr_text"] == "Tire pressure low"
    assert attachment["detected_signals"]["symptom_keys"] == ["low_pressure"]
    assert "error_code_candidate" not in attachment["detected_signals"]
    body = json.loads(requests[0].content)
    assert "/models/gemini-3.5-flash:generateContent" in str(requests[0].url)
    assert body["contents"][0]["parts"][1]["inlineData"]["mimeType"] == "image/png"
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "vision", "message": "Ảnh này báo gì?",
        "attachment_ids": [attachment["attachment_id"]], "client_context": {"vehicle_model": "VF e34"},
    })
    data = response.json()["data"]
    assert data["citations"][0]["source_id"] == "vfe34-tpms-low-pressure"
    assert "Tire pressure low" in data["message"]
    assert "sau bên phải" in data["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize("confidence,keys", [(0.3, ["low_pressure"]), (0.99, [])])
async def test_uncertain_image_does_not_invent_symptom(client, customer_db, gemini, confidence, keys):
    result, _ = gemini
    result.update(confidence=confidence, symptom_keys=keys, ocr_text="Kiểm tra lốp bên phải phía sau")
    att = (await client.post("/api/v1/customer/attachments", files={
        "file": ("low_pressure.png", image_bytes(), "image/png"),
    })).json()["data"]
    data = (await client.post("/api/v1/customer/chat", json={
        "session_id": "uncertain", "message": "Xem ảnh giúp", "attachment_ids": [att["attachment_id"]],
        "client_context": {"vehicle_model": "VF e34"},
    })).json()["data"]
    assert data["response_type"] == "CLARIFICATION"
    assert not data["citations"]


@pytest.mark.asyncio
async def test_invalid_image_is_rejected(client, customer_db):
    response = await client.post("/api/v1/customer/attachments", files={
        "file": ("tpms.png", b"not-an-image", "image/png"),
    })
    assert response.status_code == 400
    assert customer_db.query(Attachment).count() == 0


@pytest.mark.asyncio
async def test_missing_key_preserves_upload_without_fake_ocr(client, customer_db, monkeypatch):
    monkeypatch.setattr(get_settings(), "google_api_key", "")
    response = await client.post("/api/v1/customer/attachments", files={
        "file": ("cc01.png", image_bytes(), "image/png"),
    })
    data = response.json()["data"]
    assert data["analysis_status"] == "FAILED"
    assert data["ocr_text"] is None
    assert data["vision_confidence"] is None


@pytest.mark.asyncio
async def test_foreign_attachment_cannot_be_used(client, customer_db, gemini):
    att = (await client.post("/api/v1/customer/attachments", files={
        "file": ("a.png", image_bytes(), "image/png"),
    })).json()["data"]
    from src.main import app
    from src.services.auth import get_optional_user, require_customer

    other = User(id="other", username="other", password_hash="unused", role="CUSTOMER")
    customer_db.add(other)
    customer_db.commit()
    app.dependency_overrides[require_customer] = lambda: other
    app.dependency_overrides[get_optional_user] = lambda: other
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "foreign", "message": "Xem ảnh", "attachment_ids": [att["attachment_id"]],
    })
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_provider_auth_error_is_safe_and_actionable(monkeypatch):
    from src.services import dashboard_vision_service as vision

    monkeypatch.setattr(get_settings(), "agent_llm_enabled", True)
    monkeypatch.setattr(get_settings(), "google_api_key", "private-key")
    def handler(request):
        return httpx.Response(401, json={"error": {"message": "private-key"}})
    monkeypatch.setattr(vision, "AsyncClient", lambda **kwargs: httpx.AsyncClient(
        transport=httpx.MockTransport(handler), **kwargs,
    ))
    signals = await vision.analyze_dashboard_image(image_bytes(), "image/png")
    assert signals["analysis_error"] == "vision_authentication_failed"
    assert "private-key" not in json.dumps(signals)


@pytest.mark.asyncio
async def test_legacy_image_on_own_case_remains_accessible(client, customer_db, gemini):
    case = (await client.post("/api/v1/customer/chat", json={
        "session_id": "legacy", "message": "Xe có khói",
    })).json()["data"]["case_id"]
    uploaded = (await client.post("/api/v1/customer/attachments", files={
        "file": ("a.png", image_bytes(), "image/png"),
    })).json()["data"]
    att = customer_db.get(Attachment, uploaded["attachment_id"])
    att.detected_signals = {key: value for key, value in att.detected_signals.items() if key != "owner_user_id"}
    att.case_id = case
    customer_db.commit()
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "legacy", "message": "Xem ảnh", "attachment_ids": [att.id],
        "client_context": {"vehicle_model": "VF e34"},
    })
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_transient_overload_retries_then_reads_image(monkeypatch):
    from src.services import dashboard_vision_service as vision

    monkeypatch.setattr(get_settings(), "agent_llm_enabled", True)
    attempts = []
    def handler(request):
        attempts.append(request)
        if len(attempts) == 1:
            return httpx.Response(503, json={"error": {"status": "UNAVAILABLE"}})
        observation = {"is_dashboard": True, "ocr_text": "Tire pressure sensor fault",
                       "symptom_keys": ["sensor_fault"], "confidence": 0.95,
                       "wheel_position": "front_left", "observations": []}
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": json.dumps(observation)}],
        }}]})
    monkeypatch.setattr(vision, "AsyncClient", lambda **kwargs: httpx.AsyncClient(
        transport=httpx.MockTransport(handler), **kwargs,
    ))
    signals = await vision.analyze_dashboard_image(image_bytes(), "image/png")
    assert signals.get("symptom_keys") == ["sensor_fault"]
