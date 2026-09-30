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
    Attachment,
    AttachmentStatus,
    Case,
    CaseBrief,
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
)
from src.services.auth import hash_password


def seed_database() -> None:
    # Đảm bảo các bảng SQLite đã được khởi tạo
    Base.metadata.create_all(bind=engine)

    reset = "--reset" in sys.argv
    with SessionLocal() as db:
        if reset:
            for model in (CustomerFeedback, Attachment, StaffAuditLog, CaseBrief, Message, Case, User):
                db.query(model).delete()
            db.commit()
            print("[seed] Đã xóa toàn bộ dữ liệu cũ.")
        elif db.query(Case).count() > 0:
            print("[seed] DB đã có dữ liệu. Sử dụng flag --reset nếu muốn seed lại.")
            return

        now = datetime.now(UTC)

        # ======================================================================
        # 0. TÀI KHOẢN NGƯỜI DÙNG DEMO (auth-and-rbac.md & ADR-004)
        # ======================================================================
        user_staff = User(
            id="STAFF_001",
            username="staff@vinfast.vn",
            password_hash=hash_password("staff123"),
            role=UserRole.STAFF.value,
            mock_customer_id=None,
            created_at=now - timedelta(days=30),
        )
        user_cust_1 = User(
            id="USER_CUST_01",
            username="customer@vinfast.vn",
            password_hash=hash_password("customer123"),
            role=UserRole.CUSTOMER.value,
            mock_customer_id="CUST_MOCK_01",
            created_at=now - timedelta(days=10),
        )
        user_cust_2 = User(
            id="USER_CUST_02",
            username="customer2@vinfast.vn",
            password_hash=hash_password("customer123"),
            role=UserRole.CUSTOMER.value,
            mock_customer_id="CUST_MOCK_02",
            created_at=now - timedelta(days=5),
        )
        db.add_all([user_staff, user_cust_1, user_cust_2])
        db.flush()

        # ======================================================================
        # KỊCH BẢN DEMO 1: Sự cố không sạc được tại Trụ sạc (P0 - Charging/Battery)
        # ======================================================================
        case_1 = Case(
            id="CASE-20260924-001",
            user_id=user_cust_1.id,
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
                "visual_signals": [
                    {
                        "error_code_candidate": "CC01",
                        "charger_lamp": "RED",
                        "warning_type": "CHARGING_COMMUNICATION_ERROR",
                    }
                ],
            },
            suggested_action="Kiểm tra tín hiệu handshake giao tiếp trụ sạc P02 từ xa hoặc cử nhân viên kỹ thuật trạm hỗ trợ cắm lại cáp sạc.",
            confidence_score=0.92,
            is_edited_by_staff=False,
            generated_at=now - timedelta(hours=2, minutes=55),
        )

        msg_1_1 = Message(
            id=str(uuid.uuid4()),
            case_id=case_1.id,
            session_id=case_1.session_id,
            sender_type=SenderType.CUSTOMER.value,
            content="Xe VF8 của tôi không nhận sạc ở trạm Metropolis, trụ báo đèn đỏ.",
            created_at=now - timedelta(hours=3),
        )
        msg_1_2 = Message(
            id=str(uuid.uuid4()),
            case_id=case_1.id,
            session_id=case_1.session_id,
            sender_type=SenderType.AGENT.value,
            content="Dạ em ghi nhận xe VF8 đang không nhận sạc tại trạm Metropolis. Màn hình xe có hiển thị mã lỗi (ví dụ: CC01, BMS_012) hoặc anh/chị có mã trụ sạc không ạ?",
            msg_metadata={"turn": 1, "suggested_replies": ["Mã lỗi CC01, trụ P02", "Đèn đỏ, không hiện mã"]},
            created_at=now - timedelta(hours=2, minutes=58),
        )
        msg_1_3 = Message(
            id=str(uuid.uuid4()),
            case_id=case_1.id,
            session_id=case_1.session_id,
            sender_type=SenderType.CUSTOMER.value,
            content="Mã lỗi trên màn hình là CC01, tôi cắm trụ VN-CS-HN042-P02, pin còn 18%.",
            created_at=now - timedelta(hours=2, minutes=56),
        )
        msgs_1 = [msg_1_1, msg_1_2, msg_1_3]

        # Ảnh đính kèm cho Scenario 1 theo ADR-004 & demo-scenarios.md
        att_1 = Attachment(
            id="ATT-20260930-001",
            case_id=case_1.id,
            message_id=msg_1_1.id,
            storage_key="data/attachments/demo_screen_cc01.jpg",
            mime_type="image/jpeg",
            analysis_status=AttachmentStatus.ANALYZED.value,
            ocr_text="Mã lỗi CC01 - Trụ sạc VN-CS-HN042-P02 đèn báo nhấp nháy đỏ",
            detected_signals={
                "error_code_candidate": "CC01",
                "charger_lamp": "RED",
                "warning_type": "CHARGING_COMMUNICATION_ERROR",
            },
            vision_confidence=0.92,
            created_at=now - timedelta(hours=3),
        )

        # ======================================================================
        # KỊCH BẢN DEMO 2: Sự cố khẩn cấp trên Cao tốc (CRITICAL - Hard Safety Rule)
        # ======================================================================
        case_2 = Case(
            id="CASE-20260924-002",
            user_id=user_cust_1.id,
            session_id="sess_vf_99120",
            mock_customer_id="CUST_MOCK_01",
            mock_customer_name="Khách hàng Demo 01",
            mock_customer_phone="0900-000-231",
            vehicle_code_mock="VF-SF-99120",
            vehicle_model="VF9",
            intent=Intent.SERVICE_INCIDENT.value,
            priority=Priority.CRITICAL.value,
            status=TicketStatus.STAFF_REVIEWING.value,
            created_at=now - timedelta(hours=1, minutes=15),
            updated_at=now - timedelta(hours=1, minutes=10),
        )

        brief_2 = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case_2.id,
            summary="SỰ CỐ NGUY HIỂM: Xe VF9 đang di chuyển trên cao tốc Long Thành - Dầu Giây báo rùa vàng và mất công suất đột ngột, xe đang dừng giữa đường.",
            captured_fields={
                "vehicle_model": "VF9",
                "incident_location": "Cao tốc Long Thành - Dầu Giây (Km 28)",
                "warning_signal": "Rùa vàng (Turtle Mode)",
                "symptom": "Mất công suất, dừng giữa đường",
                "risk_level": "CRITICAL",
                "immediate_action_required": True,
            },
            suggested_action="Kích hoạt điều phối cứu hộ cao tốc ngay lập tức; chuyên viên gọi trực tiếp cho khách hàng để hướng dẫn an toàn.",
            confidence_score=0.99,
            is_edited_by_staff=False,
            generated_at=now - timedelta(hours=1, minutes=14),
        )

        msgs_2 = [
            Message(
                id=str(uuid.uuid4()),
                case_id=case_2.id,
                session_id=case_2.session_id,
                sender_type=SenderType.CUSTOMER.value,
                content="Xe tôi đang chạy trên cao tốc Long Thành thì tự nhiên hiện rùa vàng và mất công suất, xe đang dừng giữa đường nguy hiểm quá!",
                created_at=now - timedelta(hours=1, minutes=15),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_2.id,
                session_id=case_2.session_id,
                sender_type=SenderType.AGENT.value,
                content="Dạ em hiểu tình huống khẩn cấp của anh/chị. Em đã tạo hồ sơ khẩn cấp gửi ngay đến đội ngũ cứu hộ kỹ thuật VinFast. Anh/chị hãy BẬT ĐÈN KHẨN CẤP (Hazard), từ từ tấp xe vào làn dừng khẩn cấp an toàn, di chuyển người ra ngoài lan can bảo vệ và liên hệ ngay Hotline cứu hộ 1900-232389.",
                msg_metadata={
                    "priority": Priority.CRITICAL.value,
                    "safe_guidance": "Bật đèn Hazard, tấp xe vào làn dừng khẩn cấp an toàn, gọi Hotline cứu hộ 1900-232389.",
                },
                created_at=now - timedelta(hours=1, minutes=14),
            ),
        ]

        audit_2 = StaffAuditLog(
            id=str(uuid.uuid4()),
            case_id=case_2.id,
            staff_id="STAFF_001",
            action=StaffAction.APPROVE.value,
            previous_state={"status": TicketStatus.STAFF_REVIEWING.value},
            new_state={"status": TicketStatus.IN_PROGRESS.value},
            notes="Đã gọi khách hàng hướng dẫn an toàn và chuyển đội cứu hộ cao tốc khu vực trạm thu phí Dầu Giây.",
            created_at=now - timedelta(hours=1),
        )

        # ======================================================================
        # KỊCH BẢN DEMO 3: Khách hàng hỏi thông tin sạc (Needs Information)
        # ======================================================================
        case_3 = Case(
            id="CASE-20260924-003",
            user_id=user_cust_1.id,
            session_id="sess_vf_11045",
            mock_customer_id="CUST_MOCK_01",
            mock_customer_name="Khách hàng Demo 01",
            mock_customer_phone="0900-000-231",
            vehicle_code_mock="VF-SF-00445",
            vehicle_model="VF3",
            intent=Intent.SERVICE_INCIDENT.value,
            priority=Priority.MEDIUM.value,
            status=TicketStatus.NEEDS_INFORMATION.value,
            created_at=now - timedelta(hours=5),
            updated_at=now - timedelta(hours=4, minutes=30),
        )

        brief_3 = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case_3.id,
            summary="Khách hàng hỏi về việc sạc xe VF3 tại nhà bị chậm, đã qua 2 lượt làm rõ nhưng chưa cung cấp thông số bộ sạc hoặc nguồn điện sử dụng.",
            captured_fields={
                "vehicle_model": "VF3",
                "inquiry": "Sạc tại nhà bị chậm",
                "missing_info": ["Công suất bộ sạc", "Loại ổ cắm", "Nguồn điện tiếp địa"],
            },
            suggested_action="Nhân viên CSKH liên hệ qua số điện thoại để hướng dẫn kiểm tra thông số bộ sạc treo tường.",
            confidence_score=0.75,
            is_edited_by_staff=False,
            generated_at=now - timedelta(hours=4, minutes=50),
        )

        msgs_3 = [
            Message(
                id=str(uuid.uuid4()),
                case_id=case_3.id,
                session_id=case_3.session_id,
                sender_type=SenderType.CUSTOMER.value,
                content="Xe VF3 của tôi sạc ở nhà cả đêm mà chỉ lên được có vài phần trăm.",
                created_at=now - timedelta(hours=5),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_3.id,
                session_id=case_3.session_id,
                sender_type=SenderType.AGENT.value,
                content="Dạ anh/chị cho em hỏi mình đang dùng bộ sạc di động 2.2kW cắm ổ dân dụng hay trụ sạc treo tường 7.4kW ạ? Đèn trên bộ sạc báo màu gì ạ?",
                msg_metadata={"turn": 1, "suggested_replies": ["Sạc di động 2.2kW", "Bộ sạc treo tường 7.4kW"]},
                created_at=now - timedelta(hours=4, minutes=58),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_3.id,
                session_id=case_3.session_id,
                sender_type=SenderType.CUSTOMER.value,
                content="Tôi cũng không rõ loại nào, cắm vào ổ điện bình thường thôi.",
                created_at=now - timedelta(hours=4, minutes=52),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_3.id,
                session_id=case_3.session_id,
                sender_type=SenderType.AGENT.value,
                content="Dạ hệ thống đã ghi nhận hồ sơ và chuyển thông tin đến chuyên viên kỹ thuật. Do cần thêm thông số bộ sạc, nhân viên hỗ trợ sẽ liên hệ trực tiếp với anh/chị để tư vấn chi tiết ạ.",
                msg_metadata={"turn": 2},
                created_at=now - timedelta(hours=4, minutes=50),
            ),
        ]

        # ======================================================================
        # KỊCH BẢN DEMO 4: Tư vấn chính sách giá & ưu đãi (Resolved + Feedback)
        # ======================================================================
        case_4 = Case(
            id="CASE-20260924-004",
            user_id=user_cust_2.id,
            session_id="sess_vf_55412",
            mock_customer_id="CUST_MOCK_02",
            mock_customer_name="Khách hàng Demo 02",
            mock_customer_phone="0911-222-333",
            vehicle_code_mock="VF-SF-00312",
            vehicle_model="VF5",
            intent=Intent.SALES_GENERAL_INFO.value,
            priority=Priority.LOW.value,
            status=TicketStatus.RESOLVED.value,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(hours=18),
        )

        brief_4 = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case_4.id,
            summary="Khách hàng tìm hiểu chính sách ưu đãi miễn phí sạc pin tại trạm V-GREEN và gói thuê pin xe VF5.",
            captured_fields={
                "vehicle_model": "VF5",
                "inquiry_type": "Chính sách sạc & Gói thuê pin",
                "resolution": "Đã giải thích chi tiết chính sách miễn phí sạc V-GREEN đến hết 30/06/2027.",
            },
            suggested_action="Gửi email tổng hợp bảng so sánh chi phí lăn bánh kèm chính sách sạc ưu đãi.",
            confidence_score=0.98,
            is_edited_by_staff=True,
            generated_at=now - timedelta(days=1, minutes=-1),
        )

        msgs_4 = [
            Message(
                id=str(uuid.uuid4()),
                case_id=case_4.id,
                session_id=case_4.session_id,
                sender_type=SenderType.CUSTOMER.value,
                content="Cho mình hỏi xe VF5 hiện nay có được miễn phí sạc ở trạm công cộng không?",
                created_at=now - timedelta(days=1),
            ),
            Message(
                id=str(uuid.uuid4()),
                case_id=case_4.id,
                session_id=case_4.session_id,
                sender_type=SenderType.AGENT.value,
                content="Dạ hiện nay các dòng xe điện VinFast (bao gồm VF5) đang được áp dụng chương trình miễn phí sạc tại hệ thống trạm sạc V-GREEN trên toàn quốc đến hết ngày 30/06/2027 theo chính sách 'Mãnh liệt Tinh thần Việt Nam'.",
                msg_metadata={
                    "citations": [{"source_id": "SRC-PR-2024", "title": "Chương trình Mãnh liệt Tinh thần Việt Nam"}]
                },
                created_at=now - timedelta(days=1, minutes=-1),
            ),
        ]

        audit_4 = StaffAuditLog(
            id=str(uuid.uuid4()),
            case_id=case_4.id,
            staff_id="STAFF_001",
            action=StaffAction.RESOLVE.value,
            previous_state={"status": TicketStatus.IN_PROGRESS.value},
            new_state={"status": TicketStatus.RESOLVED.value},
            notes="Đã gửi tài liệu chính sách qua email và khách hàng xác nhận đã hiểu rõ.",
            created_at=now - timedelta(hours=18),
        )

        feedback_4 = CustomerFeedback(
            id=str(uuid.uuid4()),
            case_id=case_4.id,
            rating=5,
            comment="Nhân viên hỗ trợ tư vấn rất nhanh và nhiệt tình, cảm ơn VinFast!",
            created_at=now - timedelta(hours=17),
        )

        # Lưu toàn bộ vào SQLite
        db.add_all([case_1, case_2, case_3, case_4])
        db.add_all([brief_1, brief_2, brief_3, brief_4])
        db.add_all(msgs_1 + msgs_2 + msgs_3 + msgs_4)
        db.add_all([att_1])
        db.add_all([audit_2, audit_4])
        db.add(feedback_4)
        db.commit()

        print("[seed] Đã seed thành công 4 kịch bản chuẩn hóa (CASE-20260924-001 -> 004) vào SQLite!")


if __name__ == "__main__":
    seed_database()
