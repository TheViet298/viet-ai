"""Seed dữ liệu mẫu cách ly 2 chiều (is_demo=True) chuẩn hóa cho ServiceFlow.

Theo đúng quyết định kiến trúc:
- Chỉ thao tác trên các bản ghi có cờ is_demo=True.
- Mật khẩu đọc trực tiếp từ biến môi trường DEMO_SEED_PASSWORD (không hardcode, không fallback).
- Dữ liệu thật (is_demo=False) tuyệt đối không bị ảnh hưởng.
- 9 kịch bản định nghĩa trong fixtures/seed_demo.json.
- Mã case theo tiền tố DEMO-YYYYMMDD-xxx với thời gian tương đối tính từ thời điểm chạy.

Cách chạy:
    python -m src.seed --demo
    python -m src.seed --demo --reset --yes
"""

import argparse
import json
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config import get_settings
from src.db import Base, SessionLocal, engine, ensure_schema
from src.models.db_models import (
    Attachment,
    AttachmentStatus,
    AuthorType,
    Case,
    CaseBrief,
    CaseLocation,
    CaseUpdate,
    ChatSession,
    CustomerFeedback,
    Intent,
    Message,
    Priority,
    SenderType,
    StaffAction,
    StaffAuditLog,
    TicketStatus,
    User,
    UserRole,
    utcnow,
)
from src.services.auth import hash_password


DEMO_USERS_MAP = {
    "staff": {
        "id": "USER_DEMO_STAFF",
        "username": "demo.staff@vinfast.vn",
        "role": UserRole.STAFF.value,
        "full_name": "Chuyên viên Demo VinFast",
        "phone": "1900232389",
        "vehicle_model": None,
        "mock_customer_id": None,
    },
    "customer1": {
        "id": "USER_DEMO_CUST_01",
        "username": "demo.customer@vinfast.vn",
        "role": UserRole.CUSTOMER.value,
        "full_name": "Khách hàng Demo 1",
        "phone": "0912345678",
        "vehicle_model": "VF8",
        "mock_customer_id": "CUST_DEMO_01",
    },
    "customer2": {
        "id": "USER_DEMO_CUST_02",
        "username": "demo.customer2@vinfast.vn",
        "role": UserRole.CUSTOMER.value,
        "full_name": "Khách hàng Demo 2",
        "phone": "0987654321",
        "vehicle_model": "VF9",
        "mock_customer_id": "CUST_DEMO_02",
    },
}


def load_scenarios() -> list[dict]:
    root = Path(__file__).resolve().parents[1]
    fixtures_path = root / "fixtures" / "seed_demo.json"
    if not fixtures_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file kịch bản mẫu tại {fixtures_path}")
    return json.loads(fixtures_path.read_text(encoding="utf-8"))


def reset_demo_data(db) -> int:
    """Xóa an toàn và triệt để các bản ghi demo (is_demo=True), không đụng chạm dữ liệu thật."""
    demo_cases = db.query(Case).filter(Case.is_demo.is_(True)).all()
    demo_case_ids = [c.id for c in demo_cases]

    if demo_case_ids:
        db.query(CaseLocation).filter(CaseLocation.case_id.in_(demo_case_ids)).delete(synchronize_session=False)
        db.query(CaseUpdate).filter(CaseUpdate.case_id.in_(demo_case_ids)).delete(synchronize_session=False)
        db.query(CustomerFeedback).filter(CustomerFeedback.case_id.in_(demo_case_ids)).delete(synchronize_session=False)
        db.query(Attachment).filter(Attachment.case_id.in_(demo_case_ids)).delete(synchronize_session=False)
        db.query(StaffAuditLog).filter(StaffAuditLog.case_id.in_(demo_case_ids)).delete(synchronize_session=False)
        db.query(CaseBrief).filter(CaseBrief.case_id.in_(demo_case_ids)).delete(synchronize_session=False)
        db.query(Message).filter(Message.case_id.in_(demo_case_ids)).delete(synchronize_session=False)
        db.query(Case).filter(Case.id.in_(demo_case_ids)).delete(synchronize_session=False)

    db.query(ChatSession).filter(ChatSession.is_demo.is_(True)).delete(synchronize_session=False)
    db.query(User).filter(User.is_demo.is_(True)).delete(synchronize_session=False)

    db.commit()
    return len(demo_case_ids)


def seed_database(reset: bool = False, demo: bool = True) -> None:
    """
    Hàm seed dữ liệu kịch bản demo cách ly 2 chiều.
    Yêu cầu cờ is_demo=True và mật khẩu từ biến môi trường DEMO_SEED_PASSWORD.
    """
    ensure_schema()

    demo_password = os.environ.get("DEMO_SEED_PASSWORD")
    if not demo_password:
        raise ValueError(
            "Biến môi trường DEMO_SEED_PASSWORD không được để trống khi thực hiện seed demo. "
            "Vui lòng cấu hình DEMO_SEED_PASSWORD."
        )

    Base.metadata.create_all(bind=engine)
    scenarios = load_scenarios()
    now = datetime.now(UTC)
    date_str = now.strftime("%Y%m%d")

    with SessionLocal() as db:
        if reset:
            deleted_count = reset_demo_data(db)
            print(f"[seed] Đã dọn dẹp sạch {deleted_count} ca sự cố demo cũ.")

        # 1. Khởi tạo/Cập nhật các tài khoản người dùng Demo
        users_created = {}
        for key, uinfo in DEMO_USERS_MAP.items():
            user = db.query(User).filter(User.username == uinfo["username"]).first()
            if not user:
                user = User(
                    id=uinfo["id"],
                    username=uinfo["username"],
                    password_hash=hash_password(demo_password),
                    role=uinfo["role"],
                    full_name=uinfo["full_name"],
                    phone=uinfo["phone"],
                    vehicle_model=uinfo["vehicle_model"],
                    mock_customer_id=uinfo["mock_customer_id"],
                    is_demo=True,
                    created_at=now - timedelta(days=7),
                )
                db.add(user)
                db.flush()
            else:
                user.password_hash = hash_password(demo_password)
                user.role = uinfo["role"]
                user.is_demo = True
                user.full_name = uinfo["full_name"]
                user.phone = uinfo["phone"]
                user.vehicle_model = uinfo["vehicle_model"]
                user.mock_customer_id = uinfo["mock_customer_id"]
                db.flush()
            users_created[key] = user

        # 2. Xây dựng 9 Kịch bản sự cố Demo
        seeded_cases_count = 0
        for item in scenarios:
            scenario_key = item["scenario_key"]
            case_id = f"DEMO-{date_str}-{item['index']}"
            session_id = item.get("session_id") or f"DEMO-SESS-{date_str}-{item['index']}"
            user_obj = users_created[item["user_key"]]

            existing_case = db.query(Case).filter(Case.id == case_id).first()
            if existing_case and not reset:
                # Idempotent: Bỏ qua nếu đã tồn tại trường hợp này trong ngày
                continue

            created_time = now - timedelta(hours=item.get("created_offset_hours", 2))
            updated_time = now - timedelta(hours=item.get("updated_offset_hours", 1))

            safety_ack_time = None
            if item.get("safety_acknowledged_offset_minutes") is not None:
                safety_ack_time = now - timedelta(minutes=item["safety_acknowledged_offset_minutes"])

            # 2.1 ChatSession Demo
            chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not chat_session:
                chat_session = ChatSession(
                    id=session_id,
                    owner=f"user:{user_obj.id}",
                    is_demo=True,
                )
                db.add(chat_session)
                db.flush()

            # 2.2 Case Demo
            case = Case(
                id=case_id,
                user_id=user_obj.id,
                session_id=session_id,
                mock_customer_id=user_obj.mock_customer_id,
                mock_customer_name=user_obj.full_name,
                mock_customer_phone=user_obj.phone,
                vehicle_code_mock=item["vehicle_code_mock"],
                vehicle_model=item["vehicle_model"],
                intent=item["intent"],
                priority=item["priority"],
                status=item["status"],
                safety_status=item["safety_status"],
                safety_acknowledged_at=safety_ack_time,
                incident_version=1,
                is_demo=True,
                created_at=created_time,
                updated_at=updated_time,
            )
            db.add(case)
            db.flush()

            # 2.3 CaseBrief
            brief_data = item.get("brief")
            if brief_data:
                brief = CaseBrief(
                    id=str(uuid.uuid4()),
                    case_id=case.id,
                    summary=brief_data["summary"],
                    captured_fields=brief_data["captured_fields"],
                    suggested_action=brief_data["suggested_action"],
                    confidence_score=brief_data.get("confidence_score", 0.95),
                    is_edited_by_staff=False,
                    generated_at=created_time,
                )
                db.add(brief)

            # 2.4 CaseLocation (nếu có)
            loc_data = item.get("location")
            if loc_data:
                loc = CaseLocation(
                    id=str(uuid.uuid4()),
                    case_id=case.id,
                    status=loc_data.get("status", "SUCCESS"),
                    source=loc_data.get("source", "DEVICE_GPS"),
                    location_label=loc_data.get("location_label"),
                    latitude=loc_data.get("latitude"),
                    longitude=loc_data.get("longitude"),
                    precision=loc_data.get("precision", "EXACT"),
                    share_with_staff=loc_data.get("share_with_staff", True),
                    created_at=created_time,
                )
                db.add(loc)

            # 2.4.1 Attachment (nếu có, e.g. scenario 1)
            att_data = item.get("attachment")
            if att_data:
                att = Attachment(
                    id=att_data["id"],
                    case_id=case.id,
                    storage_key=att_data["storage_key"],
                    mime_type=att_data.get("mime_type", "image/jpeg"),
                    analysis_status=att_data.get("analysis_status", AttachmentStatus.UPLOADED.value),
                    ocr_text=att_data.get("ocr_text"),
                    detected_signals=att_data.get("detected_signals"),
                    vision_confidence=att_data.get("vision_confidence"),
                    created_at=created_time,
                )
                db.add(att)

            # 2.5 Messages
            for m in item.get("messages", []):
                msg_time = now - timedelta(minutes=m["offset_minutes"])
                msg = Message(
                    id=str(uuid.uuid4()),
                    case_id=case.id,
                    session_id=session_id,
                    sender_type=m["sender"],
                    content=m["content"],
                    created_at=msg_time,
                )
                db.add(msg)

            # 2.6 CaseUpdates
            for u in item.get("updates", []):
                u_time = now - timedelta(minutes=u["offset_minutes"])
                update = CaseUpdate(
                    id=str(uuid.uuid4()),
                    case_id=case.id,
                    author_type=u["author_type"],
                    status_after_update=u["status_after_update"],
                    customer_message=u["customer_message"],
                    next_step=u["next_step"],
                    awaiting_customer_confirmation=u.get("awaiting_customer_confirmation", False),
                    created_at=u_time,
                )
                db.add(update)

            # 2.7 Audit Logs (nếu có riêng, e.g. scenario 9)
            for a in item.get("audit_logs", []):
                a_time = now - timedelta(minutes=a["offset_minutes"])
                audit = StaffAuditLog(
                    id=str(uuid.uuid4()),
                    case_id=case.id,
                    staff_id=a["staff_id"],
                    action=a["action"],
                    previous_state={"status": a.get("previous_status", "Resolved")},
                    new_state={"status": a.get("new_status", "Closed")},
                    notes=a["notes"],
                    created_at=a_time,
                )
                db.add(audit)

            # 2.8 CustomerFeedback (nếu có, e.g. scenario 7 & 8)
            fb_data = item.get("feedback")
            if fb_data:
                fb = CustomerFeedback(
                    id=str(uuid.uuid4()),
                    case_id=case.id,
                    rating=fb_data["rating"],
                    comment=fb_data.get("comment"),
                    reason_tags=fb_data.get("reason_tags", []),
                    created_at=updated_time,
                    updated_at=updated_time,
                )
                db.add(fb)

            seeded_cases_count += 1

        db.commit()
        print(f"[seed] Đã hoàn tất khởi tạo {seeded_cases_count} ca sự cố demo (tiền tố DEMO-{date_str}-xxx).")


def main() -> int:
    parser = argparse.ArgumentParser(description="ServiceFlow Demo Data Seed (2-way Isolated)")
    parser.add_argument("--demo", action="store_true", help="Kích hoạt seed dữ liệu kịch bản Demo (bắt buộc)")
    parser.add_argument("--reset", action="store_true", help="Dọn dẹp sạch dữ liệu demo cũ trước khi dựng lại")
    parser.add_argument("--yes", "-y", action="store_true", help="Xác nhận tiếp tục không cần hỏi tương tác")
    args = parser.parse_args()

    if not args.demo:
        print(
            "CẢNH BÁO: Lệnh seed chỉ dành cho dữ liệu Demo có cờ is_demo=True.\n"
            "Vui lòng chạy kèm cờ '--demo':\n"
            "    python -m src.seed --demo\n"
            "    python -m src.seed --demo --reset --yes",
            file=sys.stderr,
        )
        return 1

    if args.reset and not args.yes:
        if sys.stdin.isatty():
            confirm = input("[CẢNH BÁO] Thao tác này sẽ xóa sạch dữ liệu DEMO cũ. Tiếp tục? (y/N): ")
            if confirm.strip().lower() not in ("y", "yes"):
                print("[seed] Đã hủy thao tác reset.")
                return 0
        else:
            print("[seed ERROR] Cần thêm cờ '--yes' khi chạy '--reset' trong script tự động.", file=sys.stderr)
            return 1

    try:
        seed_database(reset=args.reset, demo=True)
        return 0
    except Exception as exc:
        print(f"[seed ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
