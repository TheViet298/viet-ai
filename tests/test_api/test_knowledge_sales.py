import pytest

pytest_plugins = ["tests.test_api.test_customer_chat_regressions"]


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


@pytest.mark.asyncio
async def test_general_lineup_inquiry_does_not_narrow_to_profile_model(client, customer_db, monkeypatch):
    """Khi hỏi tổng quan các dòng xe, không bị thu hẹp về model xe trong hồ sơ (VF3)."""
    from src.agents.nodes import rag_node as node
    async def missing(query, vehicle_model=None):
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}
    monkeypatch.setattr(node, "vinfast_manual_search", missing)

    res = await client.post("/api/v1/customer/chat", json={
        "session_id": "lineup-inquiry-test",
        "message": "Tôi muốn tư vấn các dòng xe điện VinFast, giá lăn bánh và đăng ký lái thử",
        "client_context": {"vehicle_model": "VF3"},
    })
    assert res.status_code == 200
    data = res.json()["data"]
    msg = data["message"]
    # Phải có bảng tổng quan dải sản phẩm, không chỉ riêng thẻ VF 3
    assert "Dải sản phẩm ô tô điện thông minh VinFast" in msg or ("VF 3" in msg and "VF 9" in msg)
    assert "Thông tin dòng xe" in msg
    assert "Giá lăn bánh" in msg
    assert "Lái thử" in msg


@pytest.mark.asyncio
async def test_specific_model_inquiry_offers_comparison_with_profile_vehicle(client, customer_db, monkeypatch):
    """Khi hỏi dòng xe cụ thể (VF8), trả về thẻ VF8 và có câu gợi ý so sánh với xe đang sở hữu (VF3)."""
    from src.agents.nodes import rag_node as node
    async def missing(query, vehicle_model=None):
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}
    monkeypatch.setattr(node, "vinfast_manual_search", missing)

    res = await client.post("/api/v1/customer/chat", json={
        "session_id": "specific-model-test",
        "message": "Tư vấn xe VF8",
        "client_context": {"vehicle_model": "VF3"},
    })
    assert res.status_code == 200
    data = res.json()["data"]
    msg = data["message"]
    assert "VF 8" in msg
    assert "Công suất tối đa" in msg
    # Thẻ VF8 có câu gợi ý so sánh với VF3
    assert "VF 3" in msg


@pytest.mark.asyncio
async def test_empty_session_without_messages_excluded_from_sidebar(client, customer_db):
    """Session rỗng không có tin nhắn nào không được xuất hiện ở danh sách sidebar."""
    from src.models.db_models import ChatSession
    empty_sess = ChatSession(id="sess_vf_empty_test", owner="guest:test-empty-guest", memory_states={})
    customer_db.add(empty_sess)
    customer_db.commit()

    res = await client.get("/api/v1/customer/sessions?guest_session_id=test-empty-guest")
    assert res.status_code == 200
    sessions = res.json()["data"]["sessions"]
    session_ids = [s["session_id"] for s in sessions]
    assert "sess_vf_empty_test" not in session_ids


# =============================================================================
# 9 BÀI TEST CHÍNH THỨC THEO YÊU CẦU KIỂM THỬ (TÀI KHOẢN VF3)
# =============================================================================

@pytest.mark.asyncio
async def test_case_1_compare_two_models_only_contains_those_two(client, customer_db, monkeypatch):
    """1. 'so sánh VF3 và VF5' -> chỉ 2 xe, KHÔNG có VF6/VF7/VF8/VF9."""
    from src.agents.nodes import rag_node as node
    async def missing(query, vehicle_model=None):
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}
    monkeypatch.setattr(node, "vinfast_manual_search", missing)

    res = await client.post("/api/v1/customer/chat", json={
        "session_id": "test-comp-vf3-vf5",
        "message": "so sánh VF3 và VF5",
        "client_context": {"vehicle_model": "VF3"},
    })
    assert res.status_code == 200
    msg = res.json()["data"]["message"]
    assert "VF 3" in msg or "VF3" in msg
    assert "VF 5" in msg or "VF5" in msg
    # Đảm bảo KHÔNG có các dòng xe khác trong bảng so sánh
    for other in ("VF 6", "VF6", "VF 7", "VF7", "VF 8", "VF8", "VF 9", "VF9"):
        assert other not in msg
    # Bảng phải có các tiêu chí chuẩn
    for header in ("Công suất", "Quãng đường", "Sạc nhanh", "Số chỗ"):
        assert header in msg


@pytest.mark.asyncio
async def test_case_2_compare_three_models_contains_exactly_three(client, customer_db, monkeypatch):
    """2. 'so sánh VF3, VF5 và VF8' -> đúng 3 xe."""
    from src.agents.nodes import rag_node as node
    async def missing(query, vehicle_model=None):
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}
    monkeypatch.setattr(node, "vinfast_manual_search", missing)

    res = await client.post("/api/v1/customer/chat", json={
        "session_id": "test-comp-3-models",
        "message": "so sánh VF3, VF5 và VF8",
        "client_context": {"vehicle_model": "VF3"},
    })
    assert res.status_code == 200
    msg = res.json()["data"]["message"]
    assert "VF 3" in msg or "VF3" in msg
    assert "VF 5" in msg or "VF5" in msg
    assert "VF 8" in msg or "VF8" in msg
    # Không có VF6, VF7, VF9
    for other in ("VF 6", "VF6", "VF 7", "VF7", "VF 9", "VF9"):
        assert other not in msg


@pytest.mark.asyncio
async def test_case_3_compare_family_choice_contains_two_relevant_models(client, customer_db, monkeypatch):
    """3. 'VF8 hay VF9 hợp gia đình' -> 2 xe liên quan."""
    from src.agents.nodes import rag_node as node
    async def missing(query, vehicle_model=None):
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}
    monkeypatch.setattr(node, "vinfast_manual_search", missing)

    res = await client.post("/api/v1/customer/chat", json={
        "session_id": "test-vf8-vf9-family",
        "message": "VF8 hay VF9 hợp gia đình",
        "client_context": {"vehicle_model": "VF3"},
    })
    assert res.status_code == 200
    msg = res.json()["data"]["message"]
    assert "VF 8" in msg or "VF8" in msg
    assert "VF 9" in msg or "VF9" in msg
    # Không lẫn VF3, VF5, VF6, VF7
    for other in ("VF 5", "VF5", "VF 6", "VF6", "VF 7", "VF7"):
        assert other not in msg


@pytest.mark.asyncio
async def test_case_4_general_lineup_consultation_returns_full_lineup(client, customer_db, monkeypatch):
    """4. 'tư vấn các dòng xe điện VinFast' -> bảng cả dải."""
    from src.agents.nodes import rag_node as node
    async def missing(query, vehicle_model=None):
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}
    monkeypatch.setattr(node, "vinfast_manual_search", missing)

    res = await client.post("/api/v1/customer/chat", json={
        "session_id": "test-general-lineup",
        "message": "tư vấn các dòng xe điện VinFast",
        "client_context": {"vehicle_model": "VF3"},
    })
    assert res.status_code == 200
    msg = res.json()["data"]["message"]
    # Phải có đầy đủ từ VF3 tới VF9
    assert "VF 3" in msg
    assert "VF 5" in msg
    assert "VF 6" in msg
    assert "VF 7" in msg
    assert "VF 8" in msg
    assert "VF 9" in msg


@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_keyword", [
    ("xe nào sạc nhanh nhất", "sạc nhanh"),
    ("xe nào đi xa nhất", "quãng đường"),
])
async def test_case_5_ranking_queries_answer_without_specialist_redirect_or_forcing_vf3(client, customer_db, monkeypatch, query, expected_keyword):
    """5. 'xe nào sạc nhanh nhất' / 'xe nào đi xa nhất' -> không ép VF3, không câu 'chuyển chuyên viên'."""
    from src.agents.nodes import rag_node as node
    async def missing(query, vehicle_model=None):
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}
    monkeypatch.setattr(node, "vinfast_manual_search", missing)

    res = await client.post("/api/v1/customer/chat", json={
        "session_id": "test-ranking-query",
        "message": query,
        "client_context": {"vehicle_model": "VF3"},
    })
    assert res.status_code == 200
    msg = res.json()["data"]["message"]
    # Không được có câu chuyển chuyên viên kiểm tra
    assert "chuyên viên kiểm tra" not in msg
    assert "ghi nhận để chuyên viên" not in msg
    # Phải có thông tin xếp hạng và so sánh
    assert expected_keyword in msg.lower()
    # Có dẫn nguồn cẩm nang
    citations = res.json()["data"]["citations"]
    assert len(citations) > 0


@pytest.mark.asyncio
async def test_case_6_turtle_warning_uses_profile_model_without_asking(client, customer_db):
    """6. 'xe tôi bị rùa vàng' -> không hỏi lại dòng xe khi hồ sơ đã có VF3."""
    res = await client.post("/api/v1/customer/chat", json={
        "session_id": "test-turtle-profile",
        "message": "xe tôi bị rùa vàng",
        "client_context": {"vehicle_model": "VF3"},
    })
    assert res.status_code == 200
    msg = res.json()["data"]["message"]
    # Dùng luôn dòng xe VF3 từ hồ sơ
    assert "Xe VF3 của anh/chị" in msg or "xe VF3 của anh/chị" in msg
    # Không hỏi lại dòng xe
    assert "cho em biết dòng xe" not in msg
    # Ưu tiên hỏi an toàn
    assert "an toàn chưa" in msg


@pytest.mark.asyncio
async def test_case_7_greeting_does_not_contain_car_cards(client, customer_db):
    """7. 'xin chào' -> không có thẻ xe."""
    res = await client.post("/api/v1/customer/chat", json={
        "session_id": "test-greeting",
        "message": "xin chào",
        "client_context": {"vehicle_model": "VF3"},
    })
    assert res.status_code == 200
    msg = res.json()["data"]["message"]
    # Là câu chào chuẩn, không có thẻ xe chi tiết
    assert "Trợ lý CSKH VinFast" in msg
    assert "Thông số kỹ thuật" not in msg
    assert "Công suất tối đa" not in msg


@pytest.mark.asyncio
async def test_case_8_rolling_price_question_states_no_exact_data_without_fake_numbers(client, customer_db, monkeypatch):
    """8. Câu hỏi giá lăn bánh -> nói rõ chưa có dữ liệu, không có con số."""
    from src.agents.nodes import rag_node as node
    async def missing(query, vehicle_model=None):
        return {"status": "NO_SOURCE", "citations": [], "diagnostics": {"category": "no_eligible_evidence"}}
    monkeypatch.setattr(node, "vinfast_manual_search", missing)

    res = await client.post("/api/v1/customer/chat", json={
        "session_id": "test-rolling-price",
        "message": "Giá lăn bánh xe VF5 tại Hà Nội là bao nhiêu?",
        "client_context": {"vehicle_model": "VF3"},
    })
    assert res.status_code == 200
    msg = res.json()["data"]["message"]
    # Nói rõ chưa có nguồn giá xác minh
    assert "chưa có nguồn giá bán công bố đã xác minh" in msg or "chưa thể đưa con số" in msg
    assert "chi-phi-lan-banh" in msg


@pytest.mark.asyncio
async def test_case_9_empty_chat_does_not_create_empty_sidebar_item(client, customer_db):
    """9. Mở chat trống / bấm 'Cuộc trò chuyện mới' không gõ gì -> không tạo mục rỗng ở sidebar."""
    from src.models.db_models import ChatSession
    # Tạo 1 session chỉ có tin nhắn của bot (lời chào) nhưng không có tin nhắn của khách
    bot_sess = ChatSession(id="sess_vf_bot_only", owner="guest:guest-empty-check", memory_states={})
    customer_db.add(bot_sess)
    customer_db.commit()

    res = await client.get("/api/v1/customer/sessions?guest_session_id=guest-empty-check")
    assert res.status_code == 200
    sessions = res.json()["data"]["sessions"]
    session_ids = [s["session_id"] for s in sessions]
    assert "sess_vf_bot_only" not in session_ids


