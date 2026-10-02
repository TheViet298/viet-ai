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
async def test_customer_chat_faq(client):
    """Kiểm tra khách hàng hỏi thông tin sạc (FAQ answer kèm citation và service handoff)."""
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
    assert len(detail_after.json()["data"]["updates"]) >= 1


@pytest.mark.asyncio
async def test_guest_chat_trial(client):
    """Kiểm tra Guest trial: tối đa 5 lượt chat, trả remaining_guest_messages, chặn lượt thứ 6 (ADR-005 & api-contract.md 1)."""
    import uuid

    guest_session = f"guest_{uuid.uuid4().hex[:8]}"

    # Lượt 1 đến 5: Thành công và remaining_guest_messages giảm dần từ 4 xuống 0
    for i in range(5):
        payload = {
            "session_id": guest_session,
            "guest_session_id": guest_session,
            "message": f"Tôi muốn hỏi về ứng dụng VinFast lần {i + 1}",
        }
        res = await client.post("/api/v1/customer/chat", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["data"]["remaining_guest_messages"] == 4 - i

    # Lượt thứ 6: Bị chặn 403 Forbidden
    payload_blocked = {
        "session_id": guest_session,
        "guest_session_id": guest_session,
        "message": "Tôi muốn hỏi thêm lần thứ 6",
    }
    res_blocked = await client.post("/api/v1/customer/chat", json=payload_blocked)
    assert res_blocked.status_code == 403
    assert "hết 5 lượt chat" in res_blocked.json()["detail"]


@pytest.mark.asyncio
async def test_customer_location_and_service_points(client):
    """Kiểm tra Chia sẻ vị trí (Consent) và Gợi ý Điểm hỗ trợ/Trạm sạc theo sự cố (ADR-005)."""
    token = await get_auth_token(client, "customer@vinfast.vn", "customer123")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Khách hàng chia sẻ vị trí sự cố
    loc_payload = {
        "case_id": "CASE-20260924-001",
        "status": "CONSENTED",
        "source": "MAP_PICKER",
        "location_label": "Trạm sạc Vincom Metropolis Liễu Giai, Ba Đình, Hà Nội",
        "latitude": 21.0315,
        "longitude": 105.8145,
        "precision": "EXACT",
        "share_with_staff": True,
    }
    res_loc = await client.post("/api/v1/customer/location", json=loc_payload, headers=headers)
    assert res_loc.status_code == 200
    loc_body = res_loc.json()
    assert loc_body["success"] is True
    assert loc_body["data"]["location_label"] == "Trạm sạc Vincom Metropolis Liễu Giai, Ba Đình, Hà Nội"
    assert loc_body["data"]["latitude"] == 21.0315

    # 2. Lấy gợi ý điểm hỗ trợ (Service Points)
    res_sp = await client.get("/api/v1/customer/cases/CASE-20260924-001/service-points", headers=headers)
    assert res_sp.status_code == 200
    sp_body = res_sp.json()
    assert sp_body["success"] is True
    assert len(sp_body["data"]["recommended_points"]) >= 3
    # Case 001 là Charging/Battery nên trạm sạc được ưu tiên lên đầu
    assert sp_body["data"]["recommended_points"][0]["category"] == "CHARGING_STATION"


@pytest.mark.asyncio
async def test_customer_confirmation_flow(client):
    """Kiểm tra luồng xác nhận Customer Confirmation: STILL_UNRESOLVED -> Reopened; RESOLVED_CONFIRMED -> Closed (ADR-005)."""
    cust_token = await get_auth_token(client, "customer@vinfast.vn", "customer123")
    cust_headers = {"Authorization": f"Bearer {cust_token}"}
    staff_token = await get_auth_token(client, "staff@vinfast.vn", "staff123")
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    # 1. Staff Resolve Case 003
    res_resolve = await client.post(
        "/api/v1/staff/tickets/CASE-20260924-003/actions",
        json={"action": "RESOLVE", "staff_id": "STAFF_001", "notes": "Đã hướng dẫn khách sử dụng bộ sạc đúng cách."},
        headers=staff_headers,
    )
    assert res_resolve.status_code == 200

    # 2. Customer phản hồi STILL_UNRESOLVED -> chuyển thành Reopened
    res_unresolved = await client.post(
        "/api/v1/customer/cases/CASE-20260924-003/confirmation",
        json={"confirmation": "STILL_UNRESOLVED", "feedback_note": "Cắm lại vẫn không sạc được."},
        headers=cust_headers,
    )
    assert res_unresolved.status_code == 200
    assert res_unresolved.json()["data"]["status"] == "Reopened"

    # 3. Staff Resolve lại
    await client.post(
        "/api/v1/staff/tickets/CASE-20260924-003/actions",
        json={"action": "RESOLVE", "staff_id": "STAFF_001", "notes": "Kỹ thuật đã qua kiểm tra ổ cắm."},
        headers=staff_headers,
    )

    # 4. Customer phản hồi RESOLVED_CONFIRMED -> chuyển thành Closed
    res_confirmed = await client.post(
        "/api/v1/customer/cases/CASE-20260924-003/confirmation",
        json={"confirmation": "RESOLVED_CONFIRMED", "feedback_note": "Xe đã sạc bình thường."},
        headers=cust_headers,
    )
    assert res_confirmed.status_code == 200
    assert res_confirmed.json()["data"]["status"] == "Closed"


@pytest.mark.asyncio
async def test_customer_case_search_and_detail(client):
    """Kiểm tra tìm kiếm case theo từ khóa/trạng thái và xem Customer Case Detail (api-contract.md 2.3)."""
    token = await get_auth_token(client, "customer@vinfast.vn", "customer123")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Tìm kiếm theo từ khóa 'VF8'
    res_search = await client.get("/api/v1/customer/cases?query=VF8", headers=headers)
    assert res_search.status_code == 200
    search_body = res_search.json()
    assert search_body["success"] is True
    assert all("VF8" in c["vehicle_model"] for c in search_body["data"]["cases"])

    # 2. Xem Customer Case Detail
    res_detail = await client.get("/api/v1/customer/cases/CASE-20260924-001", headers=headers)
    assert res_detail.status_code == 200
    detail_body = res_detail.json()
    assert detail_body["success"] is True
    data = detail_body["data"]
    assert data["case"]["id"] == "CASE-20260924-001"
    assert data["case_brief"] is not None
    assert data["location"] is not None
    assert isinstance(data["updates"], list)
    assert isinstance(data["attachments"], list)
    assert isinstance(data["conversation_history"], list)


@pytest.mark.asyncio
async def test_public_support_insights(client):
    """Kiểm tra Thư viện tình huống thường gặp đã biên soạn/ẩn danh (api-contract.md 2.3 & ADR-005)."""
    res = await client.get("/api/v1/public/support-insights")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["total"] >= 5
    first_insight = body["data"]["items"][0]
    assert "title" in first_insight
    assert "symptom" in first_insight
    assert "recommended_action" in first_insight
    assert "hotline_support" in first_insight


@pytest.mark.asyncio
async def test_staff_dashboard_and_routing_directory(client):
    """Kiểm tra Staff Dashboard counter và Routing Directory (api-contract.md 3.1.1)."""
    staff_token = await get_auth_token(client, "staff@vinfast.vn", "staff123")
    headers = {"Authorization": f"Bearer {staff_token}"}

    # 1. Staff Dashboard
    res_dash = await client.get("/api/v1/staff/dashboard", headers=headers)
    assert res_dash.status_code == 200
    dash_body = res_dash.json()
    assert dash_body["success"] is True
    data = dash_body["data"]
    assert "critical_count" in data
    assert "staff_reviewing_count" in data
    assert "needs_information_count" in data
    assert "resolved_today_count" in data
    assert data["total_cases_count"] >= 4

    # 2. Staff Routing Directory
    res_routing = await client.get("/api/v1/staff/routing-directory", headers=headers)
    assert res_routing.status_code == 200
    routing_body = res_routing.json()
    assert routing_body["success"] is True
    assert routing_body["data"]["total"] == 5
    dept_names = [d["name"] for d in routing_body["data"]["departments"]]
    assert "Charging Operations" in dept_names
    assert "Emergency Support Demo" in dept_names
