import pytest

from src.agents.chatbot_agent import process_chat_message
from src.services.location_service import save_location, suggest_service_points
from src.services.session_store import decode_state, get_store


@pytest.mark.asyncio
async def test_location_consent_skip_and_manual_points():
    result = await process_chat_message("Xe VF8 mất phanh", session_id="location", user_role="customer", owner="c1")
    cid = result["case_id"]
    assert suggest_service_points(cid, "c1") == []
    data = {"case_id": cid, "status": "MANUAL", "location_label": "Hà Nội", "latitude": 21.0, "longitude": 105.8}
    saved = save_location(data, "c1")
    assert saved["latitude"] is None
    points = suggest_service_points(cid, "c1")
    assert points == []  # No verified workshop mapping in the supplied CSV snapshot.
    save_location({**data, "status": "NOT_SHARED"}, "c1")
    assert suggest_service_points(cid, "c1") == []
    with pytest.raises(PermissionError):
        save_location(data, "c2")


@pytest.mark.asyncio
async def test_buffer_summary_keeps_facts_after_six_turns():
    for text in ["Xe VF8 lỗi", "Xe vẫn chạy bình thường", "Không biết", "Không biết", "Không biết", "Không biết"]:
        await process_chat_message(text, session_id="memory", user_role="customer", owner="c1")
    with get_store().connect() as db:
        state = decode_state(db.execute("SELECT state FROM agent_sessions WHERE id='memory'").fetchone()["state"])
    assert state["captured_fields"]["vehicle_model"] == "VF8"
    assert state["memory_summary"]
    assert len(state["messages"]) <= 10
