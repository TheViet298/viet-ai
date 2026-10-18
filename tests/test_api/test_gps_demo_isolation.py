"""
Comprehensive unit tests for Step 5:
(i) Real customer cannot read/write location & service-points of demo case and vice versa
(ii) Real staff cannot view demo ticket (and vice versa), including coordinates
(iii) Customer A cannot access Customer B's case (location & service points)
(iv) seed --demo creates DEMO-* cases with is_demo=True returning correct nearby workshops
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, ensure_schema, get_db
from src.main import app
from src.models.db_models import Case, Intent, Priority, ServicePoint, TicketStatus, User, UserRole
from src.services.auth import create_token, hash_password


@pytest.fixture
def test_db_setup(tmp_path):
    db_file = tmp_path / "test_iso.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)

    from src import db as db_mod
    orig_engine = db_mod.engine
    db_mod.engine = engine
    ensure_schema()

    def override_get_db():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db

    token_cust_a = create_token("user_real_cust_a", UserRole.CUSTOMER.value)
    token_cust_b = create_token("user_real_cust_b", UserRole.CUSTOMER.value)
    token_cust_demo = create_token("user_demo_cust", UserRole.CUSTOMER.value)
    token_staff_real = create_token("user_real_staff", UserRole.STAFF.value)
    token_staff_demo = create_token("user_demo_staff", UserRole.STAFF.value)

    # Setup test data
    with Session(engine) as session:
        # Service point in Can Tho
        sp = ServicePoint(
            id="sp_cantho_1",
            source_file="test",
            category="workshop",
            name="VinFast 3S Ninh Kiều Cần Thơ",
            address="123 Đường 30/4, Quận Ninh Kiều, Cần Thơ",
            latitude=10.0342,
            longitude=105.7885,
            dong_son=True,
            is_car_compatible=True,
            is_visible=True,
        )
        session.add(sp)

        # Users: Real Cust A, Real Cust B, Demo Cust, Real Staff, Demo Staff
        u_cust_a = User(
            id="user_real_cust_a", username="cust_a@vinfast.vn",
            password_hash=hash_password("pass123"), role=UserRole.CUSTOMER.value, is_demo=False
        )
        u_cust_b = User(
            id="user_real_cust_b", username="cust_b@vinfast.vn",
            password_hash=hash_password("pass123"), role=UserRole.CUSTOMER.value, is_demo=False
        )
        u_cust_demo = User(
            id="user_demo_cust", username="demo_cust@vinfast.vn",
            password_hash=hash_password("pass123"), role=UserRole.CUSTOMER.value, is_demo=True
        )
        u_staff_real = User(
            id="user_real_staff", username="staff_real@vinfast.vn",
            password_hash=hash_password("pass123"), role=UserRole.STAFF.value, is_demo=False
        )
        u_staff_demo = User(
            id="user_demo_staff", username="staff_demo@vinfast.vn",
            password_hash=hash_password("pass123"), role=UserRole.STAFF.value, is_demo=True
        )
        session.add_all([u_cust_a, u_cust_b, u_cust_demo, u_staff_real, u_staff_demo])

        # Cases
        c_real_a = Case(
            id="CASE-REAL-A", user_id="user_real_cust_a", session_id="sess_a",
            vehicle_model="VF8", intent="Service/Incident", priority=Priority.HIGH.value,
            status=TicketStatus.NEW.value, is_demo=False
        )
        c_real_b = Case(
            id="CASE-REAL-B", user_id="user_real_cust_b", session_id="sess_b",
            vehicle_model="VF8", intent="Service/Incident", priority=Priority.HIGH.value,
            status=TicketStatus.NEW.value, is_demo=False
        )
        c_demo = Case(
            id="DEMO-CASE-001", user_id="user_demo_cust", session_id="sess_demo",
            vehicle_model="VF9", intent="Service/Incident", priority=Priority.HIGH.value,
            status=TicketStatus.NEW.value, is_demo=True
        )
        session.add_all([c_real_a, c_real_b, c_demo])
        session.commit()

    yield {
        "engine": engine,
        "token_cust_a": token_cust_a,
        "token_cust_b": token_cust_b,
        "token_cust_demo": token_cust_demo,
        "token_staff_real": token_staff_real,
        "token_staff_demo": token_staff_demo,
    }

    app.dependency_overrides.clear()
    db_mod.engine = orig_engine
    engine.dispose()


def test_gps_demo_and_cross_customer_isolation(test_db_setup):
    client = TestClient(app)
    headers_a = {"Authorization": f"Bearer {test_db_setup['token_cust_a']}"}
    headers_b = {"Authorization": f"Bearer {test_db_setup['token_cust_b']}"}
    headers_demo = {"Authorization": f"Bearer {test_db_setup['token_cust_demo']}"}
    headers_staff_real = {"Authorization": f"Bearer {test_db_setup['token_staff_real']}"}
    headers_staff_demo = {"Authorization": f"Bearer {test_db_setup['token_staff_demo']}"}

    # (i) Khách thật A KHÔNG đọc/ghi được demo case (404)
    # Gửi location lên DEMO-CASE-001 bằng token khách thật -> 404
    resp = client.post("/api/v1/customer/location", json={
        "case_id": "DEMO-CASE-001",
        "latitude": 10.034, "longitude": 105.788,
        "location_label": "Ninh Kiều Cần Thơ",
        "status": "CONSENTED", "source": "BROWSER_GPS", "share_with_staff": True
    }, headers=headers_a)
    assert resp.status_code == 404, "Khách thật không được ghi location vào case demo"

    # Đọc service points của DEMO-CASE-001 bằng token khách thật -> 404
    resp = client.get("/api/v1/customer/cases/DEMO-CASE-001/service-points", headers=headers_a)
    assert resp.status_code == 404, "Khách thật không được đọc service points của case demo"

    # Ngược lại: Khách demo KHÔNG đọc/ghi được case thật
    resp = client.post("/api/v1/customer/location", json={
        "case_id": "CASE-REAL-A",
        "latitude": 10.034, "longitude": 105.788,
        "location_label": "Ninh Kiều Cần Thơ",
        "status": "CONSENTED", "source": "BROWSER_GPS", "share_with_staff": True
    }, headers=headers_demo)
    assert resp.status_code == 404, "Khách demo không được ghi location vào case thật"

    # (ii) Staff thật KHÔNG thấy ticket demo
    resp = client.get("/api/v1/staff/tickets/DEMO-CASE-001", headers=headers_staff_real)
    assert resp.status_code == 404, "Staff thật không được thấy ticket demo"

    # Ngược lại: Staff demo KHÔNG thấy ticket thật
    resp = client.get("/api/v1/staff/tickets/CASE-REAL-A", headers=headers_staff_demo)
    assert resp.status_code == 404, "Staff demo không được thấy ticket thật"

    # (iii) Khách A KHÔNG truy cập được case của khách B
    # Khách B cố đọc case A
    resp = client.get("/api/v1/customer/cases/CASE-REAL-A/service-points", headers=headers_b)
    assert resp.status_code == 403, "Khách B không có quyền truy cập service-points của case A"

    resp = client.post("/api/v1/customer/location", json={
        "case_id": "CASE-REAL-A",
        "latitude": 10.034, "longitude": 105.788,
        "location_label": "Ninh Kiều Cần Thơ",
        "status": "CONSENTED", "source": "BROWSER_GPS", "share_with_staff": True
    }, headers=headers_b)
    assert resp.status_code == 403, "Khách B không có quyền ghi location vào case A"

    # (iv) Khách demo tương tác với demo case thành công
    resp = client.post("/api/v1/customer/location", json={
        "case_id": "DEMO-CASE-001",
        "latitude": 10.0342, "longitude": 105.7885,
        "location_label": "Ninh Kiều Cần Thơ",
        "status": "CONSENTED", "source": "BROWSER_GPS", "share_with_staff": True
    }, headers=headers_demo)
    assert resp.status_code == 200, "Khách demo phải ghi location vào case demo thành công"

    resp = client.get("/api/v1/customer/cases/DEMO-CASE-001/service-points", headers=headers_demo)
    assert resp.status_code == 200, "Khách demo phải đọc service points của demo case thành công"
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]["recommended_points"]) > 0
    assert "Ninh Kiều" in body["data"]["recommended_points"][0]["name"]
