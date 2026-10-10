import pytest

from src.agents.nodes.triage_node import classify_request_kind, triage_node
from src.models.db_models import Case
from src.services.vehicle_context import resolve_vehicle_context

pytest_plugins = ["tests.test_api.test_customer_chat_regressions"]


@pytest.mark.parametrize("text", ["so sánh xe vf8 và vf6", "VF8 và VF6 khác nhau thế nào?", "so sanh VF8 va VF6"])
def test_comparison_does_not_fill_incident_vehicle(text):
    previous = resolve_vehicle_context("Xe tôi đang hiện rùa vàng")
    context = resolve_vehicle_context(text, previous)
    assert classify_request_kind(text) == "faq"
    assert not context["is_incident"]
    assert context["models"] == ["VF8", "VF6"]
    assert "rùa" not in context["resolved_query"]


@pytest.mark.asyncio
async def test_comparison_requires_grounded_retrieval():
    result = await triage_node({"latest_user_message": "so sánh xe vf8 và vf6"})
    assert result["is_rag_query"]
    assert not result["is_general_query"]


@pytest.mark.asyncio
@pytest.mark.parametrize("after_incident", [False, True])
async def test_comparison_uses_faq_without_location_or_case(client, customer_db, monkeypatch, after_incident):
    import src.api.customer as api

    queries = []

    async def answer(text, **kwargs):
        queries.append((text, kwargs["client_context"]["vehicle_model"]))
        return {"reply": "Kết quả tra cứu so sánh VF8 và VF6", "citations": []}

    monkeypatch.setattr(api, "process_chat_message", answer)
    if after_incident:
        for text in ["lỗi rùa vàng là gì", "Xe tôi đang hiện biểu tượng này"]:
            response = await client.post("/api/v1/customer/chat", json={"session_id": "compare", "message": text})
            assert response.status_code == 200
    response = await client.post("/api/v1/customer/chat", json={"session_id": "compare", "message": "so sánh xe vf8 và vf6"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["response_type"] == "FAQ_ANSWER"
    assert not data["request_location"]
    assert data["message"] == "Kết quả tra cứu so sánh VF8 và VF6"
    assert queries[-1] == ("so sánh xe vf8 và vf6", None)
    assert customer_db.query(Case).filter_by(session_id="compare").count() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("report", ["Xe tôi đang hiện biểu tượng này", "Xe tôi đang bị sự cố này"])
async def test_turtle_report_moves_from_definition_to_incident(client, customer_db, monkeypatch, report):
    import src.api.customer as api

    async def answer(*args, **kwargs):
        return {"reply": "Giải thích rùa vàng", "citations": []}

    monkeypatch.setattr(api, "process_chat_message", answer)
    await client.post("/api/v1/customer/chat", json={"session_id": "turtle-report", "message": "lỗi rùa vàng là gì"})
    response = await client.post("/api/v1/customer/chat", json={"session_id": "turtle-report", "message": report})
    data = response.json()["data"]
    assert data["response_type"] == "CLARIFICATION"
    assert "rùa vàng" in data["message"].lower()
    assert "chế độ bảo vệ" not in data["message"]
    assert "an toàn" in data["message"]
    assert "dòng xe" in data["message"]
    assert "CC01" not in data["message"]
