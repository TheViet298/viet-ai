import io
import json

import httpx
import pytest
from PIL import Image

from src.config import get_settings
from src.models.db_models import Attachment, Case, User

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
    monkeypatch.setattr(settings, "vision_provider", "google")
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
async def test_brake_text_and_visible_icons_are_reported_without_vehicle_model(client, customer_db, gemini):
    result, _ = gemini
    result.update(ocr_text="Lỗi hệ thống trợ lực phanh thủy lực\nLái xe an toàn",
                  symptom_keys=[], wheel_position="unknown", visible_warnings=[
                      {"kind": kind, "color": "yellow", "confidence": .96}
                      for kind in ["turtle", "abs", "brake", "esc", "general_warning"]])
    att = (await client.post("/api/v1/customer/attachments", files={
        "file": ("photo.png", image_bytes(), "image/png"),
    })).json()["data"]
    assert "brake_system_fault" in att["detected_signals"]["symptom_keys"]
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "brake-image", "message": "Tôi gửi ảnh cảnh báo táp-lô",
        "attachment_ids": [att["attachment_id"]],
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["priority"] is None
    assert not data["case_id"]
    assert not data["show_emergency_banner"]
    assert not data["request_location"]
    assert data["suggested_replies"] == ["Xe đang gặp sự cố", "Giải thích về lỗi được nhận diện"]
    assert customer_db.query(Case).count() == 0
    for label in ["trợ lực phanh thủy lực", "rùa", "ABS", "phanh", "xe trượt", "Tam giác"]:
        assert label in data["message"]
    assert "chưa xác định nguyên nhân" in data["message"]
    assert "nội dung chữ, biểu tượng và màu đèn" not in data["message"]
    assert data["safe_guidance"] == "Nếu xe có dấu hiệu nguy hiểm, hãy dừng tại nơi an toàn và liên hệ cứu hộ."
    for question, expected in [
        ("Giải thích về lỗi được nhận diện", "trợ lực phanh"),
        ("biểu tượng rùa vàng là gì", "hạn chế công suất"),
        ("lỗi hệ thống trợ lực phanh thuỷ lực", "lực đạp"),
    ]:
        answer = (await client.post("/api/v1/customer/chat", json={
            "session_id": "brake-image", "message": question,
        })).json()["data"]
        assert expected in answer["message"]
        assert not answer["case_id"]
        assert not answer["show_emergency_banner"]
        assert not answer["request_location"]
        assert customer_db.query(Case).count() == 0
    incident = (await client.post("/api/v1/customer/chat", json={
        "session_id": "brake-image", "message": "Xe đang gặp sự cố",
    })).json()["data"]
    assert incident["priority"] == "CRITICAL"
    assert incident["case_id"]
    assert incident["show_emergency_banner"]
    assert incident["request_location"]
    assert incident["message"] == "**Hotline cứu hộ VinFast:** [1900-232389](tel:1900232389)"
    assert incident["safe_guidance"] == "Nếu xe có dấu hiệu nguy hiểm, hãy dừng tại nơi an toàn và liên hệ cứu hộ."
    assert not incident["citations"]
    assert customer_db.get(Attachment, att["attachment_id"]).case_id == incident["case_id"]
    # Explaining an already-open incident must not lose its binding or create
    # another incident when the customer selects support again.
    await client.post("/api/v1/customer/chat", json={
        "session_id": "brake-image", "message": "Giải thích về lỗi được nhận diện",
    })
    repeated = (await client.post("/api/v1/customer/chat", json={
        "session_id": "brake-image", "message": "Xe đang gặp sự cố",
    })).json()["data"]
    assert repeated["case_id"] == incident["case_id"]
    assert customer_db.query(Case).count() == 1


@pytest.mark.asyncio
async def test_uncertain_icons_and_parking_brake_do_not_become_brake_fault(client, customer_db, gemini):
    result, _ = gemini
    result.update(ocr_text="READY", symptom_keys=["brake_system_fault"], visible_warnings=[
        {"kind": "parking_brake", "color": "red", "confidence": .99},
        {"kind": "turtle", "color": "yellow", "confidence": .3},
    ])
    att = (await client.post("/api/v1/customer/attachments", files={
        "file": ("photo.png", image_bytes(), "image/png"),
    })).json()["data"]
    assert att["detected_signals"]["symptom_keys"] == []
    data = (await client.post("/api/v1/customer/chat", json={
        "session_id": "parking-image", "message": "Xem ảnh", "attachment_ids": [att["attachment_id"]],
    })).json()["data"]
    assert not data["case_id"]
    assert "rùa" not in data["message"]
    assert "phanh đỗ" in data["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize("danger", ["Chân phanh bị kẹt", "Phanh sát sàn", "Xe bị nổ lốp"])
async def test_image_choices_do_not_suppress_live_danger(client, customer_db, gemini, danger):
    att = (await client.post("/api/v1/customer/attachments", files={
        "file": ("photo.png", image_bytes(), "image/png"),
    })).json()["data"]
    await client.post("/api/v1/customer/chat", json={
        "session_id": "image-danger", "message": "Xem ảnh", "attachment_ids": [att["attachment_id"]],
    })
    data = (await client.post("/api/v1/customer/chat", json={
        "session_id": "image-danger", "message": danger,
    })).json()["data"]
    assert data["priority"] == "CRITICAL"
    assert data["case_id"]
    assert data["show_emergency_banner"]


def test_unrelated_explanation_does_not_reuse_image():
    from src.services.dashboard_conversation import dashboard_question
    assert not dashboard_question("Giải thích chính sách bảo hành")
    assert not dashboard_question("Giải thích giá thuê pin")
    assert not dashboard_question("VF 8 có ABS tiêu chuẩn không?")
    assert not dashboard_question("Giá thay má phanh bao nhiêu?")


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["Không có lỗi hệ thống trợ lực phanh",
                                   "Lỗi hệ thống trợ lực phanh không còn",
                                   "No brake system fault"])
async def test_negated_warning_text_does_not_create_fault(client, customer_db, gemini, text):
    result, _ = gemini
    result.update(ocr_text=text, symptom_keys=["brake_system_fault"], wheel_position="unknown")
    att = (await client.post("/api/v1/customer/attachments", files={
        "file": ("photo.png", image_bytes(), "image/png"),
    })).json()["data"]
    assert att["detected_signals"]["symptom_keys"] == []
    data = (await client.post("/api/v1/customer/chat", json={
        "session_id": "no-fault-image", "message": "Xem ảnh", "attachment_ids": [att["attachment_id"]],
    })).json()["data"]
    assert not data["case_id"]


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
    monkeypatch.setattr(get_settings(), "openai_api_key", "")
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
    monkeypatch.setattr(get_settings(), "vision_provider", "google")
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
    monkeypatch.setattr(get_settings(), "vision_provider", "google")
    monkeypatch.setattr(get_settings(), "google_api_key", "test-key")
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


@pytest.mark.asyncio
async def test_analyze_dashboard_image_openai_provider(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock

    import src.services.dashboard_vision_service as dash_mod

    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", True)
    monkeypatch.setattr(settings, "dashboard_vision_enabled", True)
    monkeypatch.setattr(settings, "vision_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "mock-openai-key")
    monkeypatch.setattr(settings, "vision_model", "gpt-6-luna")

    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_completions = MagicMock()

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.finish_reason = "stop"
    mock_choice.message.content = (
        '{"is_dashboard": true, "ocr_text": "Tire pressure low", '
        '"symptom_keys": ["low_pressure"], "confidence": 0.95, '
        '"wheel_position": "rear_right", "observations": ["TPMS warning low tire pressure"]}'
    )
    mock_response.choices = [mock_choice]

    mock_completions.create = AsyncMock(return_value=mock_response)
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat

    monkeypatch.setattr(dash_mod, "get_async_openai_client", lambda: mock_client)

    result = await dash_mod.analyze_dashboard_image(image_bytes(), "image/png")
    assert result.get("evidence_type") in {"GEMINI_VISION", "OPENAI_VISION"}
    assert result.get("is_dashboard") is True
    assert "low_pressure" in result.get("symptom_keys", [])
    assert result.get("wheel_position") == "rear_right"
