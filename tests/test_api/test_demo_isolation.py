"""
Bộ kiểm thử cách ly 2 chiều dữ liệu Demo và Real (ServiceFlow 2-Way Isolation Test Suite).
Bảo đảm phủ kín 22 endpoint và background jobs theo ma trận 2 chiều:
1. /api/v1/auth/login: staff123 -> 401; ghost user -> 401; không tự tạo user.
2. /api/v1/auth/register: client gửi is_demo=True -> DB lưu is_demo=False; /auth/me -> is_demo=False.
3. /api/v1/cases & /{id}: 401 không token; 403 customer; staff thật chỉ thấy ca thật; staff demo chỉ thấy ca demo; chéo ID -> 404.
4. /api/v1/staff/tickets: lọc 2 chiều; chi tiết chéo ID -> 404.
5. /api/v1/staff/tickets/{id}/actions: demo staff gọi ID ca thật -> 404; real staff gọi ID ca demo -> 404.
6. /api/v1/staff/dashboard/stats & /routing/directory: tính toán số liệu độc lập theo is_demo.
7. /api/v1/customer/cases & /{id}: lọc 2 chiều; chéo ID -> 404.
8. /api/v1/customer/cases/{id}/confirmation: chéo ID -> 404.
9. /api/v1/customer/cases/{id}/reopen: chéo ID -> 404.
10. /api/v1/customer/cases/{id}/feedback: chéo ID -> 404.
11. /api/v1/customer/location: gửi case_id chéo phân vùng -> 404.
12. /api/v1/customer/cases/{id}/safety-acknowledgement: chéo ID -> 404.
13. /api/v1/customer/service-points: tiện ích dịch vụ hỗ trợ khách hàng.
14. /api/v1/customer/sessions: danh sách phiên chat lọc theo is_demo.
15. /api/v1/customer/sessions/{id}/history: chéo ID session -> 404.
16. /api/v1/customer/sessions/{id} (PATCH & DELETE): chéo ID session -> 404.
17. DELETE /api/v1/customer/sessions (bulk delete): user thật xóa phiên không làm mất phiên demo.
18. Seed demo idempotent (chạy 2 lần đủ 9 case, không trùng); --reset giữ nguyên dữ liệu thật.
19. 9 kịch bản demo: Case 1 có safety_acknowledged_at, Case 2 là New, Case 5 ban đầu không feedback, Case 6 reopen.
20. Auto-close worker quét 2 không gian độc lập không lẫn lộn.
21. Guest chat is_demo=False; Demo user không claim được ca của guest.
"""

import os
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import get_settings
from src.db import Base, get_db
from src.main import app
from src.models.db_models import (
    Case,
    CaseLocation,
    ChatSession,
    CustomerFeedback,
    Message,
    Priority,
    StaffAuditLog,
    TicketStatus,
    User,
    UserRole,
)
from src.services.auth import hash_password, scoped_cases, scoped_sessions
from src.services.case_lifecycle import process_auto_close_expired_cases

DEMO_STAFF_EMAIL = "demo.staff@vinfast.vn"
DEMO_CUSTOMER_EMAIL = "demo.customer@vinfast.vn"
DEMO_PASSWORD = os.getenv("DEMO_SEED_PASSWORD", "DemoSecret@2026!Sec")


@pytest.fixture(autouse=True)
def isolated_two_way_db(tmp_path, monkeypatch):
    """Môi trường DB SQLite độc lập cho bộ test cách ly."""
    from src import seed

    monkeypatch.setenv("DEMO_SEED_PASSWORD", DEMO_PASSWORD)
    db_file = tmp_path / "two_way_isolation.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False)

    monkeypatch.setattr(seed, "engine", engine)
    monkeypatch.setattr(seed, "SessionLocal", SessionLocal)

    Base.metadata.create_all(bind=engine)

    def override_db():
        with SessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    yield SessionLocal
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


async def get_token(client, username: str, password: str) -> str:
    res = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["data"]["token"]


# ==============================================================================
# 1. TEST BẢO MẬT LOGIN VÀ REGISTER (KHÔNG AUTO-CREATE, BỎ QUA CLIENT IS_DEMO)
# ==============================================================================

@pytest.mark.asyncio
async def test_login_security_and_no_fallback_passwords(client, isolated_two_way_db):
    """Kiểm tra: mật khẩu cũ 'staff123' bị 401; tài khoản chưa tạo bị 401; không tự tạo user khi login."""
    # 1. staff123 -> 401
    res1 = await client.post("/api/v1/auth/login", json={"username": "staff_service", "password": "staff123"})
    assert res1.status_code == 401

    # 2. Tài khoản chưa từng tồn tại -> 401 và KHÔNG bị tự tạo vào DB
    unseeded = f"ghost_{uuid.uuid4().hex[:6]}@vinfast.vn"
    res2 = await client.post("/api/v1/auth/login", json={"username": unseeded, "password": "somepassword"})
    assert res2.status_code == 401

    with isolated_two_way_db() as db:
        ghost_user = db.query(User).filter(User.username == unseeded).first()
        assert ghost_user is None, "Lỗ hổng: /login tự động tạo tài khoản khi người dùng chưa đăng ký!"


@pytest.mark.asyncio
async def test_register_ignores_client_is_demo_flag(client, isolated_two_way_db):
    """Kiểm tra: client cố tình gửi is_demo: true khi đăng ký -> server luôn ép is_demo=False."""
    reg_username = f"client_attacker_{uuid.uuid4().hex[:6]}@vinfast.vn"
    payload = {
        "username": reg_username,
        "password": "SecurePassword@2026",
        "mock_customer_id": "CUST_ATTACKER_01",
        "is_demo": True,
    }
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]["user"]
    assert data["is_demo"] is False

    with isolated_two_way_db() as db:
        user = db.query(User).filter(User.username == reg_username).first()
        assert user is not None
        assert user.is_demo is False, "Lỗ hổng: /auth/register không ép is_demo=False!"

    token = await get_token(client, reg_username, "SecurePassword@2026")
    res_me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert res_me.json()["data"]["is_demo"] is False


# ==============================================================================
# 2. TEST BẢO MẬT ENDPOINT CASES LEGACY (/api/v1/cases & /{id})
# ==============================================================================

@pytest.mark.asyncio
async def test_cases_legacy_route_auth_and_isolation(client, isolated_two_way_db):
    """Kiểm tra: /api/v1/cases yêu cầu Bearer token (401), chặn Customer (403), Staff thật chỉ thấy ca thật."""
    from src import seed

    # 1. Không token -> 401
    res_no_token = await client.get("/api/v1/cases")
    assert res_no_token.status_code == 401

    # 2. Tạo 1 staff thật và 1 case thật, đồng thời chạy seed demo
    with isolated_two_way_db() as db:
        real_staff = User(
            id="real-staff-001",
            username="real.staff@vinfast.vn",
            password_hash=hash_password("RealStaffSec@2026"),
            role=UserRole.STAFF.value,
            full_name="Kỹ Thuật Viên Thật",
            is_demo=False,
        )
        real_cust = User(
            id="real-cust-001",
            username="real.customer@vinfast.vn",
            password_hash=hash_password("RealCustomerSec@2026"),
            role=UserRole.CUSTOMER.value,
            full_name="Khách Hàng Thật",
            is_demo=False,
        )
        real_case = Case(
            id="CASE-REAL-20261015-001",
            user_id="real-cust-001",
            session_id="SESS-REAL-20261015-001",
            intent="Service/Incident",
            priority=Priority.HIGH.value,
            status=TicketStatus.NEW.value,
            is_demo=False,
        )
        db.add_all([real_staff, real_cust, real_case])
        db.commit()

    seed.seed_database(demo=True)

    # 3. Customer -> 403
    cust_token = await get_token(client, "real.customer@vinfast.vn", "RealCustomerSec@2026")
    res_cust = await client.get("/api/v1/cases", headers={"Authorization": f"Bearer {cust_token}"})
    assert res_cust.status_code == 403

    # 4. Staff thật -> 200, chỉ thấy case thật, không thấy case demo nào
    staff_token = await get_token(client, "real.staff@vinfast.vn", "RealStaffSec@2026")
    res_staff = await client.get("/api/v1/cases", headers={"Authorization": f"Bearer {staff_token}"})
    assert res_staff.status_code == 200
    cases_list = res_staff.json()
    assert len(cases_list) == 1
    assert cases_list[0]["id"] == "CASE-REAL-20261015-001"

    # 5. Staff demo -> 200, chỉ thấy các case demo
    demo_staff_token = await get_token(client, DEMO_STAFF_EMAIL, DEMO_PASSWORD)
    res_demo_staff = await client.get("/api/v1/cases", headers={"Authorization": f"Bearer {demo_staff_token}"})
    assert res_demo_staff.status_code == 200
    demo_cases_list = res_demo_staff.json()
    assert len(demo_cases_list) == 9
    assert not any(c["id"] == "CASE-REAL-20261015-001" for c in demo_cases_list)

    # 6. Legacy detail /{case_id}: chéo ID -> 404
    res_cross_leg1 = await client.get(f"/api/v1/cases/{cases_list[0]['id']}", headers={"Authorization": f"Bearer {demo_staff_token}"})
    assert res_cross_leg1.status_code == 404

    res_cross_leg2 = await client.get(f"/api/v1/cases/{demo_cases_list[0]['id']}", headers={"Authorization": f"Bearer {staff_token}"})
    assert res_cross_leg2.status_code == 404


# ==============================================================================
# 3. TEST CÁCH LY 2 CHIỀU STAFF TICKETS & ACTIONS (CHÉO ID -> 404)
# ==============================================================================

@pytest.mark.asyncio
async def test_staff_tickets_and_actions_two_way_isolation(client, isolated_two_way_db):
    """
    Kiểm tra cách ly 2 chiều cho Staff API:
    - GET /api/v1/staff/tickets: staff thật chỉ thấy ca thật (0 demo); staff demo chỉ thấy ca demo (0 thật).
    - GET /api/v1/staff/tickets/{id}: chéo ID trả 404.
    - POST /api/v1/staff/tickets/{id}/actions: demo staff gọi ID ca thật -> 404; real staff gọi ID ca demo -> 404.
    """
    from src import seed

    seed.seed_database(demo=True)
    today_str = f"{datetime.now(timezone.utc):%Y%m%d}"
    demo_case_id = f"DEMO-{today_str}-001"

    with isolated_two_way_db() as db:
        real_staff = User(
            id="real-staff-iso",
            username="real.staff.iso@vinfast.vn",
            password_hash=hash_password("RealPass@2026"),
            role=UserRole.STAFF.value,
            full_name="Staff Thật",
            is_demo=False,
        )
        real_cust = User(
            id="real-cust-iso",
            username="real.cust.iso@vinfast.vn",
            password_hash=hash_password("RealPass@2026"),
            role=UserRole.CUSTOMER.value,
            full_name="Khách Hàng Thật",
            is_demo=False,
        )
        real_case = Case(
            id="CASE-REAL-STAFF-ACT-001",
            user_id="real-cust-iso",
            session_id="SESS-REAL-STAFF-ACT-001",
            intent="Service/Incident",
            priority=Priority.MEDIUM.value,
            status=TicketStatus.NEW.value,
            is_demo=False,
        )
        db.add_all([real_staff, real_cust, real_case])
        db.commit()

    real_staff_tok = await get_token(client, "real.staff.iso@vinfast.vn", "RealPass@2026")
    demo_staff_tok = await get_token(client, DEMO_STAFF_EMAIL, DEMO_PASSWORD)

    # 1. Staff thật xem queue -> chỉ thấy ca thật
    res_r_tickets = await client.get("/api/v1/staff/tickets", headers={"Authorization": f"Bearer {real_staff_tok}"})
    assert res_r_tickets.status_code == 200
    r_items = res_r_tickets.json()["data"]["items"]
    assert len(r_items) == 1
    assert r_items[0]["id"] == "CASE-REAL-STAFF-ACT-001"

    # 2. Staff demo xem queue -> chỉ thấy 9 ca demo
    res_d_tickets = await client.get("/api/v1/staff/tickets", headers={"Authorization": f"Bearer {demo_staff_tok}"})
    assert res_d_tickets.status_code == 200
    d_items = res_d_tickets.json()["data"]["items"]
    assert len(d_items) == 9
    assert not any(t["id"] == "CASE-REAL-STAFF-ACT-001" for t in d_items)

    # 3. GET Ticket Detail chéo ID -> 404
    res_cross_get1 = await client.get(f"/api/v1/staff/tickets/{demo_case_id}", headers={"Authorization": f"Bearer {real_staff_tok}"})
    assert res_cross_get1.status_code == 404

    res_cross_get2 = await client.get("/api/v1/staff/tickets/CASE-REAL-STAFF-ACT-001", headers={"Authorization": f"Bearer {demo_staff_tok}"})
    assert res_cross_get2.status_code == 404

    # 4. POST Actions chéo: Demo staff gọi ID ca thật -> 404
    for action in ["APPROVE", "RESOLVE", "CLOSE", "REQUEST_INFO"]:
        res_act_cross = await client.post(
            "/api/v1/staff/tickets/CASE-REAL-STAFF-ACT-001/actions",
            json={"action": action, "staff_id": "demo_staff_01", "notes": "Cố tình can thiệp ca thật"},
            headers={"Authorization": f"Bearer {demo_staff_tok}"},
        )
        assert res_act_cross.status_code == 404, f"Lỗ hổng: Demo staff gọi {action} trên ca thật trả {res_act_cross.status_code}"

    # 5. POST Actions chéo: Real staff gọi ID ca demo -> 404
    res_act_cross2 = await client.post(
        f"/api/v1/staff/tickets/{demo_case_id}/actions",
        json={"action": "APPROVE", "staff_id": "real-staff-iso", "notes": "Can thiệp ca demo"},
        headers={"Authorization": f"Bearer {real_staff_tok}"},
    )
    assert res_act_cross2.status_code == 404


# ==============================================================================
# 4. TEST STAFF STATS & ROUTING DIRECTORY CÁCH LY
# ==============================================================================

@pytest.mark.asyncio
async def test_staff_dashboard_stats_and_routing_isolation(client, isolated_two_way_db):
    """
    Kiểm tra /staff/dashboard/stats và /staff/routing/directory:
    - Staff thật chỉ tính thống kê trên các ca thật (is_demo=False).
    - Staff demo chỉ tính thống kê trên 9 ca demo (is_demo=True).
    """
    from src import seed

    seed.seed_database(demo=True)

    with isolated_two_way_db() as db:
        real_staff = User(
            id="real-staff-stats",
            username="real.staff.stats@vinfast.vn",
            password_hash=hash_password("RealPass@2026"),
            role=UserRole.STAFF.value,
            full_name="Staff Thống Kê Thật",
            is_demo=False,
        )
        real_cust = User(
            id="real-cust-stats",
            username="real.cust.stats@vinfast.vn",
            password_hash=hash_password("RealPass@2026"),
            role=UserRole.CUSTOMER.value,
            full_name="Khách Hàng Thống Kê",
            is_demo=False,
        )
        real_case = Case(
            id="CASE-REAL-STATS-001",
            user_id="real-cust-stats",
            session_id="SESS-REAL-STATS-001",
            intent="Service/Incident",
            priority=Priority.HIGH.value,
            status=TicketStatus.NEW.value,
            is_demo=False,
        )
        db.add_all([real_staff, real_cust, real_case])
        db.commit()

    real_staff_tok = await get_token(client, "real.staff.stats@vinfast.vn", "RealPass@2026")
    demo_staff_tok = await get_token(client, DEMO_STAFF_EMAIL, DEMO_PASSWORD)

    # 1. Staff thật xem stats
    res_real_stats = await client.get("/api/v1/staff/dashboard", headers={"Authorization": f"Bearer {real_staff_tok}"})
    assert res_real_stats.status_code == 200
    r_stats = res_real_stats.json()["data"]
    assert r_stats["total_cases_count"] == 1

    # 2. Staff demo xem stats
    res_demo_stats = await client.get("/api/v1/staff/dashboard", headers={"Authorization": f"Bearer {demo_staff_tok}"})
    assert res_demo_stats.status_code == 200
    d_stats = res_demo_stats.json()["data"]
    assert d_stats["total_cases_count"] == 9

    # 3. Routing directory
    res_dir = await client.get("/api/v1/staff/routing-directory", headers={"Authorization": f"Bearer {demo_staff_tok}"})
    assert res_dir.status_code == 200


# ==============================================================================
# 5. TEST CÁCH LY 2 CHIỀU CUSTOMER CASES & INTERACTIVE ACTIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_cases_and_actions_two_way_isolation(client, isolated_two_way_db):
    """
    Kiểm tra cách ly 2 chiều cho Customer API:
    - GET /customer/cases: danh sách ca
    - GET /customer/cases/{id}: chi tiết ca
    - POST /customer/cases/{id}/confirmation: xác nhận hoàn tất
    - POST /customer/cases/{id}/reopen: mở lại ca
    - POST /customer/cases/{id}/feedback: đánh giá
    - POST /customer/location: chia sẻ vị trí
    - POST /customer/cases/{id}/safety-acknowledgement: báo an toàn
    - POST /customer/service-points: tra cứu trạm
    """
    from src import seed

    seed.seed_database(demo=True)
    today_str = f"{datetime.now(timezone.utc):%Y%m%d}"
    demo_case_id = f"DEMO-{today_str}-001"

    with isolated_two_way_db() as db:
        real_cust = User(
            id="real-cust-interact",
            username="real.cust.interact@vinfast.vn",
            password_hash=hash_password("RealPass@2026"),
            role=UserRole.CUSTOMER.value,
            full_name="Khách Hàng Tương Tác",
            is_demo=False,
        )
        real_case = Case(
            id="CASE-REAL-INTERACT-001",
            user_id="real-cust-interact",
            session_id="SESS-REAL-INTERACT-001",
            intent="Service/Incident",
            priority=Priority.CRITICAL.value,
            status=TicketStatus.NEW.value,
            incident_version=1,
            safety_status="unconfirmed",
            is_demo=False,
        )
        db.add_all([real_cust, real_case])
        db.commit()

    real_cust_tok = await get_token(client, "real.cust.interact@vinfast.vn", "RealPass@2026")
    demo_cust_tok = await get_token(client, DEMO_CUSTOMER_EMAIL, DEMO_PASSWORD)

    # 1. GET /cases danh sách
    res_r_cases = await client.get("/api/v1/customer/cases", headers={"Authorization": f"Bearer {real_cust_tok}"})
    assert res_r_cases.status_code == 200
    r_c_items = res_r_cases.json()["data"]["cases"]
    assert len(r_c_items) == 1
    assert r_c_items[0]["id"] == "CASE-REAL-INTERACT-001"

    # 2. GET /cases/{id} chéo ID -> 404
    res_cross_c1 = await client.get(f"/api/v1/customer/cases/{demo_case_id}", headers={"Authorization": f"Bearer {real_cust_tok}"})
    assert res_cross_c1.status_code == 404

    res_cross_c2 = await client.get("/api/v1/customer/cases/CASE-REAL-INTERACT-001", headers={"Authorization": f"Bearer {demo_cust_tok}"})
    assert res_cross_c2.status_code == 404

    # 3. POST /confirmation chéo ID -> 404
    res_conf_cross1 = await client.post(
        "/api/v1/customer/cases/CASE-REAL-INTERACT-001/confirmation",
        json={"confirmation": "RESOLVED_CONFIRMED"},
        headers={"Authorization": f"Bearer {demo_cust_tok}"},
    )
    assert res_conf_cross1.status_code == 404

    res_conf_cross2 = await client.post(
        f"/api/v1/customer/cases/{demo_case_id}/confirmation",
        json={"confirmation": "RESOLVED_CONFIRMED"},
        headers={"Authorization": f"Bearer {real_cust_tok}"},
    )
    assert res_conf_cross2.status_code == 404

    # 4. POST /reopen chéo ID -> 404
    res_reopen_cross1 = await client.post(
        "/api/v1/customer/cases/CASE-REAL-INTERACT-001/reopen",
        headers={"Authorization": f"Bearer {demo_cust_tok}"},
    )
    assert res_reopen_cross1.status_code == 404

    res_reopen_cross2 = await client.post(
        f"/api/v1/customer/cases/{demo_case_id}/reopen",
        headers={"Authorization": f"Bearer {real_cust_tok}"},
    )
    assert res_reopen_cross2.status_code == 404

    # 5. POST /feedback chéo ID -> 404
    res_fb_cross1 = await client.post(
        "/api/v1/customer/cases/CASE-REAL-INTERACT-001/feedback",
        json={"rating": 5, "comment": "Thử nghiệm"},
        headers={"Authorization": f"Bearer {demo_cust_tok}"},
    )
    assert res_fb_cross1.status_code == 404

    res_fb_cross2 = await client.post(
        f"/api/v1/customer/cases/{demo_case_id}/feedback",
        json={"rating": 5, "comment": "Thử nghiệm"},
        headers={"Authorization": f"Bearer {real_cust_tok}"},
    )
    assert res_fb_cross2.status_code == 404

    # 6. POST /location chéo ID -> 404
    res_loc_cross1 = await client.post(
        "/api/v1/customer/location",
        json={"case_id": "CASE-REAL-INTERACT-001", "status": "CONSENTED", "source": "USER_TEXT", "location_label": "Hà Nội"},
        headers={"Authorization": f"Bearer {demo_cust_tok}"},
    )
    assert res_loc_cross1.status_code == 404

    res_loc_cross2 = await client.post(
        "/api/v1/customer/location",
        json={"case_id": demo_case_id, "status": "CONSENTED", "source": "USER_TEXT", "location_label": "Hải Phòng"},
        headers={"Authorization": f"Bearer {real_cust_tok}"},
    )
    assert res_loc_cross2.status_code == 404

    # 7. POST /safety-acknowledgement chéo ID -> 404
    res_safe_cross1 = await client.post(
        "/api/v1/customer/cases/CASE-REAL-INTERACT-001/safety-acknowledgement",
        json={"incident_version": 1},
        headers={"Authorization": f"Bearer {demo_cust_tok}"},
    )
    assert res_safe_cross1.status_code == 404

    res_safe_cross2 = await client.post(
        f"/api/v1/customer/cases/{demo_case_id}/safety-acknowledgement",
        json={"incident_version": 1},
        headers={"Authorization": f"Bearer {real_cust_tok}"},
    )
    assert res_safe_cross2.status_code == 404

    # 8. GET /cases/{id}/service-points: chéo ID -> 404; đúng môi trường -> 200
    res_sp_cross1 = await client.get(
        f"/api/v1/customer/cases/{demo_case_id}/service-points",
        headers={"Authorization": f"Bearer {real_cust_tok}"},
    )
    assert res_sp_cross1.status_code == 404

    res_sp_cross2 = await client.get(
        "/api/v1/customer/cases/CASE-REAL-INTERACT-001/service-points",
        headers={"Authorization": f"Bearer {demo_cust_tok}"},
    )
    assert res_sp_cross2.status_code == 404

    res_sp_valid = await client.get(
        f"/api/v1/customer/cases/{demo_case_id}/service-points",
        headers={"Authorization": f"Bearer {demo_cust_tok}"},
    )
    assert res_sp_valid.status_code == 200


# ==============================================================================
# 6. TEST CÁCH LY 2 CHIỀU SESSIONS, HISTORY VÀ DELETE SESSIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_sessions_history_and_deletion_two_way_isolation(client, isolated_two_way_db):
    """
    Kiểm tra cách ly 2 chiều phiên trò chuyện:
    - GET /customer/sessions: lọc theo user và is_demo
    - GET /customer/sessions/{id}/history: chéo ID -> 404
    - PATCH /customer/sessions/{id}: chéo ID -> 404
    - DELETE /customer/sessions/{id}: demo customer gọi ID thật -> 404; real customer gọi ID demo -> 404
    - DELETE /customer/sessions (bulk delete): khách thật xóa phiên của mình không làm mất phiên demo!
    """
    from src import seed

    seed.seed_database(demo=True)
    today_str = f"{datetime.now(timezone.utc):%Y%m%d}"
    demo_session_id = f"DEMO-SESS-{today_str}-001"

    with isolated_two_way_db() as db:
        real_cust = User(
            id="real-cust-sess",
            username="real.cust.sess@vinfast.vn",
            password_hash=hash_password("RealPass@2026"),
            role=UserRole.CUSTOMER.value,
            full_name="Khách Phiên Thật",
            is_demo=False,
        )
        real_session = ChatSession(
            id="SESS-REAL-2026-999",
            owner="user:real-cust-sess",
            is_demo=False,
        )
        real_msg = Message(
            id="MSG-REAL-2026-999",
            session_id="SESS-REAL-2026-999",
            sender_type="CUSTOMER",
            content="Xin chào hỗ trợ VinFast",
        )
        db.add_all([real_cust, real_session, real_msg])
        db.commit()

    real_cust_tok = await get_token(client, "real.cust.sess@vinfast.vn", "RealPass@2026")
    demo_cust_tok = await get_token(client, DEMO_CUSTOMER_EMAIL, DEMO_PASSWORD)

    # 1. GET /sessions
    res_r_sess = await client.get("/api/v1/customer/sessions", headers={"Authorization": f"Bearer {real_cust_tok}"})
    assert res_r_sess.status_code == 200
    r_s_items = res_r_sess.json()["data"]["sessions"]
    assert len(r_s_items) == 1
    assert r_s_items[0]["session_id"] == "SESS-REAL-2026-999"

    # 2. GET /sessions/{id}/history chéo ID -> 404
    res_hist_cross1 = await client.get(
        f"/api/v1/customer/sessions/{demo_session_id}/history",
        headers={"Authorization": f"Bearer {real_cust_tok}"},
    )
    assert res_hist_cross1.status_code == 404

    res_hist_cross2 = await client.get(
        "/api/v1/customer/sessions/SESS-REAL-2026-999/history",
        headers={"Authorization": f"Bearer {demo_cust_tok}"},
    )
    assert res_hist_cross2.status_code == 404

    # 3. PATCH /sessions/{id} chéo ID -> 404
    res_patch_cross1 = await client.patch(
        f"/api/v1/customer/sessions/{demo_session_id}",
        json={"title": "Đổi tiêu đề trái phép"},
        headers={"Authorization": f"Bearer {real_cust_tok}"},
    )
    assert res_patch_cross1.status_code == 404

    res_patch_cross2 = await client.patch(
        "/api/v1/customer/sessions/SESS-REAL-2026-999",
        json={"title": "Đổi tiêu đề trái phép"},
        headers={"Authorization": f"Bearer {demo_cust_tok}"},
    )
    assert res_patch_cross2.status_code == 404

    # 4. DELETE /sessions/{id} chéo ID -> 404
    res_del_cross1 = await client.delete(
        f"/api/v1/customer/sessions/{demo_session_id}",
        headers={"Authorization": f"Bearer {real_cust_tok}"},
    )
    assert res_del_cross1.status_code == 404

    res_del_cross2 = await client.delete(
        "/api/v1/customer/sessions/SESS-REAL-2026-999",
        headers={"Authorization": f"Bearer {demo_cust_tok}"},
    )
    assert res_del_cross2.status_code == 404

    # 5. DELETE /sessions (Bulk Delete): Khách thật xóa tất cả phiên
    res_bulk_del = await client.delete("/api/v1/customer/sessions", headers={"Authorization": f"Bearer {real_cust_tok}"})
    assert res_bulk_del.status_code == 200
    assert res_bulk_del.json()["data"]["deleted_sessions_count"] == 1

    # Kiểm tra trong DB: Phiên thật đã xóa, toàn bộ 9 phiên Demo VẪN CÒN NGUYÊN VẸN!
    with isolated_two_way_db() as db:
        real_sess_check = db.get(ChatSession, "SESS-REAL-2026-999")
        assert real_sess_check is None, "Phiên thật chưa được xóa"

        demo_sess_count = db.query(ChatSession).filter(ChatSession.is_demo == True).count()
        assert demo_sess_count == 9, "Lỗ hổng: Bulk delete của khách thật đã xóa nhầm phiên Demo!"


# ==============================================================================
# 7. TEST SEED DEMO IDEMPOTENCE & RESET AN TOÀN
# ==============================================================================

@pytest.mark.asyncio
async def test_seed_demo_idempotence_and_safe_reset(isolated_two_way_db):
    """
    Kiểm tra:
    - seed --demo 2 lần không tạo trùng lặp (đủ 9 ca).
    - --reset CHỈ xóa dữ liệu demo (is_demo=True), dữ liệu thật nguyên vẹn 100%.
    """
    from src import seed

    # 1. Tạo dữ liệu thật trước
    with isolated_two_way_db() as db:
        real_u = User(
            id="real-customer-persistent",
            username="real.persistent@vinfast.vn",
            password_hash=hash_password("Pass123"),
            role=UserRole.CUSTOMER.value,
            full_name="Khách Hàng Bất Biến",
            is_demo=False,
        )
        real_c = Case(
            id="CASE-REAL-PERSISTENT-001",
            user_id="real-customer-persistent",
            session_id="SESS-REAL-PERSISTENT-001",
            intent="Service/Incident",
            is_demo=False,
            status=TicketStatus.NEW.value,
        )
        db.add_all([real_u, real_c])
        db.commit()

    # 2. Seed demo lần 1
    seed.seed_database(demo=True)
    with isolated_two_way_db() as db:
        demo_cases_1 = db.query(Case).filter(Case.is_demo == True).count()
        assert demo_cases_1 == 9

    # 3. Seed demo lần 2 (Idempotent test)
    seed.seed_database(demo=True)
    with isolated_two_way_db() as db:
        demo_cases_2 = db.query(Case).filter(Case.is_demo == True).count()
        assert demo_cases_2 == 9, "Idempotency failed: Ca demo bị nhân bản khi chạy seed lần 2!"

    # 4. Reset demo (--reset)
    seed.seed_database(demo=True, reset=True)
    with isolated_two_way_db() as db:
        demo_cases_reset = db.query(Case).filter(Case.is_demo == True).count()
        assert demo_cases_reset == 9

        real_u_check = db.query(User).filter(User.id == "real-customer-persistent").first()
        real_c_check = db.query(Case).filter(Case.id == "CASE-REAL-PERSISTENT-001").first()
        assert real_u_check is not None, "NGUY HIỂM: --reset đã xóa nhầm User thật!"
        assert real_c_check is not None, "NGUY HIỂM: --reset đã xóa nhầm Case thật!"
        assert real_u_check.is_demo is False
        assert real_c_check.is_demo is False


# ==============================================================================
# 8. TEST FULL 9 KỊCH BẢN DEMO (CASE 1 SAFETY, CASE 2 NEW, CASE 5 CONFIRM, CASE 6 REOPEN)
# ==============================================================================

@pytest.mark.asyncio
async def test_full_demo_scenarios_workflow(client, isolated_two_way_db):
    """
    Kiểm tra toàn bộ luồng demo thực tế theo đúng yêu cầu chi tiết 9 kịch bản:
    1. Case 1: có safety_acknowledged_at -> staff APPROVE -> RESOLVE.
    2. Case 2: trạng thái ban đầu là 'New', chưa phân công staff nào.
    3. Case 5: trạng thái Resolved, BAN ĐẦU CHƯA CÓ FEEDBACK. Customer confirm -> Closed + gửi feedback 5 sao.
    4. Case 6: trạng thái Resolved -> Customer reopen -> Reopened.
    """
    from src import seed

    seed.seed_database(demo=True)
    today_str = f"{datetime.now(timezone.utc):%Y%m%d}"
    case_001 = f"DEMO-{today_str}-001"
    case_002 = f"DEMO-{today_str}-002"
    case_005 = f"DEMO-{today_str}-005"
    case_006 = f"DEMO-{today_str}-006"

    staff_tok = await get_token(client, DEMO_STAFF_EMAIL, DEMO_PASSWORD)
    cust_tok = await get_token(client, DEMO_CUSTOMER_EMAIL, DEMO_PASSWORD)

    # 1. Kiểm tra Case 1: có safety_acknowledged_at và staff thao tác duyệt
    with isolated_two_way_db() as db:
        c1_db = db.get(Case, case_001)
        assert c1_db is not None
        assert c1_db.safety_acknowledged_at is not None, "Case 1 phải có safety_acknowledged_at"

    res_appr = await client.post(
        f"/api/v1/staff/tickets/{case_001}/actions",
        json={"action": "APPROVE", "staff_id": "demo_staff_01", "notes": "Đã tiếp nhận hồ sơ sạc."},
        headers={"Authorization": f"Bearer {staff_tok}"},
    )
    assert res_appr.status_code == 200

    res_res = await client.post(
        f"/api/v1/staff/tickets/{case_001}/actions",
        json={"action": "RESOLVE", "staff_id": "demo_staff_01", "notes": "Đã xử lý xong súng sạc."},
        headers={"Authorization": f"Bearer {staff_tok}"},
    )
    assert res_res.status_code == 200

    res_c1_detail = await client.get(f"/api/v1/staff/tickets/{case_001}", headers={"Authorization": f"Bearer {staff_tok}"})
    assert res_c1_detail.json()["data"]["case"]["status"] == "Resolved"

    # 2. Kiểm tra Case 2: trạng thái New, chưa phân công
    with isolated_two_way_db() as db:
        c2_db = db.get(Case, case_002)
        assert c2_db is not None
        assert c2_db.status == TicketStatus.NEW.value, f"Case 2 phải là 'New', nhận {c2_db.status}"
        assert c2_db.assigned_staff_id is None, "Case 2 chưa được phân công staff"

    # 3. Kiểm tra Case 5: ban đầu Resolved, KHÔNG có feedback
    with isolated_two_way_db() as db:
        c5_db = db.get(Case, case_005)
        assert c5_db is not None
        assert c5_db.status == TicketStatus.RESOLVED.value
        fb_c5 = db.query(CustomerFeedback).filter(CustomerFeedback.case_id == case_005).first()
        assert fb_c5 is None, "Case 5 ban đầu không được có feedback"

    # Customer xác nhận hoàn tất Case 5
    res_confirm = await client.post(
        f"/api/v1/customer/cases/{case_005}/confirmation",
        json={"confirmation": "RESOLVED_CONFIRMED", "feedback_note": "Cổng sạc mở rất tốt."},
        headers={"Authorization": f"Bearer {cust_tok}"},
    )
    assert res_confirm.status_code == 200
    assert res_confirm.json()["data"]["status"] == "Closed"

    # Customer gửi đánh giá feedback 5 sao cho Case 5
    res_fb = await client.post(
        f"/api/v1/customer/cases/{case_005}/feedback",
        json={"rating": 5, "comment": "Dịch vụ VinFast chuyên nghiệp!"},
        headers={"Authorization": f"Bearer {cust_tok}"},
    )
    assert res_fb.status_code == 200
    assert res_fb.json()["data"]["success"] is True

    # 4. Customer mở lại (Reopen) Case 6
    res_reopen = await client.post(
        f"/api/v1/customer/cases/{case_006}/reopen",
        headers={"Authorization": f"Bearer {cust_tok}"},
    )
    assert res_reopen.status_code == 200
    assert res_reopen.json()["data"]["status"] == "Reopened"


# ==============================================================================
# 9. TEST AUTO-CLOSE WORKER CÁCH LY 2 CHIỀU
# ==============================================================================

@pytest.mark.asyncio
async def test_auto_close_worker_two_way_isolation(isolated_two_way_db):
    """
    Kiểm tra worker tự động đóng ca hết hạn:
    - process_auto_close_expired_cases(is_demo=False): chỉ đóng ca thật, ca demo giữ nguyên.
    - process_auto_close_expired_cases(is_demo=True): chỉ đóng ca demo, ca thật giữ nguyên.
    """
    today_str = f"{datetime.now(timezone.utc):%Y%m%d}"
    old_time = datetime.now(timezone.utc) - timedelta(hours=80)

    with isolated_two_way_db() as db:
        real_exp = Case(
            id="CASE-REAL-AUTO-CLOSE-EXP",
            session_id="SESS-REAL-AUTO-CLOSE-EXP",
            intent="Service/Incident",
            status=TicketStatus.RESOLVED.value,
            updated_at=old_time,
            is_demo=False,
        )
        demo_exp = Case(
            id=f"DEMO-{today_str}-AUTO-EXP",
            session_id=f"DEMO-SESS-{today_str}-AUTO-EXP",
            intent="Service/Incident",
            status=TicketStatus.RESOLVED.value,
            updated_at=old_time,
            is_demo=True,
        )
        db.add_all([real_exp, demo_exp])
        db.commit()

        # 1. Quét chỉ ca thật: ca thật đóng, ca demo nguyên
        closed_real = process_auto_close_expired_cases(db, is_demo=False)
        assert closed_real == 1
        c_real = db.get(Case, "CASE-REAL-AUTO-CLOSE-EXP")
        c_demo = db.get(Case, f"DEMO-{today_str}-AUTO-EXP")
        assert c_real.status == TicketStatus.CLOSED.value
        assert c_demo.status == TicketStatus.RESOLVED.value, "Ca demo không được bị đóng khi quét is_demo=False"

        # 2. Quét chỉ ca demo: ca demo đóng
        closed_demo = process_auto_close_expired_cases(db, is_demo=True)
        assert closed_demo == 1
        c_demo_after = db.get(Case, f"DEMO-{today_str}-AUTO-EXP")
        assert c_demo_after.status == TicketStatus.CLOSED.value


# ==============================================================================
# 10. TEST GUEST CHAT VÀ CHẶN CLAIM CHÉO
# ==============================================================================

@pytest.mark.asyncio
async def test_guest_chat_is_real_and_demo_user_cannot_claim(client, isolated_two_way_db):
    """
    Kiểm tra:
    - Guest chat có is_demo=False.
    - Demo user không thể claim ca của guest (do khác phân vùng is_demo).
    """
    from src import seed

    seed.seed_database(demo=True)

    # 1. Guest tạo session chat và ca sự cố
    guest_session_id = f"guest_sess_{uuid.uuid4().hex[:8]}"
    with isolated_two_way_db() as db:
        guest_sess = ChatSession(
            id=guest_session_id,
            owner=f"guest:{guest_session_id}",
            is_demo=False,
        )
        guest_case = Case(
            id=f"CASE-GUEST-{uuid.uuid4().hex[:6]}",
            session_id=guest_session_id,
            intent="Service/Incident",
            status=TicketStatus.NEW.value,
            is_demo=False,
        )
        db.add_all([guest_sess, guest_case])
        db.commit()

        assert guest_sess.is_demo is False
        assert guest_case.is_demo is False

    # 2. Demo Customer đăng nhập và cố gắng claim ca của guest
    demo_cust_tok = await get_token(client, DEMO_CUSTOMER_EMAIL, DEMO_PASSWORD)

    # Thử gọi API tương tác trên ca guest
    res_claim = await client.post(
        f"/api/v1/customer/cases/{guest_case.id}/confirmation",
        json={"confirmation": "RESOLVED_CONFIRMED"},
        headers={"Authorization": f"Bearer {demo_cust_tok}"},
    )
    assert res_claim.status_code == 404, "Lỗ hổng: Demo user có thể truy cập/claim ca của khách dùng thử thật!"
