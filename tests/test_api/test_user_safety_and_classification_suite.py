import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, get_db
from src.main import app
from src.models.db_models import User
from src.services.auth import get_optional_user, require_customer


@pytest.fixture
def chat_client_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'suite_test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(
            id="cust_test_suite",
            username="nguyen_van_an",
            password_hash="hashed",
            role="CUSTOMER",
            mock_customer_id="CUST_MOCK_01",
        )
        db.add(user)
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_customer] = lambda: user
        app.dependency_overrides[get_optional_user] = lambda: user
        yield db
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.asyncio
async def test_case_1_turtle_definition(client, chat_client_db, monkeypatch):
    """1. Biểu tượng con rùa vàng nghĩa là gì? -> FAQ, giải thích, không banner, không xin vị trí, có chip bridge."""
    import src.api.customer as api
    async def mock_ai(*args, **kwargs):
        return {
            "reply": "Biểu tượng con rùa màu vàng (Turtle Mode) là chế độ bảo vệ khi xe bị giới hạn công suất.",
            "citations": [],
            "suggested_replies": [],
        }
    monkeypatch.setattr(api, "process_chat_message", mock_ai)

    resp = await client.post(
        "/api/v1/customer/chat",
        json={"session_id": "test_s1", "message": "Biểu tượng con rùa vàng nghĩa là gì?"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["response_type"] == "FAQ_ANSWER"
    assert data["priority"] in (None, "LOW")
    assert data["show_emergency_banner"] is False
    assert data["request_location"] is False
    assert "Xe tôi đang hiện biểu tượng này" in data["suggested_replies"]


@pytest.mark.asyncio
async def test_case_2_turtle_active_vehicle(client, chat_client_db):
    """2. Xe tôi đang hiện rùa vàng, nghĩa là gì? -> Giải thích kèm hỏi nhẹ tình trạng, chưa bật CRITICAL."""
    resp = await client.post(
        "/api/v1/customer/chat",
        json={"session_id": "test_s2", "message": "Xe tôi đang hiện rùa vàng, nghĩa là gì?"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Chưa bật CRITICAL, không có banner khẩn cấp, không xin vị trí
    assert data["priority"] != "CRITICAL"
    assert data["show_emergency_banner"] is False
    assert data["request_location"] is False
    # Giải thích kèm hỏi tình trạng vận hành
    assert "chế độ bảo vệ an toàn" in data["message"]
    assert "di chuyển" in data["message"]


@pytest.mark.asyncio
async def test_case_3_turtle_on_highway_critical(client, chat_client_db):
    """3. Xe hiện rùa vàng và đang trên cao tốc -> Sự cố CRITICAL, banner, hotline, xin vị trí."""
    resp = await client.post(
        "/api/v1/customer/chat",
        json={"session_id": "test_s3", "message": "Xe hiện rùa vàng và đang trên cao tốc"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["response_type"] == "CASE_CREATED"
    assert data["priority"] == "CRITICAL"
    assert data["show_emergency_banner"] is True
    assert data["request_location"] is True
    assert "1900-232389" in data["safe_guidance"] or "1900-232389" in data["message"]


@pytest.mark.asyncio
async def test_case_4_cannot_charge_is_incident(client, chat_client_db):
    """4. Tại sao xe tôi không sạc được? -> Incident (hỏi làm rõ), không phải FAQ."""
    resp = await client.post(
        "/api/v1/customer/chat",
        json={"session_id": "test_s4", "message": "Tại sao xe tôi không sạc được?"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Phải là CLARIFICATION incident, KHÔNG được là FAQ_ANSWER
    assert data["response_type"] == "CLARIFICATION"
    assert data["show_emergency_banner"] is False
    assert data["request_location"] is False


@pytest.mark.asyncio
async def test_case_5_maintenance_12k_is_faq(client, chat_client_db, monkeypatch):
    """5. Khi nào cần bảo dưỡng 12.000km? -> FAQ."""
    import src.api.customer as api
    async def mock_ai(*args, **kwargs):
        return {
            "reply": "Mốc bảo dưỡng 12.000km hoặc 1 năm là kỳ bảo dưỡng cấp 1 của VinFast.",
            "citations": [],
            "suggested_replies": [],
        }
    monkeypatch.setattr(api, "process_chat_message", mock_ai)

    resp = await client.post(
        "/api/v1/customer/chat",
        json={"session_id": "test_s5", "message": "Khi nào cần bảo dưỡng 12.000km?"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["response_type"] == "FAQ_ANSWER"
    assert data["show_emergency_banner"] is False
    assert data["request_location"] is False


@pytest.mark.asyncio
async def test_case_6_smoke_with_explanation_is_critical(client, chat_client_db):
    """6. Xe bốc khói, giải thích giúp tôi vì sao -> CRITICAL dù có chữ 'giải thích'."""
    resp = await client.post(
        "/api/v1/customer/chat",
        json={"session_id": "test_s6", "message": "Xe bốc khói, giải thích giúp tôi vì sao"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["response_type"] == "CASE_CREATED"
    assert data["priority"] == "CRITICAL"
    assert data["show_emergency_banner"] is True
    assert data["request_location"] is True


@pytest.mark.asyncio
async def test_case_7_charging_pricing_is_faq(client, chat_client_db, monkeypatch):
    """7. Trạm sạc VinFast tính phí thế nào? -> FAQ, không xin vị trí."""
    import src.api.customer as api
    async def mock_ai(*args, **kwargs):
        return {
            "reply": "Đơn giá sạc VinFast là 3.858 VNĐ/kWh theo quy định niêm yết.",
            "citations": [],
            "suggested_replies": [],
        }
    monkeypatch.setattr(api, "process_chat_message", mock_ai)

    resp = await client.post(
        "/api/v1/customer/chat",
        json={"session_id": "test_s7", "message": "Trạm sạc VinFast tính phí thế nào?"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["response_type"] == "FAQ_ANSWER"
    assert data["show_emergency_banner"] is False
    assert data["request_location"] is False


@pytest.mark.asyncio
async def test_case_8_find_station_near_me_requests_location(client, chat_client_db, monkeypatch):
    """8. Tìm trạm sạc gần tôi -> Hiện thanh xin vị trí."""
    import src.api.customer as api
    async def mock_ai(*args, **kwargs):
        return {
            "reply": "Anh/chị vui lòng chia sẻ vị trí để em hiển thị trạm sạc gần nhất nhé.",
            "citations": [],
            "suggested_replies": [],
        }
    monkeypatch.setattr(api, "process_chat_message", mock_ai)

    resp = await client.post(
        "/api/v1/customer/chat",
        json={"session_id": "test_s8", "message": "Tìm trạm sạc gần tôi"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["request_location"] is True
    assert data["show_emergency_banner"] is False


@pytest.mark.asyncio
async def test_issue_2_greeting_salutation_and_branding(client, chat_client_db):
    """Vấn đề 2: Lời chào tự nhiên với tên khách An, đồng nhất Trợ lý VF Serv, không undefined."""
    resp = await client.post(
        "/api/v1/customer/chat",
        json={
            "session_id": "test_greeting",
            "message": "Xin chào",
            "client_context": {"customer_name": "Nguyễn Văn An", "vehicle_model": "VF8"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "Chào anh An!" in data["message"]
    assert "anh" in data["message"]
    assert "undefined" not in data["message"]
    assert "anh/chị" not in data["message"]
    assert "24/7" not in data["message"]  # không lặp header
