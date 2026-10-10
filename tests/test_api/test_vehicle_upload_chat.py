import io
import pytest
from PIL import Image

pytest_plugins = ["tests.test_api.test_customer_chat_regressions"]


def dummy_image():
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), "blue").save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_exterior_upload_triggers_vehicle_model_instead_of_cardd(client, customer_db, monkeypatch):
    import src.api.customer as api

    async def mock_recognize(data, mime):
        return {
            "status": "candidate",
            "model_label": "VF 3",
            "candidates": [{"label": "VF 3", "confidence": 0.95}],
            "model_version": "gpt-6-luna",
            "threshold": 0.7,
            "requires_user_confirmation": True,
        }

    monkeypatch.setattr(api, "recognize_vehicle_model", mock_recognize, raising=False)

    upload = await client.post(
        "/api/v1/customer/attachments",
        data={"image_kind": "exterior"},
        files={"file": ("car.png", dummy_image(), "image/png")},
    )
    assert upload.status_code == 200
    data = upload.json()["data"]
    signals = data["detected_signals"]
    assert signals["evidence_type"] == "VEHICLE_MODEL"
    assert signals["vehicle_model"] == "VF 3"
    assert "CARDD" not in signals.get("evidence_type", "")


@pytest.mark.asyncio
async def test_chat_uses_recognized_vehicle_model_from_attachment(client, customer_db, monkeypatch):
    import src.api.customer as api

    async def mock_recognize(data, mime):
        return {
            "status": "candidate",
            "model_label": "VF 7",
            "candidates": [{"label": "VF 7", "confidence": 0.92}],
            "model_version": "gpt-6-luna",
            "threshold": 0.7,
            "requires_user_confirmation": True,
        }

    monkeypatch.setattr(api, "recognize_vehicle_model", mock_recognize, raising=False)

    upload = await client.post(
        "/api/v1/customer/attachments",
        data={"image_kind": "exterior"},
        files={"file": ("car.png", dummy_image(), "image/png")},
    )
    attachment_id = upload.json()["data"]["attachment_id"]

    chat = await client.post(
        "/api/v1/customer/chat",
        json={
            "session_id": "test-vehicle-model-chat",
            "message": "Đây là xe gì?",
            "attachment_ids": [attachment_id],
        },
    )
    assert chat.status_code == 200
    reply = chat.json()["data"]["message"]
    assert "VF 7" in reply or "VinFast" in reply
