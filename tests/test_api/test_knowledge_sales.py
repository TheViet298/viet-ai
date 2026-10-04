import pytest

pytest_plugins = ["tests.test_api.test_customer_chat_regressions"]


@pytest.mark.asyncio
async def test_multi_topic_sales_answers_every_part_without_fixed_vf8_filter(client, customer_db, monkeypatch):
    from src.agents.nodes import rag_node as node
    calls = []
    async def missing(query, vehicle_model=None):
        calls.append((query, vehicle_model))
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}
    monkeypatch.setattr(node, "vinfast_manual_search", missing)
    data = (await client.post("/api/v1/customer/chat", json={
        "session_id": "multi-topic-sales", "message": "Tôi muốn tư vấn thông tin các dòng xe điện VinFast từ VF 3 đến VF 9, giá lăn bánh và đăng ký lái thử cho xe VF8.",
        "client_context": {"vehicle_model": "VF8"},
    })).json()["data"]
    assert "Thông tin dòng xe" in data["message"]
    assert "Giá lăn bánh" in data["message"]
    assert "Lái thử" in data["message"]
    assert len(calls) == 3
    assert calls[0][1] is None
    assert calls[2][1] == "VF8"
    assert "B1" not in data["message"]
    assert not data["citations"]
    assert data["case_id"] is None


@pytest.mark.asyncio
async def test_explicit_model_overrides_selector_for_knowledge(client, customer_db, monkeypatch):
    import src.api.customer as api
    async def answer(text, **kwargs):
        assert kwargs["client_context"]["vehicle_model"] == "VF5"
        return {"reply": "Chưa đủ nguồn cho câu hỏi này.", "citations": []}
    monkeypatch.setattr(api, "process_chat_message", answer)
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "explicit-vf5", "message": "Thông số dung lượng pin VF5 bao nhiêu?",
        "client_context": {"vehicle_model": "VF8"},
    })
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("question,subject", [("Biểu tượng con rùa vàng là gì thì", "giới hạn công suất"),
                                           ("TPMS là gì trên xe?", "áp suất lốp")])
async def test_common_car_knowledge_answers_in_real_graph_without_official_source(client, customer_db, question, subject):
    data = (await client.post("/api/v1/customer/chat", json={
        "session_id": "common-car-knowledge", "message": question,
        "client_context": {"vehicle_model": "VF8"},
    })).json()["data"]
    assert subject in data["message"].casefold()
    assert "kiến thức chung" in data["message"].casefold()
    assert data["response_type"] == "FAQ_ANSWER"
    assert data["case_id"] is None
    assert not data["citations"]
    assert not data["show_emergency_banner"]


@pytest.mark.asyncio
async def test_concept_followup_preserves_subject_then_new_incident_is_not_a_definition(client, customer_db):
    for question, subjects in [("SOH là gì?", ["sức khỏe"]),
                               ("Nó khác SOC thế nào?", ["sức khỏe", "mức pin"]),
                               ("Phân biệt ABS và ESC", ["bó cứng", "cân bằng"]),
                               ("ADAS?", ["hỗ trợ người lái"])]:
        data = (await client.post("/api/v1/customer/chat", json={
            "session_id": "concept-followup", "message": question,
            "client_context": {"vehicle_model": "VF8"},
        })).json()["data"]
        for subject in subjects:
            assert subject in data["message"].casefold()
        assert data["case_id"] is None
    data = (await client.post("/api/v1/customer/chat", json={
        "session_id": "concept-followup", "message": "Xe tôi bị mất phanh",
        "client_context": {"vehicle_model": "VF8"},
    })).json()["data"]
    assert data["priority"] == "CRITICAL"
    assert data["show_emergency_banner"]

