import io

import pytest


# Helper hàm đăng nhập để lấy token xác thực trong test
async def get_auth_token(client, username: str = "customer@vinfast.vn", password: str = "customer123") -> str:
    res = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["data"]["token"]


@pytest.mark.asyncio
async def test_public_articles(client):
    """Guest chỉ xem Landing/FAQ/Policy từ nguồn đã kiểm chứng (api-contract.md 1.1)."""
    res = await client.get("/api/v1/public/articles")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "data" in body
    assert body["data"]["total"] >= 4
    article = body["data"]["articles"][0]
    assert "title" in article
    assert "source_url" in article
    assert "verified_at" in article


@pytest.mark.asyncio
async def test_auth_register_and_login(client):
    """Kiểm tra Đăng ký & Đăng nhập theo auth-and-rbac.md."""
    # 1. Đăng ký Customer mới
    import uuid

    unique_user = f"new_driver_{uuid.uuid4().hex[:6]}@vinfast.vn"
    reg_payload = {
        "username": unique_user,
        "password": "securepassword123",
        "mock_customer_id": "CUST_MOCK_NEW",
    }
    res_reg = await client.post("/api/v1/auth/register", json=reg_payload)
    assert res_reg.status_code == 200
    reg_body = res_reg.json()
    assert reg_body["data"]["user"]["role"] == "CUSTOMER"

    # 2. Đăng nhập
    login_payload = {
        "username": unique_user,
        "password": "securepassword123",
    }
    res_login = await client.post("/api/v1/auth/login", json=login_payload)
    assert res_login.status_code == 200
    login_body = res_login.json()
    token = login_body["data"]["token"]
    assert token is not None

    # 3. Lấy thông tin cá nhân /auth/me
    headers = {"Authorization": f"Bearer {token}"}
    res_me = await client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["data"]["username"] == unique_user


@pytest.mark.asyncio
async def test_rbac_restrictions(client):
    """Kiểm tra RBAC: 401 khi chưa đăng nhập và 403 khi sai role."""
    # 1. Chưa đăng nhập gọi Staff API -> 401
    res_unauth = await client.get("/api/v1/staff/tickets")
    assert res_unauth.status_code == 401

    # 2. Customer gọi Staff API -> 403
    cust_token = await get_auth_token(client, "customer@vinfast.vn", "customer123")
    res_forbidden = await client.get("/api/v1/staff/tickets", headers={"Authorization": f"Bearer {cust_token}"})
    assert res_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_customer_attachment_upload(client):
    """Kiểm tra Upload ảnh riêng tư và trích xuất OCR sơ bộ (api-contract.md 1.1 & ADR-004)."""
    token = await get_auth_token(client, "customer@vinfast.vn", "customer123")
    headers = {"Authorization": f"Bearer {token}"}

    file_content = b"fake-image-bytes-of-dashboard"
    files = {"file": ("screen_error_cc01.jpg", io.BytesIO(file_content), "image/jpeg")}

    res = await client.post("/api/v1/customer/attachments", files=files, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert data["attachment_id"].startswith("ATT-")
    assert data["analysis_status"] == "ANALYZED"
    assert "CC01" in data["ocr_text"]
    assert data["detected_signals"]["error_code_candidate"] == "CC01"
    assert data["vision_confidence"] is not None


@pytest.mark.asyncio
async def test_customer_chat_critical_safety(client):
    """Kiểm tra Hard Safety Rules: phát hiện từ khóa nguy hiểm -> CRITICAL, bỏ qua làm rõ."""
    token = await get_auth_token(client, "customer@vinfast.vn", "customer123")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "session_id": "sess_safety_test_01",
        "message": "Xe đang chạy trên cao tốc thì báo rùa vàng và mất công suất dừng giữa đường!",
        "client_context": {
            "mock_customer_id": "CUST_MOCK_01",
            "vehicle_model": "VF9",
            "vehicle_code_mock": "VF-SF-99999",
        },
    }
    res = await client.post("/api/v1/customer/chat", json=payload, headers=headers)
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
async def test_customer_chat_faq(client, monkeypatch):
    """Kiểm tra khách hàng hỏi thông tin sạc (FAQ answer kèm citation và service handoff)."""
    # API mapping is verified against grounded evidence, independent of a local KB.
    from src.services.rag_service import source_registry
    import src.api.customer as api
    async def grounded_faq(*args, **kwargs):
        source = source_registry()["SRC-003"]
        return {"reply": "Theo biểu phí đã xác thực.", "citations": [{**source, "source_id": "SRC-003", "relevant_snippet": "Biểu phí sạc.", "applicable_models": ["ALL"]}]}
    monkeypatch.setattr(api, "process_chat_message", grounded_faq)
    token = await get_auth_token(client, "customer@vinfast.vn", "customer123")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "session_id": "sess_faq_test_01",
        "message": "Tôi muốn biết chi phí sạc pin tại trụ sạc công cộng của VinFast là bao nhiêu?",
        "client_context": {
            "mock_customer_id": "CUST_MOCK_01",
            "vehicle_model": "VF8",
            "vehicle_code_mock": "VF-SF-00231",
        },
    }
    res = await client.post("/api/v1/customer/chat", json=payload, headers=headers)
    assert res.status_code == 200
    body = res.json()

    assert body["success"] is True
    data = body["data"]
    assert data["response_type"] == "FAQ_ANSWER"
    assert data["citations"] is not None
    assert len(data["citations"]) > 0
    assert data["service_handoff"] is not None


@pytest.mark.asyncio
async def test_customer_cases_and_status(client):
    """Kiểm tra GET /api/v1/customer/cases và /customer/cases/{id}/status theo api-contract.md 2.2 & 2.3."""
    token = await get_auth_token(client, "customer@vinfast.vn", "customer123")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Danh sách case của Customer
    res_list = await client.get("/api/v1/customer/cases", headers=headers)
    assert res_list.status_code == 200
    body_list = res_list.json()
    assert body_list["success"] is True
    assert body_list["data"]["total"] >= 1

    # 2. Chi tiết trạng thái case
    res_status = await client.get("/api/v1/customer/cases/CASE-20260924-001/status", headers=headers)
    assert res_status.status_code == 200
    body_status = res_status.json()
    assert body_status["data"]["case_id"] == "CASE-20260924-001"
    assert "status" in body_status["data"]


@pytest.mark.asyncio
async def test_customer_reopen_and_feedback(client):
    """Kiểm tra Reopen và gửi Feedback của Customer (api-contract.md 2.3)."""
    token2 = await get_auth_token(client, "customer2@vinfast.vn", "customer123")
    headers2 = {"Authorization": f"Bearer {token2}"}

    # 1. Gửi feedback cho case đã xử lý (CASE-20260924-004)
    feedback_res = await client.post(
        "/api/v1/customer/cases/CASE-20260924-004/feedback",
        json={"rating": 5, "comment": "Tư vấn rất tốt!"},
        headers=headers2,
    )
    assert feedback_res.status_code == 200
    assert feedback_res.json()["data"]["success"] is True

    # 2. Mở lại (reopen) case đã Resolved
    reopen_res = await client.post(
        "/api/v1/customer/cases/CASE-20260924-004/reopen",
        headers=headers2,
    )
    assert reopen_res.status_code == 200
    assert reopen_res.json()["data"]["status"] == "Reopened"


@pytest.mark.asyncio
async def test_staff_ticket_queue_and_actions(client):
    """Kiểm tra Staff APIs: queue, detail kèm attachment, APPROVE và RESOLVE."""
    staff_token = await get_auth_token(client, "staff@vinfast.vn", "staff123")
    headers = {"Authorization": f"Bearer {staff_token}"}

    # 1. Lấy danh sách queue
    res_queue = await client.get("/api/v1/staff/tickets", headers=headers)
    assert res_queue.status_code == 200
    queue_data = res_queue.json()["data"]
    assert queue_data["total"] >= 4

    # 2. Lấy chi tiết ticket kèm ảnh đính kèm (CASE-20260924-001)
    res_detail = await client.get("/api/v1/staff/tickets/CASE-20260924-001", headers=headers)
    assert res_detail.status_code == 200
    detail_data = res_detail.json()["data"]
    assert detail_data["case"]["id"] == "CASE-20260924-001"
    assert len(detail_data["attachments"]) >= 1
    assert detail_data["attachments"][0]["attachment_id"] == "ATT-20260930-001"

    # 3. Staff thực hiện action APPROVE
    res_approve = await client.post(
        "/api/v1/staff/tickets/CASE-20260924-001/actions",
        json={"action": "APPROVE", "staff_id": "STAFF_001", "notes": "Đã duyệt tiếp nhận."},
        headers=headers,
    )
    assert res_approve.status_code == 200

    # 4. Staff thực hiện action RESOLVE (Mới bổ sung theo spec)
    res_resolve = await client.post(
        "/api/v1/staff/tickets/CASE-20260924-001/actions",
        json={"action": "RESOLVE", "staff_id": "STAFF_001", "notes": "Đã xử lý xong."},
        headers=headers,
    )
    assert res_resolve.status_code == 200

    # Kiểm tra trạng thái cuối là Resolved
    detail_after = await client.get("/api/v1/staff/tickets/CASE-20260924-001", headers=headers)
    assert detail_after.json()["data"]["case"]["status"] == "Resolved"
