"""Seed dữ liệu mẫu chuẩn hóa cho SQLite theo đúng đặc tả demo-scenarios.md và data-model.md.

Chạy (từ thư mục gốc):
    python -m src.seed            # Chỉ seed nếu DB còn trống
    python -m src.seed --reset    # Xóa sạch dữ liệu cũ và seed lại từ đầu
"""

import sys
import uuid
from datetime import UTC, datetime, timedelta

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.db import Base, SessionLocal, engine
from src.models.db_models import (
    Case,
    CaseBrief,
    Intent,
    Message,
    Priority,
    SenderType,
    StaffAction,
    StaffAuditLog,
    TicketStatus,
)


def seed_database() -> None:
    # Đảm bảo các bảng SQLite đã được khởi tạo
    Base.metadata.create_all(bind=engine)

    reset = "--reset" in sys.argv
    with SessionLocal() as db:
        if reset:
            for model in (StaffAuditLog, CaseBrief, Message, Case):
                db.query(model).delete()
            db.commit()
            print("[seed] Đã xóa toàn bộ dữ liệu cũ.")
        elif db.query(Case).count() > 0:
            print("[seed] DB đã có dữ liệu. Sử dụng flag --reset nếu muốn seed lại.")
            return

        now = datetime.now(UTC)

        # ======================================================================
        # KỊCH BẢN DEMO 1: Sự cố không sạc được tại Trụ sạc (P0 - Charging/Battery)
        # ======================================================================
        case_1 = Case(
            id="CASE-20260924-001",
            session_id="sess_vf_98234",
            mock_customer_id="CUST_MOCK_01",
            mock_customer_name="Khách hàng Demo 01",
            mock_customer_phone="0900-000-231",
            vehicle_code_mock="VF-SF-00231",
            vehicle_model="VF8",
            intent=Intent.CHARGING_BATTERY.value,
            priority=Priority.HIGH.value,
            status=TicketStatus.STAFF_REVIEWING.value,
            created_at=now - timedelta(hours=3),
            updated_at=now - timedelta(hours=2, minutes=50),
        )

        brief_1 = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case_1.id,
            summary="Xe VF8 không nhận sạc DC tại trạm Metropolis, màn hình xe báo mã lỗi CC01 và đèn trụ báo đỏ.",
            captured_fields={
                "vehicle_model": "VF8",
                "station_location": "Vincom Metropolis Liễu Giai",
                "charger_id": "VN-CS-HN042-P02",
                "error_code": "CC01",
                "current_soc": "18%",
            },
            suggested_action="Kiểm tra tín hiệu handshake giao tiếp trụ sạc P02 từ xa hoặc cử nhân viên kỹ thuật trạm hỗ trợ cắm lại cáp sạc.",
            confidence_score=0.92,
            is_edited_by_staff=False,
            generated_at=now - timedelta(hours=2, minutes=55),
        )

        msgs_1 = [
            Message(
                id=str(uuid.uuid4()),
                case_id=case_1.id,
                session_id=case_1.session_id,
                sender_type=SenderType.CUSTOMER.value,
                content="Xe VF8 của tôi không nhận sạc ở trạm Metropolis, trụ báo đèn đỏ.",
                created_at=now - timedelta(hours=3),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_1.id,
                session_id=case_1.session_id,
                sender_type=SenderType.AGENT.value,
                content="Dạ em ghi nhận xe VF8 đang không nhận sạc tại trạm Metropolis. Màn hình xe có hiển thị mã lỗi (ví dụ: CC01, BMS_012) hoặc anh/chị có mã trụ sạc không ạ?",
                msg_metadata={"turn": 1, "suggested_replies": ["Mã lỗi CC01, trụ P02", "Đèn đỏ, không hiện mã"]},
                created_at=now - timedelta(hours=2, minutes=58),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_1.id,
                session_id=case_1.session_id,
                sender_type=SenderType.CUSTOMER.value,
                content="Mã lỗi trên màn hình là CC01, tôi cắm trụ VN-CS-HN042-P02, pin còn 18%.",
                created_at=now - timedelta(hours=2, minutes=56),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_1.id,
                session_id=case_1.session_id,
                sender_type=SenderType.AGENT.value,
                content="Hệ thống đã ghi nhận đầy đủ dữ kiện kỹ thuật và tạo hồ sơ hỗ trợ CASE-20260924-001. Hồ sơ đã chuyển đến chuyên viên dịch vụ để xử lý.",
                msg_metadata={"priority": Priority.HIGH.value},
                created_at=now - timedelta(hours=2, minutes=55),
            ),
        ]

        # ======================================================================
        # KỊCH BẢN DEMO 2: Rùa vàng & Giảm công suất nguy hiểm (Critical Safety)
        # ======================================================================
        case_2 = Case(
            id="CASE-20260924-002",
            session_id="sess_vf_critical_881",
            mock_customer_id="CUST_MOCK_99",
            mock_customer_name="Khách hàng Demo 99",
            mock_customer_phone="0900-000-991",
            vehicle_code_mock="VF-SF-99120",
            vehicle_model="VF9",
            intent=Intent.SERVICE_INCIDENT.value,
            priority=Priority.CRITICAL.value,
            status=TicketStatus.STAFF_REVIEWING.value,
            created_at=now - timedelta(hours=1, minutes=30),
            updated_at=now - timedelta(hours=1, minutes=20),
        )

        brief_2 = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case_2.id,
            summary="Xe VF9 đang chạy trên cao tốc hiện biểu tượng rùa vàng và xe bị giật, đạp ga không lên quá 30km/h.",
            captured_fields={
                "vehicle_model": "VF9",
                "location": "Cao tốc Hà Nội - Hải Phòng",
                "warning_icon": "Rùa vàng",
                "speed_issue": "Không vượt quá 30km/h",
                "safety_flag": True,
            },
            suggested_action="Điều phối Đội cứu hộ cao tốc khẩn cấp và gọi trực tiếp hỗ trợ khách hàng an toàn.",
            confidence_score=0.98,
            is_edited_by_staff=False,
            generated_at=now - timedelta(hours=1, minutes=25),
        )

        msgs_2 = [
            Message(
                id=str(uuid.uuid4()),
                case_id=case_2.id,
                session_id=case_2.session_id,
                sender_type=SenderType.CUSTOMER.value,
                content="Xe VF9 của tôi đang chạy trên cao tốc thì hiện biểu tượng rùa vàng và xe bị giật, đạp ga không lên quá 30km/h.",
                created_at=now - timedelta(hours=1, minutes=30),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_2.id,
                session_id=case_2.session_id,
                sender_type=SenderType.AGENT.value,
                content="Anh/chị vui lòng bật đèn khẩn cấp (Hazard), từ từ tấp xe vào làn dừng khẩn cấp an toàn và gọi hotline cứu hộ 1900-232389. Hệ thống đã kích hoạt hồ sơ cứu hộ khẩn cấp CASE-20260924-002.",
                msg_metadata={"priority": Priority.CRITICAL.value, "safety_alert": True},
                created_at=now - timedelta(hours=1, minutes=29),
            ),
        ]

        audit_2 = StaffAuditLog(
            id=str(uuid.uuid4()),
            case_id=case_2.id,
            staff_id="STAFF_RESCUE_01",
            action=StaffAction.REROUTE.value,
            previous_state={"status": TicketStatus.STAFF_REVIEWING.value},
            new_state={"status": TicketStatus.IN_PROGRESS.value, "assigned": "Đội Cứu Hộ Cao Tốc"},
            notes="Ca khẩn cấp cao tốc, đã liên hệ cứu hộ trạm gần nhất tiếp cận hiện trường.",
            created_at=now - timedelta(hours=1, minutes=20),
        )

        # ======================================================================
        # KỊCH BẢN DEMO 3: Thiếu dữ kiện sau 2 lượt (Needs Information)
        # ======================================================================
        case_3 = Case(
            id="CASE-20260924-003",
            session_id="sess_vf_clarify_332",
            mock_customer_id="CUST_MOCK_02",
            mock_customer_name="Khách hàng Demo 02",
            mock_customer_phone="0900-000-445",
            vehicle_code_mock="VF-SF-00445",
            vehicle_model="VF5",
            intent=Intent.SERVICE_INCIDENT.value,
            priority=Priority.MEDIUM.value,
            status=TicketStatus.NEEDS_INFORMATION.value,
            created_at=now - timedelta(minutes=45),
            updated_at=now - timedelta(minutes=40),
        )

        brief_3 = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case_3.id,
            summary="Xe VF5 báo đèn lỗi trên bảng đồng hồ trung tâm (sau 2 lượt clarify vẫn chưa cung cấp mã lỗi cụ thể).",
            captured_fields={
                "vehicle_model": "VF5",
                "missing_fields": ["error_code", "symptom_detail"],
            },
            suggested_action="Nhân viên CSKH liên hệ khách hàng để hướng dẫn chụp lại màn hình cảnh báo.",
            confidence_score=0.65,
            is_edited_by_staff=False,
            generated_at=now - timedelta(minutes=40),
        )

        msgs_3 = [
            Message(
                id=str(uuid.uuid4()),
                case_id=case_3.id,
                session_id=case_3.session_id,
                sender_type=SenderType.CUSTOMER.value,
                content="Xe VF5 của mình báo đèn lỗi trên màn hình.",
                created_at=now - timedelta(minutes=45),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_3.id,
                session_id=case_3.session_id,
                sender_type=SenderType.AGENT.value,
                content="Dạ anh/chị cho em biết biểu tượng đèn cảnh báo có màu gì và hiển thị ký hiệu gì không ạ?",
                msg_metadata={"turn": 1},
                created_at=now - timedelta(minutes=44),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_3.id,
                session_id=case_3.session_id,
                sender_type=SenderType.CUSTOMER.value,
                content="Nó hiện đèn màu vàng nhưng tôi không nhớ rõ hình gì.",
                created_at=now - timedelta(minutes=42),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_3.id,
                session_id=case_3.session_id,
                sender_type=SenderType.AGENT.value,
                content="Hệ thống đã tạo hồ sơ ghi nhận CASE-20260924-003. Do chưa đủ một số dữ kiện kỹ thuật, hồ sơ được chuyển sang hàng đợi nhân viên hỗ trợ; nhân viên sẽ kiểm tra hoặc yêu cầu bổ sung thông tin.",
                msg_metadata={"turn": 2, "status": TicketStatus.NEEDS_INFORMATION.value},
                created_at=now - timedelta(minutes=40),
            ),
        ]

        # ======================================================================
        # KỊCH BẢN DEMO 4: Sales & Tư vấn xe (Resolved / Closed)
        # ======================================================================
        case_4 = Case(
            id="CASE-20260924-004",
            session_id="sess_vf_sales_102",
            mock_customer_id="CUST_MOCK_03",
            mock_customer_name="Khách hàng Demo 03",
            mock_customer_phone="0900-000-312",
            vehicle_code_mock="VF-SF-00312",
            vehicle_model="VF3",
            intent=Intent.SALES_GENERAL_INFO.value,
            priority=Priority.LOW.value,
            status=TicketStatus.RESOLVED.value,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(hours=18),
        )

        brief_4 = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case_4.id,
            summary="Khách hỏi giá lăn bánh và chính sách thuê pin của dòng xe VF3.",
            captured_fields={
                "vehicle_model": "VF3",
                "inquiry_topics": ["Bảng giá lăn bánh", "Chính sách thuê pin"],
            },
            suggested_action="Showroom VinFast liên hệ tư vấn báo giá chi tiết.",
            confidence_score=0.95,
            is_edited_by_staff=True,
            generated_at=now - timedelta(days=1),
        )

        msgs_4 = [
            Message(
                id=str(uuid.uuid4()),
                case_id=case_4.id,
                session_id=case_4.session_id,
                sender_type=SenderType.CUSTOMER.value,
                content="Cho mình hỏi giá lăn bánh xe VF3 và có gói thuê pin không?",
                created_at=now - timedelta(days=1),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_4.id,
                session_id=case_4.session_id,
                sender_type=SenderType.AGENT.value,
                content="Dạ em đã ghi nhận nhu cầu tư vấn xe VF3 và chuyển tới chuyên viên bán hàng gần nhất.",
                created_at=now - timedelta(days=1, minutes=-2),
            ),
        ]

        audit_4 = StaffAuditLog(
            id=str(uuid.uuid4()),
            case_id=case_4.id,
            staff_id="STAFF_SALES_01",
            action=StaffAction.APPROVE.value,
            previous_state={"status": TicketStatus.STAFF_REVIEWING.value},
            new_state={"status": TicketStatus.RESOLVED.value},
            notes="Đã gửi bảng báo giá và liên hệ khách tư vấn gói thuê pin.",
            created_at=now - timedelta(hours=18),
        )

        # Lưu toàn bộ vào SQLite
        db.add_all([case_1, case_2, case_3, case_4])
        db.add_all([brief_1, brief_2, brief_3, brief_4])
        db.add_all(msgs_1 + msgs_2 + msgs_3 + msgs_4)
        db.add_all([audit_2, audit_4])
        db.commit()

        print("[seed] Đã seed thành công 4 kịch bản chuẩn hóa (CASE-20260924-001 -> 004) vào SQLite!")


if __name__ == "__main__":
    seed_database()
