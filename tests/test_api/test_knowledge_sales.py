import pytest

pytest_plugins = ["tests.test_api.test_customer_chat_regressions"]


@pytest.mark.asyncio
async def test_color_question_after_quote_uses_knowledge_in_same_session(client, customer_db, monkeypatch):
    import src.api.customer as api
    from src.agents.nodes import rag_node as node

    async def missing(*args, **kwargs):
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}

    queries = []

    async def answer(text, **kwargs):
        queries.append(text)
        assert 'lăn bánh' not in text
        return {"reply": "Thông tin màu sắc VF8 Plus từ nguồn sản phẩm.", "citations": []}

    monkeypatch.setattr(node, 'vinfast_manual_search', missing)
    monkeypatch.setattr(api, 'process_chat_message', answer)
    first = await client.post('/api/v1/customer/chat', json={
        'session_id': 'quote-then-colors', 'message': 'Dự toán lăn bánh VinFast VF 8 Plus',
    })
    assert first.status_code == 200
    second = await client.post('/api/v1/customer/chat', json={
        'session_id': 'quote-then-colors', 'message': 'vf8 plus có những màu gì',
    })
    assert second.status_code == 200
    assert len(queries) == 1
    assert 'Thông tin màu sắc' in second.json()['data']['message']
    assert 'chi-phi-lan-banh' not in second.json()['data']['message']
    assert not second.json()['data']['vehicle_cards']


@pytest.mark.asyncio
async def test_unsupported_color_answer_is_not_reported_as_generation_failure(client, customer_db, monkeypatch):
    import src.api.customer as api

    async def unsupported(text, **kwargs):
        return {
            'reply': 'Hiện chưa có tài liệu chính thức đã xác thực đủ để trả lời yêu cầu này.',
            'citations': [], 'is_no_source': True,
            'retrieval_diagnostics': {'stage': 'generation', 'category': 'unsupported_answer'},
        }

    monkeypatch.setattr(api, 'process_chat_message', unsupported)
    response = await client.post('/api/v1/customer/chat', json={
        'session_id': 'unsupported-colors', 'message': 'vf8 plus có những màu gì',
    })
    assert response.status_code == 200
    reply = response.json()['data']['message']
    assert 'chưa có tài liệu' in reply
    assert 'chưa hoàn tất' not in reply


@pytest.mark.asyncio
@pytest.mark.parametrize("followup", [
    "Sao không có giá chính xác?",
    "Sao không có giá lăn bánh?",
    "Tại sao không báo giá cụ thể?",
    "Vì sao chưa đưa ra giá chính xác?",
])
async def test_price_followup_explains_uncertainty_in_same_session(client, customer_db, monkeypatch, followup):
    from src.agents.nodes import rag_node as node

    calls = []

    async def missing(query, vehicle_model=None):
        calls.append(query)
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}

    monkeypatch.setattr(node, "vinfast_manual_search", missing)
    first = await client.post("/api/v1/customer/chat", json={
        "session_id": "vf8-price-followup", "message": "Giá lăn bánh của xe VF8 là bao nhiêu?",
    })
    assert first.status_code == 200
    second = await client.post("/api/v1/customer/chat", json={
        "session_id": "vf8-price-followup", "message": followup,
    })
    assert second.status_code == 200
    data = second.json()["data"]
    reply = data["message"]
    assert reply != first.json()["data"]["message"]
    assert "VF8" in reply
    for reason in ("phiên bản", "mua pin", "thuê pin", "nếu còn áp dụng", "đăng ký", "showroom", "thời điểm mua"):
        assert reason in reply
    assert 'chưa có nguồn giá bán công bố đã xác minh' in reply
    assert 'chi-phi-lan-banh' in reply
    assert len(calls) == 2
    assert data["response_type"] == "FAQ_ANSWER"
    assert data["case_id"] is None
    assert not data["citations"]
    assert not data["show_emergency_banner"]


@pytest.mark.asyncio
@pytest.mark.parametrize("question", ["Tại sao VF8 không giảm giá?", "Tại sao VF8 không có giá ưu đãi?"])
async def test_discount_question_still_retrieves_sales_evidence(client, customer_db, monkeypatch, question):
    from src.agents.nodes import rag_node as node

    calls = []

    async def missing(query, vehicle_model=None):
        calls.append(query)
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}

    monkeypatch.setattr(node, "vinfast_manual_search", missing)
    response = await client.post("/api/v1/customer/chat", json={
        "session_id": "vf8-discount", "message": question,
    })
    assert response.status_code == 200
    assert len(calls) == 1
    assert "chưa đủ thông tin" not in response.json()["data"]["message"]


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

