import pytest

from src.agents.chatbot_agent import process_chat_message
from src.services.rag_service import source_registry
from src.services.session_store import decode_state, get_store


@pytest.mark.asyncio
async def test_application_no_source_memory_matches_reply_without_phantom_case(monkeypatch):
    import src.agents.nodes.rag_node as node
    async def search(query, **kwargs):
        return {'status': 'NO_SOURCE', 'citations': []}
    monkeypatch.setattr(node, 'vinfast_manual_search', search)
    reply = await process_chat_message('VF8 được bảo hành bao lâu?', session_id='application-memory',
        user_role='customer', owner='owner', persist_business_case=False)
    with get_store().connect() as db:
        state = decode_state(db.execute("SELECT state FROM agent_sessions WHERE id='application-memory'").fetchone()[0])
        assert db.execute('SELECT count(*) FROM cases').fetchone()[0] == 0
    assert state['messages'][-1].content == reply['response']


@pytest.mark.asyncio
async def test_warranty_followup_uses_context_but_preserves_original_message(monkeypatch):
    import src.agents.nodes.rag_node as node
    queries = []
    async def search(query, **kwargs):
        queries.append(query)
        snippet = "VF8: 10 năm hoặc 200.000 km tùy điều kiện nào đến trước." if len(queries) == 1 else "Điều kiện bảo hành VF8: sử dụng đúng hướng dẫn và bảo dưỡng định kỳ."
        citation = {**source_registry()["SRC-002"], "source_id": "SRC-002", "applicable_models": ["VF8"], "distance": .2, "relevant_snippet": snippet}
        return {"status": "SUCCESS", "citations": [citation]}
    monkeypatch.setattr(node, "vinfast_manual_search", search)
    args = {"session_id": "followup", "user_role": "customer", "owner": "owner", "client_context": {"vehicle_model": "VF8"}}
    first = await process_chat_message("VF8 được bảo hành bao lâu?", **args)
    assert first["response_type"] == "FAQ_ANSWER"
    second = await process_chat_message("điều kiện là gì", **args)
    assert second["response_type"] == "FAQ_ANSWER"
    assert "bảo hành" in queries[-1].casefold()
    assert "điều kiện" in queries[-1].casefold()
    assert "bảo dưỡng định kỳ" in second["reply"]
    with get_store().connect() as db:
        row = db.execute("SELECT state FROM agent_sessions WHERE id='followup'").fetchone()
    state = decode_state(row["state"])
    assert state["latest_user_message"] == "điều kiện là gì"
    assert state["messages"][-2].content == "điều kiện là gì"
    fresh = await process_chat_message("điều kiện là gì", **{**args, "session_id": "fresh"})
    assert fresh["response_type"] != "FAQ_ANSWER"
    changed = await process_chat_message("Giá vé máy bay bao nhiêu?", **args)
    assert changed["response_type"] == "OUT_OF_SCOPE"


@pytest.mark.parametrize("text,expected", [
    ("làm ở đâu?", "Đặt lịch bảo dưỡng"),
    ("Xe không sạc được", "Xe không sạc được"),
    ("VF5 bảo hành bao lâu?", "VF5 bảo hành bao lâu?"),
])
def test_appointment_followups_and_explicit_topic_changes(text, expected):
    from src.services.followup_context import resolve_faq_followup
    state = {"resolved_query": "Hướng dẫn đặt lịch bảo dưỡng VF8", "is_rag_query": True, "response_type": "FAQ_ANSWER"}
    assert resolve_faq_followup(text, state).startswith(expected)
