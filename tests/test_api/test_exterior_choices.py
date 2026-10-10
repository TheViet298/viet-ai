import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.config import get_settings
from src.models.db_models import Attachment, Case, CaseBrief
from tests.test_api.test_vehicle_upload_chat import dummy_image

pytest_plugins = ["tests.test_api.test_customer_chat_regressions"]


@pytest.mark.asyncio
@pytest.mark.parametrize("supported_severity", ["severe", "minor"])
async def test_model_filters_uncertain_damage_without_losing_visible_damage(monkeypatch, supported_severity):
    import src.services.vehicle_vision_service as vision
    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    result = {"is_vinfast": True, "vehicle_model": "VF 3", "confidence": .93,
              "candidates": [], "damages": [
                  {"part": "cửa hậu", "location": "phía sau", "description": "móp, biến dạng", "confidence": .95, "severity": supported_severity},
                  {"part": "thân xe", "location": "gầm", "description": "không rõ hư hại", "confidence": .3, "severity": "severe"}],
              "severity": "severe"}
    create = AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(
        finish_reason="stop", message=SimpleNamespace(content=json.dumps(result)))]))
    monkeypatch.setattr(vision, "get_async_openai_client", lambda: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    observation = (await vision.recognize_vehicle_model(b"image", "image/png"))["exterior_observation"]
    assert len(observation["damages"]) == 1
    assert observation["damages"][0]["part"] == "cửa hậu"
    assert observation["severity"] == supported_severity


@pytest.mark.asyncio
async def test_image_choices_gate_case_and_restore_same_case(client, customer_db, monkeypatch):
    import src.api.customer as api
    async def recognize(*args):
        return {"status": "candidate", "model_label": "VF 3", "candidates": [{"confidence": .94}],
                "exterior_observation": {"damages": [{"part": "cửa hậu", "location": "phía sau",
                    "description": "móp, biến dạng", "confidence": .95}], "severity": "severe"}}
    monkeypatch.setattr(api, "recognize_vehicle_model", recognize)
    att = (await client.post("/api/v1/customer/attachments", data={"image_kind": "exterior"},
        files={"file": ("car.png", dummy_image(), "image/png")})).json()["data"]
    data = (await client.post("/api/v1/customer/chat", json={"session_id": "exterior-choice",
        "message": "Tôi gửi ảnh xe", "attachment_ids": [att["attachment_id"]]})).json()["data"]
    assert data["suggested_replies"] == ["Xe đang gặp sự cố", "Tư vấn sửa chữa và bảo hành"]
    assert "cửa hậu" in data["message"]
    assert not data["show_emergency_banner"] and not data["request_location"]
    assert customer_db.query(Case).count() == 0
    # Ownership is checked again on contextual follow-ups.
    stored = customer_db.get(Attachment, att["attachment_id"])
    original = stored.detected_signals
    stored.detected_signals = {**original, "owner_user_id": "another-user"}
    customer_db.commit()
    denied = await client.post("/api/v1/customer/chat", json={"session_id": "exterior-choice", "message": "Xe đang gặp sự cố"})
    assert denied.status_code == 403
    stored.detected_signals = original
    customer_db.commit()
    incident = (await client.post("/api/v1/customer/chat", json={"session_id": "exterior-choice",
        "message": "Xe đang gặp sự cố"})).json()["data"]
    assert incident["show_emergency_banner"] and incident["request_location"]
    assert "1900-232389" in incident["message"]
    assert "cửa hậu" not in incident["message"]
    assert customer_db.query(Case).count() == 1
    import src.services.exterior_conversation as conversation
    async def no_source(*args):
        return "Chưa có tài liệu đủ để xác nhận bảo hành.", []
    monkeypatch.setattr(conversation, "warranty_answer", no_source)
    advice = (await client.post("/api/v1/customer/chat", json={"session_id": "exterior-choice",
        "message": "Tư vấn sửa chữa và bảo hành"})).json()["data"]
    assert "Dấu hiệu hư hại quan sát được" not in advice["message"]
    assert "cửa hậu" not in advice["message"]
    assert "Hướng dẫn sửa chữa" in advice["message"] and "Chưa có tài liệu" in advice["message"]
    assert advice["case_id"] == incident["case_id"]
    again = (await client.post("/api/v1/customer/chat", json={"session_id": "exterior-choice",
        "message": "Xe đang gặp sự cố"})).json()["data"]
    assert again["case_id"] == incident["case_id"]
    assert customer_db.query(Case).count() == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("severity,expected", [("severe", "CRITICAL"), ("moderate", "HIGH")])
async def test_new_exterior_incident_resets_safety_and_upgrades_priority(client, customer_db, severity, expected):
    case = Case(id="CASE-exterior-existing", user_id="regression-customer", session_id="new-photo",
                priority="LOW", status="Staff Reviewing", intent="Service/Incident",
                safety_status="customer_reported_safe", incident_version=2)
    att = Attachment(id="new-exterior-photo", storage_key="unused", mime_type="image/png",
                     detected_signals={"owner_user_id": "regression-customer", "evidence_type": "VEHICLE_MODEL",
                         "exterior_observation": {"severity": severity, "damages": [{"part": "nóc xe",
                             "location": "phía trên", "description": "biến dạng", "confidence": .98}]}})
    customer_db.add_all([case, att])
    customer_db.commit()
    await client.post("/api/v1/customer/chat", json={"session_id": "new-photo", "message": "Tôi gửi ảnh xe",
        "attachment_ids": [att.id]})
    customer_db.refresh(case)
    assert case.safety_status == "customer_reported_safe"
    data = (await client.post("/api/v1/customer/chat", json={"session_id": "new-photo",
        "message": "Xe đang gặp sự cố"})).json()["data"]
    assert data["priority"] == expected
    assert data["safety_status"] == "unconfirmed"
    assert data["incident_version"] == 3
    brief = customer_db.query(CaseBrief).filter_by(case_id=data["case_id"]).one()
    brief.is_edited_by_staff = True
    brief.captured_fields = {"staff_note": "Checked"}
    customer_db.commit()
    again = (await client.post("/api/v1/customer/chat", json={"session_id": "new-photo",
        "message": "Xe đang gặp sự cố"})).json()["data"]
    assert again["incident_version"] == 3


@pytest.mark.asyncio
async def test_warranty_query_keeps_customer_question_and_pin_topic_does_not_reuse_damage(monkeypatch):
    import src.services.exterior_conversation as conversation
    assert not conversation.exterior_question("Chính sách bảo hành pin VF 8 thế nào?")
    captured = []
    async def rag(state):
        captured.append(state["latest_user_message"])
        return {"response": "Không có dữ liệu đủ.", "rag_citations": []}
    monkeypatch.setattr(conversation, "rag_node", rag)
    await conversation.warranty_answer("VF 8", "query", "Hư hại kính trong ảnh có được bảo hành không?")
    assert "Hư hại kính" in captured[0]


@pytest.mark.asyncio
async def test_missing_warranty_source_does_not_claim_staff_handoff(monkeypatch):
    import src.services.exterior_conversation as conversation
    async def unavailable(state):
        return {"response": "Tôi sẽ chuyển chuyên viên kiểm tra.", "is_no_source": True, "rag_citations": []}
    monkeypatch.setattr(conversation, "rag_node", unavailable)
    reply, citations = await conversation.warranty_answer("VF 3", "query", "Tư vấn sửa chữa và bảo hành")
    assert "chuyển chuyên viên" not in reply
    assert not citations
