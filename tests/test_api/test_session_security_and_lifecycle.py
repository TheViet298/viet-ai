import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, get_db
from src.main import app
from src.models.db_models import Case, ChatRequestRecord, ChatSession, Message, User
from src.services.auth import create_token, hash_password


@pytest.fixture
def sec_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'sec_test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user_x = User(
            id="user-x-id",
            username="user_x@vinfast.vn",
            password_hash=hash_password("Pass1234"),
            role="CUSTOMER",
        )
        user_y = User(
            id="user-y-id",
            username="user_y@vinfast.vn",
            password_hash=hash_password("Pass1234"),
            role="CUSTOMER",
        )
        db.add_all([user_x, user_y])
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        yield db
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.asyncio
async def test_session_takeover_prevention(client, sec_db):
    """
    Kịch bản then chốt: User X đăng nhập, gửi raw_claim = session_id của user Y.
    Kiểm tra session của Y TUYỆT ĐỐI không bị đổi chủ sang User X.
    """
    victim_session_id = f"sess_vf_{uuid.uuid4()}"
    y_session = ChatSession(id=victim_session_id, owner="user:user-y-id", memory_states={})
    sec_db.add(y_session)
    sec_db.commit()

    # User X đăng nhập và cố tình gửi raw_claim = victim_session_id
    res = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "user_x@vinfast.vn",
            "password": "Pass1234",
            "guest_session_id": victim_session_id,
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["claimed_sessions"] == 0

    # Kiểm tra trong DB: session của Y vẫn thuộc về Y
    sec_db.expire_all()
    reloaded_session = sec_db.get(ChatSession, victim_session_id)
    assert reloaded_session.owner == "user:user-y-id"


@pytest.mark.asyncio
async def test_guest_isolation_and_claim(client, sec_db):
    """
    Guest A và Guest B cùng chat. A đăng nhập -> chỉ claim session của A, session của B giữ nguyên.
    """
    guest_a_id = f"sess_vf_{uuid.uuid4()}"
    guest_b_id = f"sess_vf_{uuid.uuid4()}"

    session_a = ChatSession(id=guest_a_id, owner=f"guest:{guest_a_id}", memory_states={})
    session_b = ChatSession(id=guest_b_id, owner=f"guest:{guest_b_id}", memory_states={})
    case_a = Case(id="CASE-A", session_id=guest_a_id, user_id=None, status="PENDING", intent="CONSULTATION")
    case_b = Case(id="CASE-B", session_id=guest_b_id, user_id=None, status="PENDING", intent="CONSULTATION")
    msg_a = Message(id="MSG-A", session_id=guest_a_id, sender_type="CUSTOMER", content="Chào A")
    msg_b = Message(id="MSG-B", session_id=guest_b_id, sender_type="CUSTOMER", content="Chào B")

    sec_db.add_all([session_a, session_b, case_a, case_b, msg_a, msg_b])
    sec_db.commit()

    # Guest A đăng ký tài khoản mới kèm guest_session_id của mình
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "customer_a@vinfast.vn",
            "password": "Pass1234",
            "guest_session_id": guest_a_id,
        },
    )
    assert res.status_code == 200
    res_data = res.json()["data"]
    user_a_id = res_data["user"]["id"]
    assert res_data["claimed_sessions"] == 1

    # Kiểm tra DB
    sec_db.expire_all()
    reloaded_a = sec_db.get(ChatSession, guest_a_id)
    reloaded_b = sec_db.get(ChatSession, guest_b_id)
    reloaded_case_a = sec_db.get(Case, "CASE-A")
    reloaded_case_b = sec_db.get(Case, "CASE-B")

    assert reloaded_a.owner == f"user:{user_a_id}"
    assert reloaded_b.owner == f"guest:{guest_b_id}"
    assert reloaded_case_a.user_id == user_a_id
    assert reloaded_case_b.user_id is None


@pytest.mark.asyncio
async def test_double_claim_idempotent(client, sec_db):
    """
    Mở hai tab cùng đăng nhập, claim hai lần -> không nhân đôi, không lỗi.
    """
    guest_id = f"sess_vf_{uuid.uuid4()}"
    session = ChatSession(id=guest_id, owner=f"guest:{guest_id}", memory_states={})
    sec_db.add(session)
    sec_db.commit()

    # Lần 1: Claim thành công
    res1 = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "user_x@vinfast.vn",
            "password": "Pass1234",
            "guest_session_id": guest_id,
        },
    )
    assert res1.status_code == 200
    assert res1.json()["data"]["claimed_sessions"] == 1

    # Lần 2 (tab thứ 2 gọi lại cùng guest_id sau khi đã claim): không lỗi, trả về 0 claimed
    res2 = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "user_x@vinfast.vn",
            "password": "Pass1234",
            "guest_session_id": guest_id,
        },
    )
    assert res2.status_code == 200
    assert res2.json()["data"]["claimed_sessions"] == 0


@pytest.mark.asyncio
async def test_title_cache_and_manual_rename_lifecycle(client, sec_db):
    """
    Kiểm tra chu trình:
    1. Chat 'xin chào' -> Title không bị đóng băng vội vàng thành 'Cuộc trò chuyện mới'.
    2. Chat 'xe vf5 giá bao nhiêu' -> Title tự động lấy theo câu hỏi thực sự.
    3. Đổi tên thủ công thành 'Tư vấn VF5' -> cờ title_edited được bật, lưu đúng vào memory_states.
    4. Reload/List lại -> Tiêu đề thủ công giữ nguyên, không bị auto-title ghi đè.
    """
    guest_id = f"sess_vf_{uuid.uuid4()}"
    token = create_token(user_id="user-x-id", role="CUSTOMER")
    headers = {"Authorization": f"Bearer {token}"}

    # Tạo session cho user-x
    session = ChatSession(id=guest_id, owner="user:user-x-id", memory_states={})
    msg1 = Message(id="M1", session_id=guest_id, sender_type="CUSTOMER", content="Xin chào trợ lý")
    sec_db.add_all([session, msg1])
    sec_db.commit()

    # Bước 1: List sessions khi chỉ có câu chào
    res_list1 = await client.get("/api/v1/customer/sessions", headers=headers)
    assert res_list1.status_code == 200
    sessions_data1 = res_list1.json()["data"]["sessions"]
    assert len(sessions_data1) == 1
    # Lúc này title hiển thị là Cuộc trò chuyện mới
    assert sessions_data1[0]["title"] == "Cuộc trò chuyện mới"

    # Kiểm tra trong DB: không bị đóng băng title vào memory_states
    sec_db.expire_all()
    s_db = sec_db.get(ChatSession, guest_id)
    assert "title" not in (s_db.memory_states or {})

    # Bước 2: Thêm tin nhắn có nội dung thực "xe vf5 giá bao nhiêu"
    msg2 = Message(id="M2", session_id=guest_id, sender_type="CUSTOMER", content="Xe VF5 giá bao nhiêu?")
    sec_db.add(msg2)
    sec_db.commit()

    # List lại: Tiêu đề tự động tính lại theo tin nhắn thực
    res_list2 = await client.get("/api/v1/customer/sessions", headers=headers)
    assert res_list2.status_code == 200
    sessions_data2 = res_list2.json()["data"]["sessions"]
    assert "VF5" in sessions_data2[0]["title"]

    # Bước 3: Đổi tên thủ công
    patch_res = await client.patch(
        f"/api/v1/customer/sessions/{guest_id}",
        json={"title": "Tư vấn VF5 bản Plus"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["title"] == "Tư vấn VF5 bản Plus"

    # Bước 4: F5 / List lại -> Tên thủ công còn nguyên vẹn
    sec_db.expire_all()
    s_reloaded = sec_db.get(ChatSession, guest_id)
    assert s_reloaded.memory_states.get("title") == "Tư vấn VF5 bản Plus"
    assert s_reloaded.memory_states.get("title_edited") is True

    res_list3 = await client.get("/api/v1/customer/sessions", headers=headers)
    assert res_list3.status_code == 200
    assert res_list3.json()["data"]["sessions"][0]["title"] == "Tư vấn VF5 bản Plus"


@pytest.mark.asyncio
async def test_session_deletion_removes_messages_cleanly(client, sec_db):
    """
    Xóa session: Xác nhận Message và ChatRequestRecord bị xóa triệt để, không để dữ liệu mồ côi.
    """
    session_id = f"sess_vf_{uuid.uuid4()}"
    token = create_token(user_id="user-x-id", role="CUSTOMER")
    headers = {"Authorization": f"Bearer {token}"}

    s = ChatSession(id=session_id, owner="user:user-x-id", memory_states={})
    m = Message(id="M-DEL", session_id=session_id, sender_type="CUSTOMER", content="Nội dung cần xóa")
    r = ChatRequestRecord(id="REQ-DEL", owner="user:user-x-id", session_id=session_id, request_hash="h", response={})
    sec_db.add_all([s, m, r])
    sec_db.commit()

    del_res = await client.delete(f"/api/v1/customer/sessions/{session_id}", headers=headers)
    assert del_res.status_code == 200

    sec_db.expire_all()
    assert sec_db.get(ChatSession, session_id) is None
    assert sec_db.query(Message).filter_by(session_id=session_id).first() is None
    assert sec_db.query(ChatRequestRecord).filter_by(session_id=session_id).first() is None
