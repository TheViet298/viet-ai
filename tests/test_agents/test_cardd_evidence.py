import copy
import json

import pytest

from src.agents.cardd_evidence import make_cardd_signal
from src.agents.graph import agent
from src.config import get_settings
from src.services.vision.contract import VisionEvidence, damage_result
from src.services.vision.damage_detector import BASELINE_SHA256


def payload(score=0.29):
    return VisionEvidence(
        image_id="image-001",
        damage=damage_result(
            [{"label": "dent", "confidence": score, "bbox_xyxy": [0.1, 0.2, 0.8, 0.6]}], BASELINE_SHA256
        ),
    ).model_dump(mode="json")


@pytest.fixture(autouse=True)
def isolated_agent(monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", False)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'app.db'}")


@pytest.mark.asyncio
async def test_low_score_image_requests_confirmation_without_promoting_facts():
    result = await agent.ainvoke(
        {
            "query": "Xem ảnh ngoại thất giúp tôi",
            "user_role": "customer",
            "vehicle_model": "VF8",
            "captured_fields": {"vehicle_model": "VF8"},
            "pending_cardd_signal": make_cardd_signal(payload(), 1),
        }
    )
    assert result["response_type"] == "CLARIFICATION"
    assert "móp" in result["response"] and "chắc chắn" in result["response"]
    assert "xác nhận" in result["response"].lower()
    assert result["captured_fields"] == {"vehicle_model": "VF8"}
    assert not result["is_critical"]
    assert result["pending_cardd_signal"] is None
    assert result["cardd_evidence"]["confirmation"] == "unconfirmed"


@pytest.mark.asyncio
async def test_emergency_reply_is_not_replaced_with_photo_question():
    result = await agent.ainvoke(
        {"query": "Xe VF8 bốc khói", "user_role": "customer", "pending_cardd_signal": make_cardd_signal(payload(), 1)}
    )
    assert result["response_type"] == "EMERGENCY_ALERT"
    assert "1900" in result["response"]
    assert result["case_brief"]["visual_evidence"]["confirmation"] == "unconfirmed"
    assert not result["case_brief"]["captured_fields"].get("damage")


@pytest.mark.asyncio
async def test_explicit_confirmation_records_general_damage_not_each_label():
    first = await agent.ainvoke(
        {
            "query": "Xem ảnh ngoại thất giúp tôi",
            "user_role": "customer",
            "pending_cardd_signal": make_cardd_signal(payload(), 1),
        }
    )
    second = await agent.ainvoke(
        {**first, "query": "Xác nhận hư hại trong ảnh", "latest_user_message": "Xác nhận hư hại trong ảnh"}
    )
    assert second["cardd_evidence"]["confirmation"] == "confirmed"
    assert "warning_symbol" not in second["missing_fields"]
    assert "vehicle_model" in second["missing_fields"]
    assert "không được không" not in second["response"]
    third = await agent.ainvoke(
        {**second, "query": "Xe VF8 vẫn chạy bình thường", "latest_user_message": "Xe VF8 vẫn chạy bình thường"}
    )
    assert third["case_brief"]["vehicle_model"] == "VF8"
    assert third["case_brief"]["visual_evidence"]["confirmation"] == "confirmed"
    assert "AI" in third["case_brief"]["summary"]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["not_detected", "unavailable"])
async def test_empty_or_failed_analysis_never_claims_intact_vehicle(status):
    doc = payload()
    doc["damage"].update(status=status, detections=[], reason="inference_failed" if status == "unavailable" else None)
    result = await agent.ainvoke(
        {
            "query": "Xem ảnh ngoại thất giúp tôi",
            "user_role": "customer",
            "pending_cardd_signal": make_cardd_signal(doc, 1),
        }
    )
    assert result["response_type"] == "CLARIFICATION"
    assert "nguyên vẹn" not in result["response"] or "không" in result["response"]
    assert "mô tả" in result["response"].lower()


@pytest.mark.asyncio
async def test_stale_and_duplicate_signals_do_not_repeat_photo_review():
    signal = make_cardd_signal(payload(), 1)
    first = await agent.ainvoke(
        {"query": "Xem ảnh ngoại thất giúp tôi", "user_role": "customer", "pending_cardd_signal": signal}
    )
    second = await agent.ainvoke(
        {**first, "query": "Xe VF8", "latest_user_message": "Xe VF8", "pending_cardd_signal": signal}
    )
    assert not second["cardd_new_input"]
    assert second["cardd_evidence"]["turn"] == 1
    expired = await agent.ainvoke({**first, "turn": 3, "query": "Xin chào", "latest_user_message": "Xin chào"})
    assert expired["cardd_evidence"] is None


def test_invalid_evidence_keeps_no_raw_image_or_vehicle_guess():
    bad = copy.deepcopy(payload())
    bad["image_bytes"] = "private-image-data"
    signal = make_cardd_signal(bad, 1)
    assert "private-image-data" not in json.dumps(signal)
    assert signal["evidence"]["reason"] == "invalid_evidence"


@pytest.mark.asyncio
async def test_python_chat_entrypoint_accepts_trusted_evidence(monkeypatch):
    from src.agents.chatbot_agent import process_chat_message
    from src.services.session_store import get_store

    result = await process_chat_message(
        "Xem ảnh ngoại thất giúp tôi",
        session_id="cardd-session",
        user_role="customer",
        owner="c1",
        damage_evidence=payload(),
    )
    assert result["visual_evidence"]["image_id"] == "image-001"
    state, _ = get_store().claim("cardd-session", "c1", "customer")
    assert state["pending_cardd_signal"] is None


@pytest.mark.asyncio
async def test_rejection_does_not_treat_predicted_damage_as_fact():
    first = await agent.ainvoke(
        {
            "query": "Xem ảnh ngoại thất giúp tôi",
            "user_role": "customer",
            "pending_cardd_signal": make_cardd_signal(payload(), 1),
        }
    )
    result = await agent.ainvoke(
        {**first, "query": "Không xác nhận kết quả ảnh", "latest_user_message": "Không xác nhận kết quả ảnh"}
    )
    assert result["cardd_evidence"]["confirmation"] == "rejected"
    assert result["case_brief"] is None


@pytest.mark.asyncio
async def test_current_turn_duplicate_does_not_reset_confirmation_or_age():
    first = await agent.ainvoke(
        {
            "query": "Xem ảnh ngoại thất giúp tôi",
            "user_role": "customer",
            "pending_cardd_signal": make_cardd_signal(payload(), 1),
        }
    )
    second = await agent.ainvoke(
        {
            **first,
            "query": "Xe VF8",
            "latest_user_message": "Xe VF8",
            "pending_cardd_signal": make_cardd_signal(payload(), 2),
        }
    )
    assert not second["cardd_new_input"]
    assert second["cardd_evidence"]["turn"] == 1


@pytest.mark.asyncio
async def test_faq_with_attachment_still_uses_grounded_text_flow(monkeypatch):
    from src.agents.nodes import rag_node as module

    async def no_source(*args, **kwargs):
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {}}

    monkeypatch.setattr(module, "vinfast_manual_search", no_source)
    result = await agent.ainvoke(
        {
            "query": "Bảo hành VF8 bao lâu?",
            "user_role": "customer",
            "pending_cardd_signal": make_cardd_signal(payload(), 1),
        }
    )
    assert result["is_rag_query"] and result["is_no_source"]
    assert "xác nhận ảnh" not in result["response"].lower()


def test_knowledge_context_excludes_unconfirmed_photo_labels():
    from src.agents.cardd_evidence import confirmed_cardd_context

    record = make_cardd_signal(payload(), 1)["evidence"]
    assert confirmed_cardd_context({"turn": 1, "cardd_evidence": record}) == ""
    record["confirmation"] = "confirmed"
    record["confirmation_turn"] = 2
    assert "giả thuyết AI" in confirmed_cardd_context({"turn": 2, "cardd_evidence": record})


@pytest.mark.asyncio
async def test_model_metadata_cannot_confirm_damage_for_user():
    signal = make_cardd_signal(payload(), 1)
    signal["evidence"].update(confirmation="confirmed", confirmation_turn=1)
    result = await agent.ainvoke(
        {"query": "Xem ảnh ngoại thất giúp tôi", "user_role": "customer", "pending_cardd_signal": signal}
    )
    assert result["cardd_evidence"]["confirmation"] == "unconfirmed"


@pytest.mark.asyncio
async def test_review_respects_existing_clarification_cap():
    result = await agent.ainvoke(
        {
            "query": "Xem ảnh ngoại thất giúp tôi",
            "user_role": "customer",
            "clarification_turn": 2,
            "pending_cardd_signal": make_cardd_signal(payload(), 1),
        }
    )
    assert result["case_brief"]["visual_evidence"]["confirmation"] == "unconfirmed"
    assert result["clarification_turn"] == 2
    assert result["ticket_status"] == "Needs Information"
    assert result["guardrails"]["clarification_limit_reached"]


@pytest.mark.asyncio
async def test_not_requested_does_not_create_pending_damage_confirmation():
    doc = VisionEvidence(image_id="image-unused").model_dump(mode="json")
    result = await agent.ainvoke(
        {"query": "Xin chào", "user_role": "customer", "pending_cardd_signal": make_cardd_signal(doc, 1)}
    )
    assert result["cardd_evidence"] is None
    assert not result["cardd_new_input"]
