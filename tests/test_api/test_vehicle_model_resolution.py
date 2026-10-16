import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, get_db
from src.main import app
from src.models.db_models import User, Case, CaseBrief, UserRole
from src.services.auth import get_optional_user, require_customer, require_staff


@pytest.fixture
def resolution_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'resolution.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user_vf8 = User(
            id="cust-vf8-id",
            username="cust_vf8@vinfast.vn",
            password_hash="unused",
            role="CUSTOMER",
            vehicle_model="VF8",
            full_name="Nguyễn Văn A",
            mock_customer_id="CUST_VF8_01",
        )
        user_vf3 = User(
            id="cust-vf3-id",
            username="cust_vf3@vinfast.vn",
            password_hash="unused",
            role="CUSTOMER",
            vehicle_model="VF3",
            full_name="Trần Thị B",
            mock_customer_id="CUST_VF3_01",
        )
        user_none = User(
            id="cust-none-id",
            username="cust_none@vinfast.vn",
            password_hash="unused",
            role="CUSTOMER",
            vehicle_model=None,
            full_name="Lê Văn C",
            mock_customer_id="CUST_NONE_01",
        )
        staff_user = User(
            id="staff-test-id",
            username="staff_test@vinfast.vn",
            password_hash="unused",
            role="STAFF",
            is_demo=False,
        )
        db.add_all([user_vf8, user_vf3, user_none, staff_user])
        db.commit()

        app.dependency_overrides[get_db] = lambda: db
        yield {"db": db, "vf8": user_vf8, "vf3": user_vf3, "none": user_none, "staff": staff_user}

    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.asyncio
async def test_1_consultation_vf7_then_incident_resolves_to_profile_vf8(client, resolution_db):
    user = resolution_db["vf8"]
    app.dependency_overrides[require_customer] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    session_id = "test-session-resolve-01"

    # Turn 1: Tư vấn về VF 7
    r1 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "Tư vấn về VF 7"
    })
    assert r1.status_code == 200
    d1 = r1.json()["data"]
    assert "VF 7" in d1["message"] or "VF7" in d1["message"]

    # Turn 2: Chuyển ngữ cảnh sang sự cố
    r2 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "xe tôi gặp sự cố về pin"
    })
    assert r2.status_code == 200
    d2 = r2.json()["data"]
    # PHẢI bắt VF8 từ hồ sơ, KHÔNG được bắt VF7 từ câu tư vấn trước!
    assert "VF8" in d2["message"], f"Expected VF8 from user profile, got: {d2['message']}"
    assert "VF7" not in d2["message"], f"Should not inherit VF7 into incident: {d2['message']}"


@pytest.mark.asyncio
async def test_2_explicit_user_stated_model_in_incident_overrides_profile(client, resolution_db):
    user = resolution_db["vf8"]
    app.dependency_overrides[require_customer] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    session_id = "test-session-resolve-02"
    r = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "VF7 của tôi báo lỗi trên màn hình"
    })
    assert r.status_code == 200
    d = r.json()["data"]
    assert "VF7" in d["message"]


@pytest.mark.asyncio
async def test_3_incident_phrase_xe_minh_sac_khong_vao_resolves_to_profile(client, resolution_db):
    user = resolution_db["vf8"]
    app.dependency_overrides[require_customer] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    session_id = "test-session-resolve-03"
    # Turn 1: Hỏi tư vấn VF7 trước
    r1 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "Tư vấn về xe VF 7"
    })
    assert r1.status_code == 200

    # Turn 2: Chuyển sang sự cố với cụm từ "xe mình" + "sạc không vào điện"
    r2 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "xe mình sạc không vào điện"
    })
    assert r2.status_code == 200
    d = r2.json()["data"]
    # Bắt buộc chuyển sang sự cố và nhận diện xe VF8 từ hồ sơ, KHÔNG nhận VF7
    assert "VF8" in d["message"]
    assert "VF7" not in d["message"]
    assert d.get("response_type") == "CLARIFICATION"


@pytest.mark.asyncio
async def test_4_xe_toi_nen_mua_gi_stays_consultation(client, resolution_db):
    user = resolution_db["vf8"]
    app.dependency_overrides[require_customer] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    session_id = "test-session-resolve-04"
    r = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "xe tôi nên mua gì để đi làm hàng ngày?"
    })
    assert r.status_code == 200
    d = r.json()["data"]
    # Không tạo incident case, không kích hoạt luồng sự cố
    assert d.get("case_id") is None
    assert d.get("response_type") == "FAQ_ANSWER"


@pytest.mark.asyncio
async def test_5_guest_or_empty_profile_asks_for_model(client, resolution_db):
    user = resolution_db["none"]
    app.dependency_overrides[require_customer] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    session_id = "test-session-resolve-05"
    r = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "xe tôi gặp sự cố về pin"
    })
    assert r.status_code == 200
    d = r.json()["data"]
    # Vì hồ sơ trống không có model, hệ thống phải hỏi lại dòng xe
    assert "dòng xe nào" in d["message"].lower() or "chưa xác định dòng" in d["message"].lower()
    assert any(m in (d.get("suggested_replies") or []) for m in ["VF3", "VF5", "VF8"])


@pytest.mark.asyncio
async def test_6_incident_then_consultation_vf5_returns_vf5_card(client, resolution_db):
    user = resolution_db["vf8"]
    app.dependency_overrides[require_customer] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    session_id = "test-session-resolve-06"
    # Turn 1: Sự cố
    r1 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "xe tôi gặp sự cố về pin"
    })
    assert r1.status_code == 200

    # Turn 2: Hỏi tư vấn VF5
    r2 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "tư vấn về xe VF 5"
    })
    assert r2.status_code == 200
    d2 = r2.json()["data"]
    assert "VF 5" in d2["message"] or "VF5" in d2["message"]


@pytest.mark.asyncio
async def test_7_consultation_vf8_from_account_vf3_returns_vf8_with_comparison(client, resolution_db):
    user = resolution_db["vf3"]
    app.dependency_overrides[require_customer] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    session_id = "test-session-resolve-07"
    r = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "Tư vấn về VF 8"
    })
    assert r.status_code == 200
    d = r.json()["data"]
    assert "VF 8" in d["message"] or "VF8" in d["message"]
    # Gợi mở so sánh với VF3 mà tài khoản đang sở hữu
    assert "VF 3" in d["message"] or "VF3" in d["message"]


@pytest.mark.asyncio
async def test_8_profile_incident_light_confirmation_chips(client, resolution_db):
    user = resolution_db["vf8"]
    app.dependency_overrides[require_customer] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    session_id = "test-session-resolve-08"
    r = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "xe tôi gặp sự cố về pin"
    })
    assert r.status_code == 200
    d = r.json()["data"]
    # Hỏi xác nhận nhẹ dòng xe từ hồ sơ kèm chip "Đúng" / "Xe khác"
    assert "VF8" in d["message"]
    replies = d.get("suggested_replies") or []
    assert any("Đúng" in rep for rep in replies)
    assert any("Xe khác" in rep for rep in replies)


@pytest.mark.asyncio
async def test_8b_customer_ignores_chip_and_types_symptom_no_repeat_prompt(client, resolution_db):
    user = resolution_db["vf8"]
    app.dependency_overrides[require_customer] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    session_id = "test-session-resolve-08b"
    # Turn 1: Hỏi xác nhận nhẹ
    r1 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "xe tôi gặp sự cố về pin"
    })
    assert r1.status_code == 200
    d1 = r1.json()["data"]
    assert any("Đúng" in rep for rep in (d1.get("suggested_replies") or []))

    # Turn 2: Khách BỎ QUA chip và gõ tiếp triệu chứng
    r2 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "trụ sạc P02 báo đèn đỏ không nhận xe"
    })
    assert r2.status_code == 200
    d2 = r2.json()["data"]
    # Bot tiếp tục với VF8, KHÔNG lặp lại câu hỏi xác nhận và KHÔNG lặp lại chip Đúng / Xe khác
    assert "VF8" in d2["message"]
    replies2 = d2.get("suggested_replies") or []
    assert not any("Đúng" in rep for rep in replies2)
    assert not any("Xe khác" in rep for rep in replies2)


@pytest.mark.asyncio
async def test_8c_customer_clicks_xe_khac_and_chooses_vf5(client, resolution_db):
    user = resolution_db["vf8"]
    db = resolution_db["db"]
    app.dependency_overrides[require_customer] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    session_id = "test-session-resolve-08c"
    # Turn 1: Sự cố ban đầu nhận diện VF8 hồ sơ
    await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "xe tôi gặp sự cố về pin"
    })

    # Turn 2: Khách bấm "Xe khác"
    r2 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "Xe khác"
    })
    assert r2.status_code == 200
    d2 = r2.json()["data"]
    assert "dòng xe nào" in d2["message"].lower()

    # Turn 3: Khách chọn "VF5"
    r3 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "VF5"
    })
    assert r3.status_code == 200
    d3 = r3.json()["data"]
    case_id = d3.get("case_id")
    assert case_id is not None
    case = db.query(Case).filter(Case.id == case_id).first()
    assert case is not None
    assert case.vehicle_model == "VF5"
    assert case.vehicle_source == "user_stated"


@pytest.mark.asyncio
async def test_8d_customer_clicks_confirm_yes_marks_user_stated(client, resolution_db):
    user = resolution_db["vf8"]
    db = resolution_db["db"]
    app.dependency_overrides[require_customer] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    session_id = "test-session-resolve-08d"
    # Turn 1: Sự cố
    await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "xe tôi gặp sự cố về pin"
    })

    # Turn 2: Khách bấm "Đúng"
    r2 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "Đúng"
    })
    assert r2.status_code == 200
    d2 = r2.json()["data"]
    assert "VF8" in d2["message"]


@pytest.mark.asyncio
async def test_9_case_persists_vehicle_source_and_staff_endpoint_returns_it(client, resolution_db):
    user = resolution_db["vf8"]
    staff = resolution_db["staff"]
    db = resolution_db["db"]

    app.dependency_overrides[require_customer] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    session_id = "test-session-resolve-09"
    r = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "xe tôi gặp sự cố sạc tại trạm Vincom Landmark 81 trụ 03 báo lỗi CC01"
    })
    assert r.status_code == 200
    d = r.json()["data"]
    case_id = d.get("case_id")
    assert case_id is not None

    # Kiểm tra trong DB
    case = db.query(Case).filter(Case.id == case_id).first()
    assert case is not None
    assert case.vehicle_source == "profile"

    # Staff endpoint kiểm tra
    app.dependency_overrides[require_staff] = lambda: staff
    r_staff = await client.get("/api/v1/staff/tickets")
    assert r_staff.status_code == 200
    tickets = r_staff.json()["data"]["items"]
    target_ticket = next((t for t in tickets if t["id"] == case_id), None)
    assert target_ticket is not None
    assert target_ticket.get("vehicle_source") == "profile"
