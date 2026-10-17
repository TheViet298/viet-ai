import os
import sys
import uuid
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.db import SessionLocal
from src.models.db_models import User, ChatSession, Message, ChatRequestRecord, Case
from src.services.auth import create_token, hash_password

client = TestClient(app)


def test_customer_delete_single_and_all():
    """Kiểm tra người dùng đã đăng nhập xóa 1 session và xóa tất cả sessions."""
    db = SessionLocal()
    user = User(id=uuid.uuid4().hex, username='delete-fixture-' + uuid.uuid4().hex,
                password_hash='unused', role='CUSTOMER')
    db.add(user)
    db.commit()

    token = create_token(user.id, user.role)
    headers = {"Authorization": f"Bearer {token}"}

    s1 = f"sess_test_c1_{uuid.uuid4().hex[:8]}"
    s2 = f"sess_test_c2_{uuid.uuid4().hex[:8]}"
    db.add_all([
        ChatSession(id=s1, owner=f"user:{user.id}", memory_states={"title": "S1"}),
        ChatSession(id=s2, owner=f"user:{user.id}", memory_states={"title": "S2"}),
    ])
    db.commit()

    # 1. Xóa 1 session
    res1 = client.delete(f"/api/v1/customer/sessions/{s1}", headers=headers)
    assert res1.status_code == 200
    assert res1.json()["data"]["deleted_session_id"] == s1
    db.expire_all()
    assert db.get(ChatSession, s1) is None

    # 2. Xóa tất cả
    res_all = client.delete("/api/v1/customer/sessions", headers=headers)
    assert res_all.status_code == 200
    assert res_all.json()["data"]["deleted_sessions_count"] >= 1
    db.expire_all()
    assert db.get(ChatSession, s2) is None
    db.close()


def test_guest_decoupled_guest_id_delete_and_list():
    """Kiểm tra cơ chế tách guest_id: 1 guest có nhiều session, xóa 1 hoặc xóa tất cả đều chuẩn."""
    db = SessionLocal()
    guest_id = f"gst_{uuid.uuid4().hex[:12]}"
    g_headers = {"X-Guest-Id": guest_id}

    s1 = f"sess_test_g1_{uuid.uuid4().hex[:8]}"
    s2 = f"sess_test_g2_{uuid.uuid4().hex[:8]}"
    s3 = f"sess_test_g3_{uuid.uuid4().hex[:8]}"

    db.add_all([
        ChatSession(id=s1, owner=f"guest:{guest_id}", memory_states={"title": "Hỏi về VF3"}),
        ChatSession(id=s2, owner=f"guest:{guest_id}", memory_states={"title": "Trạm sạc gần nhất"}),
        ChatSession(id=s3, owner=f"guest:{guest_id}", memory_states={"title": "Bảo dưỡng 12000km"}),
    ])
    for sid in [s1, s2, s3]:
        db.add(Message(id=uuid.uuid4().hex, session_id=sid, sender_type="CUSTOMER", content="Xin chào"))
    db.commit()

    # Danh sách trả về đủ 3 sessions
    res_list = client.get(f"/api/v1/customer/sessions?guest_session_id={guest_id}", headers=g_headers)
    assert res_list.status_code == 200
    assert res_list.json()["data"]["total"] == 3

    # Xóa 1 session bất kỳ của guest bằng guest_id
    res_del_1 = client.delete(f"/api/v1/customer/sessions/{s1}?guest_session_id={guest_id}", headers=g_headers)
    assert res_del_1.status_code == 200
    db.expire_all()
    assert db.get(ChatSession, s1) is None

    # Xóa tất cả session của guest
    res_del_all = client.delete(f"/api/v1/customer/sessions?guest_session_id={guest_id}", headers=g_headers)
    assert res_del_all.status_code == 200
    assert res_del_all.json()["data"]["deleted_sessions_count"] == 2
    db.expire_all()
    assert db.get(ChatSession, s2) is None
    assert db.get(ChatSession, s3) is None
    db.close()


def test_guest_multi_session_claim_on_register():
    """Kiểm tra claim toàn bộ lịch sử theo guest_id khi đăng ký tài khoản."""
    db = SessionLocal()
    guest_claim_id = f"gst_claim_{uuid.uuid4().hex[:10]}"
    c1 = f"sess_c1_{uuid.uuid4().hex[:8]}"
    c2 = f"sess_c2_{uuid.uuid4().hex[:8]}"
    c3 = f"sess_c3_{uuid.uuid4().hex[:8]}"

    db.add_all([
        ChatSession(id=c1, owner=f"guest:{guest_claim_id}", memory_states={"title": "Cuộc 1"}),
        ChatSession(id=c2, owner=f"guest:{guest_claim_id}", memory_states={"title": "Cuộc 2"}),
        ChatSession(id=c3, owner=f"guest:{guest_claim_id}", memory_states={"title": "Cuộc 3"}),
    ])
    db.commit()

    reg_username = f"test_cust_{uuid.uuid4().hex[:6]}"
    res_reg = client.post(
        "/api/v1/auth/register",
        json={
            "username": reg_username,
            "password": "Password123@",
            "guest_session_id": guest_claim_id,
            "full_name": "Khách Test Claim",
        },
        headers={"X-Guest-Id": guest_claim_id},
    )
    assert res_reg.status_code == 200
    new_user_id = res_reg.json()["data"]["user"]["id"]
    new_token = res_reg.json()["data"]["token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}

    db.expire_all()
    claimed_sessions = db.query(ChatSession).filter(ChatSession.owner == f"user:{new_user_id}").all()
    claimed_ids = {s.id for s in claimed_sessions}
    assert {c1, c2, c3}.issubset(claimed_ids)

    # User mới xóa từng session và xóa tất cả đều thành công 200
    res_del_1 = client.delete(f"/api/v1/customer/sessions/{c1}", headers=new_headers)
    assert res_del_1.status_code == 200

    res_del_all = client.delete("/api/v1/customer/sessions", headers=new_headers)
    assert res_del_all.status_code == 200
    db.expire_all()
    assert db.get(ChatSession, c2) is None
    assert db.get(ChatSession, c3) is None
    db.close()


def test_guest_claim_idor_protection():
    """Kiểm tra chống chiếm đoạt session: gửi session_id của người khác không được đổi chủ."""
    db = SessionLocal()
    victim_guest_id = f"gst_victim_{uuid.uuid4().hex[:10]}"
    victim_session = f"sess_victim_{uuid.uuid4().hex[:8]}"
    db.add(ChatSession(id=victim_session, owner=f"guest:{victim_guest_id}", memory_states={"title": "Session bí mật của nạn nhân"}))
    db.commit()

    attacker_username = f"attacker_{uuid.uuid4().hex[:6]}"
    db.add(User(
        id=uuid.uuid4().hex,
        username=attacker_username,
        password_hash=hash_password("Password123@"),
        role="CUSTOMER",
        full_name="Kẻ tấn công",
    ))
    db.commit()

    # Kẻ tấn công login gửi session_id của nạn nhân nhằm claim trái phép
    res_attack = client.post(
        "/api/v1/auth/login",
        json={
            "username": attacker_username,
            "password": "Password123@",
            "guest_session_id": victim_session,
        },
    )
    assert res_attack.status_code == 200
    db.expire_all()
    victim_s_check = db.get(ChatSession, victim_session)
    assert victim_s_check.owner == f"guest:{victim_guest_id}"

    db.delete(victim_s_check)
    db.commit()
    db.close()


def test_cross_user_isolation():
    """Kiểm tra cô lập dữ liệu tuyệt đối giữa các user:
    User A tạo session, User B đăng nhập thì:
    - GET /sessions của B không chứa session của A
    - GET /sessions/{id}/history của A từ B -> 404
    - PATCH /sessions/{id} của A từ B -> 404
    - DELETE /sessions/{id} của A từ B -> 404
    """
    db = SessionLocal()
    user_a = User(
        id=f"usr_a_{uuid.uuid4().hex[:8]}",
        username=f"user_a_{uuid.uuid4().hex[:6]}",
        password_hash=hash_password("Pass123@"),
        role="CUSTOMER",
        full_name="Khách Hàng A",
    )
    user_b = User(
        id=f"usr_b_{uuid.uuid4().hex[:8]}",
        username=f"user_b_{uuid.uuid4().hex[:6]}",
        password_hash=hash_password("Pass123@"),
        role="CUSTOMER",
        full_name="Khách Hàng B",
    )
    db.add_all([user_a, user_b])
    db.commit()

    # User A có 1 session
    sess_a = f"sess_a_{uuid.uuid4().hex[:8]}"
    db.add(ChatSession(id=sess_a, owner=f"user:{user_a.id}", memory_states={"title": "Session bí mật của A"}))
    db.add(Message(id=uuid.uuid4().hex, session_id=sess_a, sender_type="CUSTOMER", content="Nội dung riêng tư của A"))
    db.commit()

    token_b = create_token(user_b.id, user_b.role)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. B lấy danh sách session -> không chứa sess_a
    res_list_b = client.get("/api/v1/customer/sessions", headers=headers_b)
    assert res_list_b.status_code == 200
    b_session_ids = [s["session_id"] for s in res_list_b.json()["data"]["sessions"]]
    assert sess_a not in b_session_ids

    # 2. B cố truy cập lịch sử của A -> 404
    res_hist_b = client.get(f"/api/v1/customer/sessions/{sess_a}/history", headers=headers_b)
    assert res_hist_b.status_code == 404

    # 3. B cố đổi tên session của A -> 404
    res_patch_b = client.patch(f"/api/v1/customer/sessions/{sess_a}", json={"title": "Hacked"}, headers=headers_b)
    assert res_patch_b.status_code == 404

    # 4. B cố xóa session của A -> 404
    res_del_b = client.delete(f"/api/v1/customer/sessions/{sess_a}", headers=headers_b)
    assert res_del_b.status_code == 404

    # Xác nhận session của A vẫn an toàn trong DB
    db.expire_all()
    s_a_check = db.get(ChatSession, sess_a)
    assert s_a_check is not None
    assert s_a_check.owner == f"user:{user_a.id}"

    # Dọn dẹp
    db.delete(s_a_check)
    db.query(Message).filter(Message.session_id == sess_a).delete()
    db.delete(user_a)
    db.delete(user_b)
    db.commit()
    db.close()
