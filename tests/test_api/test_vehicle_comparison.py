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

    async def answer(text, *args, **kwargs):
        v_model = kwargs.get("client_context", {}).get("vehicle_model") if "client_context" in kwargs else kwargs.get("user_vehicle")
        queries.append((text, v_model))
        return {"reply": "Kết quả tra cứu so sánh VF8 và VF6", "citations": []}

    monkeypatch.setattr(api, "process_chat_message", answer)
    monkeypatch.setattr(api, "answer_sales_question", answer)
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


@pytest.mark.asyncio
async def test_comparison_vf3_and_vf5_returns_only_requested_models(client, customer_db):
    """
    Kỳ vọng: Câu hỏi 'so sánh VF3 và VF5' chỉ trả về bảng so sánh 2 xe VF 3 và VF 5,
    tuyệt đối không trả về bảng cả dải xe (VF 8, VF 9 không được xuất hiện).
    """
    response = await client.post(
        "/api/v1/customer/chat",
        json={"session_id": "compare-vf3-vf5", "message": "so sánh VF3 và VF5"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["response_type"] == "FAQ_ANSWER"
    msg = data["message"]
    assert "VF 3" in msg and "VF 5" in msg
    assert "VF 8" not in msg and "VF 9" not in msg
    # Card comparison uses shared labeled rows; markdown heading is presentation.
    assert data['vehicle_comparison']
    assert {card['model'] for card in data['vehicle_cards']} == {'VF3', 'VF5'}
    for label in ('Số chỗ', 'Quãng đường', 'Công suất', 'sạc nhanh'):
        assert label.casefold() in msg.casefold()


@pytest.mark.asyncio
async def test_ranking_fastest_charging_returns_ranking_table(client, customer_db):
    """
    Kỳ vọng: Câu hỏi xếp hạng 'xe nào sạc nhanh nhất' trả về bảng xếp hạng thời gian sạc,
    có trích dẫn tài liệu chính thức từ Knowledge Base.
    """
    response = await client.post(
        "/api/v1/customer/chat",
        json={"session_id": "rank-charging", "message": "xe nào sạc nhanh nhất?"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["response_type"] == "FAQ_ANSWER"
    msg = data["message"]
    assert len(data.get("citations", [])) > 0


@pytest.mark.asyncio
async def test_comparison_vf3_with_vf5_returns_valid_table_and_two_citations(client, customer_db):
    """
    Kỳ vọng: Câu hỏi 'vf3 với vf5 khác nhau ở đâu' trả về bảng markdown hợp lệ
    (có dòng phân cách | :--- | :--- |) và đủ 2 citation cho cả 2 xe (VF 3 và VF 5 Plus).
    """
    response = await client.post(
        "/api/v1/customer/chat",
        json={"session_id": "compare-table-citations", "message": "vf3 với vf5 khác nhau ở đâu"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["response_type"] == "FAQ_ANSWER"

    msg = data["message"]
    assert 'VF 3 Eco' in msg and 'VF 5' in msg
    assert '215 km (NEDC)' in msg and '326 km (NEDC)' in msg
    assert '210 km' not in msg

    # 4. Kiểm tra đủ 2 nguồn citation cho cả 2 xe
    citations = data.get("citations", [])
    assert len(citations) == 2
    cit_models = [c.get("applicable_models", [None])[0] for c in citations]
    assert "VF3" in cit_models
    assert "VF5" in cit_models

    cit_urls = [c.get("url") for c in citations]
    assert any("dat-coc-xe-dien-vf3" in u for u in cit_urls)
    assert any("dat-coc-xe-dien-vf5" in u for u in cit_urls)

