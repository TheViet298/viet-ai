import io

import pytest
from PIL import Image

pytest_plugins = ["tests.test_api.test_customer_chat_regressions"]


def picture():
    buffer = io.BytesIO()
    Image.new("RGB", (24, 24), "white").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["exterior", "dashboard", "charger", "unknown"])
async def test_auto_route_uses_only_selected_analyzer(client, customer_db, monkeypatch, kind):
    import src.api.customer as api
    calls = []
    async def classify(*args):
        return {"image_kind": kind, "confidence": .96 if kind != "unknown" else .2}
    async def dashboard(*args):
        calls.append("dashboard")
        return {"evidence_type": "GEMINI_VISION", "is_dashboard": True, "ocr_text": "READY", "confidence": .9}
    async def damage(path, image_id):
        calls.append("exterior")
        return {"schema_version": "1.0", "image_id": image_id,
                "damage": {"status": "no_detection", "detections": []}}
    monkeypatch.setattr(api, "classify_vehicle_image", classify, raising=False)
    monkeypatch.setattr(api, "analyze_dashboard_image", dashboard)
    monkeypatch.setattr(api, "analyze_exterior_image", damage)
    response = await client.post("/api/v1/customer/attachments", data={"image_kind": "auto"},
                                 files={"file": ("random-name.png", picture(), "image/png")})
    assert response.status_code == 200
    attachment = response.json()["data"]
    assert attachment["detected_signals"]["image_kind"] == kind
    assert calls == (["exterior"] if kind == "exterior" else ["dashboard"] if kind in {"dashboard", "charger"} else [])
    if kind == "unknown":
        assert attachment["analysis_status"] == "FAILED"
        chat = await client.post("/api/v1/customer/chat", json={
            "session_id": "unknown-image", "message": "Xem ảnh giúp", "attachment_ids": [attachment["attachment_id"]]})
        data = chat.json()["data"]
        assert data["response_type"] == "CLARIFICATION"
        assert "loại ảnh" in data["message"].casefold()
        assert data["case_id"] is None

