import pytest


@pytest.mark.asyncio
async def test_get_ticket_queue(client):
    """Kiểm tra GET /api/v1/staff/tickets theo api-contract.md Mục 3.1."""
    res = await client.get("/api/v1/staff/tickets")
    assert res.status_code == 200
    body = res.json()

    # Bắt buộc chuẩn response envelope
    assert body["success"] is True
    assert "data" in body
    assert "meta" in body
    assert "timestamp" in body["meta"]

    data = body["data"]
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 4

    item = data["items"][0]
    assert "id" in item
    assert item["id"].startswith("CASE-")
    assert "mock_customer_id" in item
    assert "vehicle_model" in item
    assert "priority" in item
    assert "status" in item
    assert "confidence_score" in item


@pytest.mark.asyncio
async def test_get_ticket_detail(client):
    """Kiểm tra GET /api/v1/staff/tickets/{case_id} theo api-contract.md Mục 3.2."""
    res = await client.get("/api/v1/staff/tickets/CASE-20260924-001")
    assert res.status_code == 200
    body = res.json()

    assert body["success"] is True
    data = body["data"]
    assert "case" in data
    assert "case_brief" in data
    assert "conversation_history" in data

    assert data["case"]["id"] == "CASE-20260924-001"
    assert data["case"]["mock_customer_id"] == "CUST_MOCK_01"
    assert data["case"]["vehicle_code_mock"] == "VF-SF-00231"
    assert "summary" in data["case_brief"]
    assert "captured_fields" in data["case_brief"]
    assert len(data["conversation_history"]) >= 3


@pytest.mark.asyncio
async def test_staff_action_approve(client):
    """Kiểm tra POST /api/v1/staff/tickets/{case_id}/actions hành động APPROVE theo api-contract.md Mục 3.3."""
    payload = {
        "action": "APPROVE",
        "staff_id": "STAFF_TEST_01",
        "notes": "Đã duyệt và chuyển kỹ thuật viên xử lý.",
    }
    res = await client.post("/api/v1/staff/tickets/CASE-20260924-001/actions", json=payload)
    assert res.status_code == 200
    body = res.json()

    assert body["success"] is True
    assert body["data"]["case_id"] == "CASE-20260924-001"

    # Kiểm tra trạng thái đã chuyển sang In Progress
    detail_res = await client.get("/api/v1/staff/tickets/CASE-20260924-001")
    detail = detail_res.json()["data"]
    assert detail["case"]["status"] == "In Progress"


@pytest.mark.asyncio
async def test_staff_action_edit_brief(client):
    """Kiểm tra POST /api/v1/staff/tickets/{case_id}/actions hành động EDIT_BRIEF."""
    payload = {
        "action": "EDIT_BRIEF",
        "staff_id": "STAFF_TEST_01",
        "edited_brief": {
            "summary": "Tóm tắt sự cố đã được nhân viên hiệu chỉnh",
            "error_code": "CC01-MODIFIED",
        },
        "notes": "Chỉnh sửa tóm tắt theo xác minh hotline",
    }
    res = await client.post("/api/v1/staff/tickets/CASE-20260924-001/actions", json=payload)
    assert res.status_code == 200

    detail_res = await client.get("/api/v1/staff/tickets/CASE-20260924-001")
    brief = detail_res.json()["data"]["case_brief"]
    assert brief["summary"] == "Tóm tắt sự cố đã được nhân viên hiệu chỉnh"
    assert brief["is_edited_by_staff"] is True


@pytest.mark.asyncio
async def test_customer_chat_critical_safety(client):
    """Kiểm tra Hard Safety Rules: phát hiện từ khóa nguy hiểm -> CRITICAL, bỏ qua làm rõ."""
    payload = {
        "session_id": "sess_safety_test_01",
        "message": "Xe đang chạy trên cao tốc thì báo rùa vàng và mất công suất dừng giữa đường!",
        "client_context": {
            "mock_customer_id": "CUST_TEST_99",
            "vehicle_model": "VF9",
            "vehicle_code_mock": "VF-SF-99999",
        },
    }
    res = await client.post("/api/v1/customer/chat", json=payload)
    assert res.status_code == 200
    body = res.json()

    assert body["success"] is True
    data = body["data"]
    assert data["response_type"] == "CASE_CREATED"
    assert data["priority"] == "CRITICAL"
    assert data["case_id"] is not None
    assert data["case_id"].startswith("CASE-")
    assert data["safe_guidance"] is not None
    assert "dừng khẩn cấp" in data["safe_guidance"].lower()


@pytest.mark.asyncio
async def test_customer_chat_faq(client):
    """Kiểm tra khách hàng hỏi thông tin sạc (FAQ answer kèm citation và service handoff)."""
    payload = {
        "session_id": "sess_faq_test_01",
        "message": "Tôi muốn biết chi phí sạc pin tại trụ sạc công cộng của VinFast là bao nhiêu?",
        "client_context": {
            "mock_customer_id": "CUST_TEST_01",
            "vehicle_model": "VF8",
            "vehicle_code_mock": "VF-SF-00231",
        },
    }
    res = await client.post("/api/v1/customer/chat", json=payload)
    assert res.status_code == 200
    body = res.json()

    assert body["success"] is True
    data = body["data"]
    assert data["response_type"] == "FAQ_ANSWER"
    assert data["citations"] is not None
    assert len(data["citations"]) > 0
    assert data["service_handoff"] is not None


@pytest.mark.asyncio
async def test_customer_case_status(client):
    """Kiểm tra GET /api/v1/customer/cases/{case_id}/status theo api-contract.md Mục 2.2."""
    res = await client.get("/api/v1/customer/cases/CASE-20260924-001/status")
    assert res.status_code == 200
    body = res.json()

    assert body["success"] is True
    assert body["data"]["case_id"] == "CASE-20260924-001"
    assert "status" in body["data"]
    assert "status_description" in body["data"]
