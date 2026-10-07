import io

import pytest
from PIL import Image

from src.agents.cardd_evidence import CONFIRM, REJECT
from src.models.db_models import Case, CaseBrief

pytest_plugins = ["tests.test_api.test_customer_chat_regressions"]


def photo_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "gray").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def damage_runtime(monkeypatch):
    import src.api.customer as api

    async def analyze(path, image_id):
        return {
            "schema_version": "1.0", "image_id": image_id,
            "damage": {"status": "detected", "model_version": "a" * 64,
                       "threshold": 0.25,
                       "detections": [{"label": "dent", "confidence": 0.29,
                                       "bbox_xyxy": [0.1, 0.1, 0.8, 0.7]}]},
        }

    async def dashboard(*args, **kwargs):
        pytest.fail("An exterior upload must not use dashboard OCR")

    monkeypatch.setattr(api, "analyze_exterior_image", analyze, raising=False)
    monkeypatch.setattr(api, "analyze_dashboard_image", dashboard)


@pytest.mark.asyncio
async def test_exterior_upload_confirmation_and_staff_brief(client, customer_db, damage_runtime):
    upload = await client.post("/api/v1/customer/attachments", data={"image_kind": "exterior"},
                               files={"file": ("car.png", photo_bytes(), "image/png")})
    assert upload.status_code == 200
    attachment = upload.json()["data"]
    assert attachment["ocr_text"] is None
    assert attachment["detected_signals"]["evidence_type"] == "CARDD"
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "exterior-review", "message": "Xem ảnh ngoại thất giúp tôi",
        "attachment_ids": [attachment["attachment_id"]], "client_context": {"vehicle_model": "VF8"},
    })
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["suggested_replies"] == [CONFIRM, REJECT]
    assert "móp" in result["message"]
    assert "táp-lô" not in result["message"]
    assert result["visual_evidence"]["confirmation"] == "unconfirmed"
    assert result["case_id"] is None
    for message in [CONFIRM, "Xe vẫn chạy bình thường"]:
        response = await client.post("/api/v1/customer/chat", json={
            "session_id": "exterior-review", "message": message,
            "client_context": {"vehicle_model": "VF8"},
        })
        assert response.status_code == 200
    result = response.json()["data"]
    case = customer_db.get(Case, result["case_id"])
    assert case and case.user_id == "regression-customer"
    brief = customer_db.query(CaseBrief).filter_by(case_id=case.id).one()
    assert brief.captured_fields["visual_evidence"]["confirmation"] == "confirmed"
    assert "warning_symbol" not in brief.captured_fields


@pytest.mark.asyncio
async def test_invalid_image_kind_is_rejected(client, customer_db):
    response = await client.post("/api/v1/customer/attachments", data={"image_kind": "fake"},
                                 files={"file": ("car.png", photo_bytes(), "image/png")})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_cardd_failure_is_visible_without_dashboard_ocr(client, customer_db, monkeypatch):
    import src.api.customer as api

    async def unavailable(path, image_id):
        return {"image_id": image_id, "damage": {"status": "unavailable", "reason": "inference_timeout"}}

    monkeypatch.setattr(api, "analyze_exterior_image", unavailable)
    upload = await client.post("/api/v1/customer/attachments", data={"image_kind": "exterior"},
                               files={"file": ("car.png", photo_bytes(), "image/png")})
    attachment = upload.json()["data"]
    assert attachment["analysis_status"] == "FAILED"
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "failed-inference", "message": "Xem ảnh ngoại thất",
        "attachment_ids": [attachment["attachment_id"]],
    })
    result = response.json()["data"]
    assert result["visual_evidence"]["status"] == "unavailable"
    assert "táp-lô" not in result["message"]
    assert result["case_id"] is None


@pytest.mark.asyncio
async def test_emergency_text_precedes_exterior_confirmation(client, customer_db, damage_runtime):
    upload = await client.post("/api/v1/customer/attachments", data={"image_kind": "exterior"},
                               files={"file": ("car.png", photo_bytes(), "image/png")})
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "damage-emergency", "message": "Xe đang bốc khói",
        "attachment_ids": [upload.json()["data"]["attachment_id"]],
    })
    result = response.json()["data"]
    assert result["priority"] == "CRITICAL"
    assert result["show_emergency_banner"] is True
    assert CONFIRM not in (result["suggested_replies"] or [])


@pytest.mark.asyncio
async def test_other_customer_cannot_reuse_exterior_upload(client, customer_db, damage_runtime):
    from src.main import app
    from src.models.db_models import User
    from src.services.auth import get_optional_user

    upload = await client.post("/api/v1/customer/attachments", data={"image_kind": "exterior"},
                               files={"file": ("car.png", photo_bytes(), "image/png")})
    other = User(id="other-cardd", username="other-cardd", password_hash="unused", role="CUSTOMER")
    customer_db.add(other)
    customer_db.commit()
    app.dependency_overrides[get_optional_user] = lambda: other
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "foreign-damage", "message": "Xem ảnh ngoại thất",
        "attachment_ids": [upload.json()["data"]["attachment_id"]],
    })
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_exterior_flow_keeps_vehicle_confirmed_in_chat(client, customer_db, damage_runtime):
    import json

    from src.models.db_models import ChatSession
    from src.services.session_store import decode_state

    await client.post("/api/v1/customer/chat", json={
        "session_id": "owned-photo", "message": "Tôi đang sử dụng xe VF5",
    })
    upload = await client.post("/api/v1/customer/attachments", data={"image_kind": "exterior"},
                               files={"file": ("car.png", photo_bytes(), "image/png")})
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "owned-photo", "message": "Ảnh đây",
        "attachment_ids": [upload.json()["data"]["attachment_id"]],
    })
    assert response.status_code == 200
    session = customer_db.get(ChatSession, 'owned-photo')
    state = session.memory_states['cardd:regression-customer:owned-photo']
    assert decode_state(json.dumps(state))["captured_fields"]["vehicle_model"] == "VF5"
