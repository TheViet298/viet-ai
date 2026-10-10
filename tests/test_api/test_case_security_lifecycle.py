import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db import Base, get_db
from src.main import app
from src.models.db_models import (
    Case,
    CaseBrief,
    CustomerFeedback,
    Intent,
    Priority,
    StaffAuditLog,
    TicketStatus,
    User,
    UserRole,
    utcnow,
)
from src.services.auth import create_token, hash_password
from src.services.case_lifecycle import process_auto_close_expired_cases


@pytest.fixture
def test_db_session(tmp_path):
    """Tạo database SQLite độc lập trong thư mục tạm cho mỗi test run."""
    engine = create_engine(f"sqlite:///{tmp_path / 'security_test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        app.dependency_overrides[get_db] = lambda: db
        yield db
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.asyncio
async def test_cross_user_forbidden_access(client, test_db_session):
    """1. User B gọi confirmation, feedback, reopen trên case của User A -> mong đợi 403 Forbidden."""
    db = test_db_session
    user_a = User(id="user-a-uuid", username="user_a", password_hash="h1", role=UserRole.CUSTOMER.value)
    user_b = User(id="user-b-uuid", username="user_b", password_hash="h2", role=UserRole.CUSTOMER.value)
    case_a = Case(
        id="CASE-USER-A-01",
        user_id="user-a-uuid",
        session_id="session-user-a-token-1234",
        vehicle_model="VF8",
        intent=Intent.SERVICE_INCIDENT.value,
        priority=Priority.MEDIUM.value,
        status=TicketStatus.RESOLVED.value,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add_all([user_a, user_b, case_a])
    db.commit()

    token_b = create_token(user_id=user_b.id, role=user_b.role)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # B gọi confirmation trên case của A -> 403
    res_confirm = await client.post(
        f"/api/v1/customer/cases/{case_a.id}/confirmation",
        headers=headers_b,
        json={"confirmation": "RESOLVED_CONFIRMED"},
    )
    assert res_confirm.status_code == 403

    # B gọi feedback trên case của A -> 403
    res_feedback = await client.post(
        f"/api/v1/customer/cases/{case_a.id}/feedback",
        headers=headers_b,
        json={"rating": 5, "comment": "Tấn công IDOR"},
    )
    assert res_feedback.status_code == 403

    # B gọi action REOPEN trên case của A -> 403
    res_reopen = await client.post(
        f"/api/v1/customer/cases/{case_a.id}/actions",
        headers=headers_b,
        json={"action": "REOPEN", "reason": "Tấn công IDOR"},
    )
    assert res_reopen.status_code == 403


@pytest.mark.asyncio
async def test_claim_case_invalid_entropy_or_nonexistent(client, test_db_session):
    """2. Claim với session_id quá ngắn, tuần tự/lặp ký tự, hoặc không tồn tại -> Không claim được."""
    db = test_db_session
    user = User(
        id="user-claim-01",
        username="claim_tester",
        password_hash=hash_password("password123"),
        role=UserRole.CUSTOMER.value,
    )
    # Case hợp lệ của guest
    valid_guest_session = "valid_guest_session_secret_token_12345"
    case_guest = Case(
        id="CASE-GUEST-01",
        user_id=None,
        session_id=valid_guest_session,
        vehicle_model="VF5",
        intent=Intent.SERVICE_INCIDENT.value,
        priority=Priority.MEDIUM.value,
        status=TicketStatus.NEW.value,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add_all([user, case_guest])
    db.commit()

    # Case A: session_id quá ngắn (dưới 16 ký tự)
    await client.post(
        "/api/v1/auth/login",
        json={"username": "claim_tester", "password": "password123", "guest_session_id": "short_sess"},
    )
    db.refresh(case_guest)
    assert case_guest.user_id is None

    # Case B: session_id lặp ký tự thiếu entropy (aaaaaaaaaaaaaaaa)
    await client.post(
        "/api/v1/auth/login",
        json={"username": "claim_tester", "password": "password123", "guest_session_id": "aaaaaaaaaaaaaaaa"},
    )
    db.refresh(case_guest)
    assert case_guest.user_id is None

    # Case C: session_id ngẫu nhiên nhưng không có trong DB
    await client.post(
        "/api/v1/auth/login",
        json={"username": "claim_tester", "password": "password123", "guest_session_id": "random_fake_token_not_exist_999"},
    )
    db.refresh(case_guest)
    assert case_guest.user_id is None


@pytest.mark.asyncio
async def test_claim_case_race_condition(client, test_db_session):
    """3. Hai request claim đồng thời với cùng 1 session_id -> Chỉ 1 request claim thành công."""
    db = test_db_session
    u1 = User(id="u1-uuid", username="user1", password_hash=hash_password("pass12345"), role=UserRole.CUSTOMER.value)
    u2 = User(id="u2-uuid", username="user2", password_hash=hash_password("pass12345"), role=UserRole.CUSTOMER.value)
    guest_session = "race_condition_guest_token_12345678"
    case = Case(
        id="CASE-RACE-01",
        user_id=None,
        session_id=guest_session,
        vehicle_model="VF8",
        intent=Intent.CHARGING_BATTERY.value,
        priority=Priority.HIGH.value,
        status=TicketStatus.NEW.value,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add_all([u1, u2, case])
    db.commit()

    # User 1 đăng nhập kèm guest session -> claim thành công
    res1 = await client.post(
        "/api/v1/auth/login",
        json={"username": "user1", "password": "pass12345", "guest_session_id": guest_session},
    )
    assert res1.status_code == 200

    db.refresh(case)
    assert case.user_id == "u1-uuid"

    # User 2 sau đó (hoặc đồng thời) gửi cùng guest_session_id -> không thể chiếm đoạt case đã có chủ
    res2 = await client.post(
        "/api/v1/auth/login",
        json={"username": "user2", "password": "pass12345", "guest_session_id": guest_session},
    )
    assert res2.status_code == 200

    db.refresh(case)
    assert case.user_id == "u1-uuid"  # Vẫn nguyên vẹn là User 1, User 2 không cướp được


@pytest.mark.asyncio
async def test_register_ignores_mock_customer_id(client, test_db_session):
    """4. Đăng ký tài khoản thường kèm mock_customer_id trong body -> Bị bỏ qua, user có mock_customer_id = None."""
    db = test_db_session
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "new_customer_real",
            "password": "secure_password_123",
            "full_name": "Khách Hàng Mới",
            "mock_customer_id": "CUST_MOCK_01",  # Kẻ tấn công cố tình truyền ID seed
        },
    )
    assert res.status_code == 200
    user_db = db.query(User).filter(User.username == "new_customer_real").first()
    assert user_db is not None
    assert user_db.mock_customer_id is None  # Đảm bảo không bị gán mock ID


@pytest.mark.asyncio
async def test_no_mock_customer_id_fallback_allowed(client, test_db_session):
    """5. Hoàn toàn không còn nhánh fallback: dù mock_customer_id trùng khớp vẫn bị chặn 403 Forbidden."""
    db = test_db_session

    user = User(
        id="user-demo-match",
        username="user_demo",
        password_hash="pass",
        role=UserRole.CUSTOMER.value,
        mock_customer_id="CUST_MOCK_SEED",
    )
    case = Case(
        id="CASE-SEED-01",
        user_id="another-user-id",  # Case thuộc user khác
        session_id="seed-session-123456",
        mock_customer_id="CUST_MOCK_SEED",
        vehicle_model="VF9",
        intent=Intent.SERVICE_INCIDENT.value,
        priority=Priority.MEDIUM.value,
        status=TicketStatus.RESOLVED.value,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add_all([user, case])
    db.commit()

    token = create_token(user_id=user.id, role=user.role)
    headers = {"Authorization": f"Bearer {token}"}

    # Bị chặn 403 tuyệt đối vì quyền sở hữu chỉ chấp nhận case.user_id == user.id
    res = await client.post(
        f"/api/v1/customer/cases/{case.id}/confirmation",
        headers=headers,
        json={"confirmation": "RESOLVED_CONFIRMED"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_concurrent_feedback_upsert_unique(client, test_db_session):
    """6. Hai request feedback đồng thời/liên tiếp -> Chỉ 1 bản ghi duy nhất trong DB (Upsert idempotent)."""
    db = test_db_session
    user = User(id="user-fb-1", username="user_fb", password_hash="pass", role=UserRole.CUSTOMER.value)
    case = Case(
        id="CASE-FB-01",
        user_id="user-fb-1",
        session_id="session-fb-123456",
        vehicle_model="VF8",
        intent=Intent.SERVICE_INCIDENT.value,
        priority=Priority.MEDIUM.value,
        status=TicketStatus.RESOLVED.value,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add_all([user, case])
    db.commit()

    token = create_token(user_id=user.id, role=user.role)
    headers = {"Authorization": f"Bearer {token}"}

    # Gửi feedback lần 1 (1 sao, kèm lý do tag)
    res1 = await client.post(
        f"/api/v1/customer/cases/{case.id}/feedback",
        headers=headers,
        json={"rating": 1, "comment": "Chờ quá lâu", "reason_tags": ["Chờ hỗ trợ lâu"]},
    )
    assert res1.status_code == 200

    # Gửi feedback lần 2 (khách sửa thành 5 sao)
    res2 = await client.post(
        f"/api/v1/customer/cases/{case.id}/feedback",
        headers=headers,
        json={"rating": 5, "comment": "Đã hỗ trợ xong, cảm ơn", "reason_tags": []},
    )
    assert res2.status_code == 200

    # Kiểm tra DB: Phải có ĐÚNG 1 bản ghi duy nhất, rating đã update thành 5
    feedbacks = db.query(CustomerFeedback).filter(CustomerFeedback.case_id == case.id).all()
    assert len(feedbacks) == 1
    assert feedbacks[0].rating == 5
    assert feedbacks[0].comment == "Đã hỗ trợ xong, cảm ơn"


@pytest.mark.asyncio
async def test_feedback_rejected_when_not_resolved_or_closed(client, test_db_session):
    """7. Gửi feedback khi case ở trạng thái New hoặc In Progress -> Bị từ chối với 409 Conflict."""
    db = test_db_session
    user = User(id="user-fb-prog", username="user_prog", password_hash="pass", role=UserRole.CUSTOMER.value)
    case = Case(
        id="CASE-PROG-01",
        user_id="user-fb-prog",
        session_id="session-prog-123456",
        vehicle_model="VF5",
        intent=Intent.SERVICE_INCIDENT.value,
        priority=Priority.MEDIUM.value,
        status=TicketStatus.IN_PROGRESS.value,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add_all([user, case])
    db.commit()

    token = create_token(user_id=user.id, role=user.role)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        f"/api/v1/customer/cases/{case.id}/feedback",
        headers=headers,
        json={"rating": 5, "comment": "Tốt"},
    )
    assert res.status_code == 409
    assert "In Progress" in res.text


@pytest.mark.asyncio
async def test_auto_close_idempotent(client, test_db_session):
    """8. Chạy auto-close hai lần liên tiếp -> Chỉ đóng 1 lần và sinh đúng 1 audit log."""
    db = test_db_session
    old_time = utcnow() - timedelta(hours=75)
    case = Case(
        id="CASE-AUTO-01",
        user_id="user-auto-1",
        session_id="session-auto-123456",
        vehicle_model="VF8",
        intent=Intent.SERVICE_INCIDENT.value,
        priority=Priority.MEDIUM.value,
        status=TicketStatus.RESOLVED.value,
        created_at=old_time,
        updated_at=old_time,
    )
    db.add(case)
    db.commit()

    # Lần 1: Quét quá hạn 72h -> Đóng ca thành công
    closed_1 = process_auto_close_expired_cases(db, expired_hours=72)
    assert closed_1 == 1

    db.refresh(case)
    assert case.status == TicketStatus.CLOSED.value

    # Lần 2: Quét lại ngay lập tức -> Không đóng thêm, trả về 0
    closed_2 = process_auto_close_expired_cases(db, expired_hours=72)
    assert closed_2 == 0

    # Kiểm tra audit log: Chỉ có đúng 1 bản ghi auto close
    audit_logs = db.query(StaffAuditLog).filter(
        StaffAuditLog.case_id == case.id,
        StaffAuditLog.staff_id == "SYSTEM_AUTO_CLOSE",
    ).all()
    assert len(audit_logs) == 1


@pytest.mark.asyncio
async def test_reopen_auto_closed_case_step_up_priority(client, test_db_session):
    """9. Reopen case đã auto-close -> Tăng đúng 1 bậc ưu tiên (MEDIUM -> HIGH), trạng thái Reopened, reset timestamp."""
    db = test_db_session
    user = User(id="user-reopen-1", username="user_reopen", password_hash="pass", role=UserRole.CUSTOMER.value)
    brief = CaseBrief(
        id=str(uuid.uuid4()),
        case_id="CASE-REOPEN-01",
        summary="Xe sạc không vào điện",
        captured_fields={},
        suggested_action="Kiểm tra trụ sạc",
    )
    case = Case(
        id="CASE-REOPEN-01",
        user_id="user-reopen-1",
        session_id="session-reopen-123456",
        vehicle_model="VF8",
        intent=Intent.CHARGING_BATTERY.value,
        priority=Priority.MEDIUM.value,
        status=TicketStatus.CLOSED.value,
        created_at=utcnow() - timedelta(days=4),
        updated_at=utcnow() - timedelta(days=1),
    )
    case.brief = brief
    db.add_all([user, case])
    db.commit()

    token = create_token(user_id=user.id, role=user.role)
    headers = {"Authorization": f"Bearer {token}"}

    reopen_reason = "Vẫn còn hiện tượng ngắt sạc khi pin đạt 80%"
    res = await client.post(
        f"/api/v1/customer/cases/{case.id}/actions",
        headers=headers,
        json={"action": "REOPEN", "reason": reopen_reason},
    )
    assert res.status_code == 200

    db.refresh(case)
    assert case.status == TicketStatus.REOPENED.value
    # Ưu tiên nâng 1 bậc từ MEDIUM -> HIGH
    assert case.priority == Priority.HIGH.value
    # Lưu đúng reopen_reason
    assert case.brief.captured_fields.get("reopen_reason") == reopen_reason
    # Timestamp cập nhật mới gần đây (trong vòng 5 giây)
    updated_at_utc = case.updated_at.replace(tzinfo=UTC) if case.updated_at.tzinfo is None else case.updated_at
    assert (utcnow() - updated_at_utc).total_seconds() < 5


@pytest.mark.asyncio
async def test_mock_customer_id_does_not_grant_access(client, test_db_session):
    """10. Nhánh mock_customer_id đã bị xóa bỏ hoàn toàn: không còn fallback, trả về 403 Forbidden."""
    db = test_db_session
    user_owner = User(
        id="owner-uuid-1",
        username="owner_user",
        password_hash="pass",
        role=UserRole.CUSTOMER.value,
        mock_customer_id="CUST_MOCK_01",
    )
    user_attacker = User(
        id="attacker-uuid-2",
        username="attacker_user",
        password_hash="pass",
        role=UserRole.CUSTOMER.value,
        mock_customer_id="CUST_MOCK_01",
    )
    case = Case(
        id="CASE-MOCK-TEST-01",
        user_id="owner-uuid-1",
        session_id="session-mock-123456",
        mock_customer_id="CUST_MOCK_01",
        vehicle_model="VF8",
        intent=Intent.CHARGING_BATTERY.value,
        priority=Priority.MEDIUM.value,
        status=TicketStatus.RESOLVED.value,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add_all([user_owner, user_attacker, case])
    db.commit()

    token_attacker = create_token(user_id=user_attacker.id, role=user_attacker.role)
    headers = {"Authorization": f"Bearer {token_attacker}"}

    # 1. Attacker gửi xác nhận hoàn tất -> 403 Forbidden
    res = await client.post(
        f"/api/v1/customer/cases/{case.id}/actions",
        headers=headers,
        json={"action": "CONFIRM_RESOLUTION"},
    )
    assert res.status_code == 403

    # 2. Attacker gửi đánh giá CSAT -> 403 Forbidden
    res_fb = await client.post(
        f"/api/v1/customer/cases/{case.id}/feedback",
        headers=headers,
        json={"rating": 5, "comment": "Tốt"},
    )
    assert res_fb.status_code == 403

    # 3. Attacker truy vấn trạng thái ca -> 403 Forbidden
    res_status = await client.get(
        f"/api/v1/customer/cases/{case.id}/status",
        headers=headers,
    )
    assert res_status.status_code == 403
