"""Seed dữ liệu mẫu cho SQLite.

Chạy (trong thư mục backend/):
    python -m app.seed            # chỉ seed nếu DB còn trống
    python -m app.seed --reset    # xóa hết dữ liệu cũ rồi seed lại
"""
import sys
from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import (
    Case,
    Intent,
    Message,
    Priority,
    ReviewAction,
    ReviewerFeedback,
    SourceChannel,
    Ticket,
    TicketStatus,
)


def build_cases(now: datetime) -> list[Case]:
    # 1. Sales - đã duyệt và chuyển bộ phận
    sales = Case(
        source_channel=SourceChannel.web_chat.value,
        customer_ref="khach_web_001",
        intent=Intent.sales.value,
        priority=Priority.low.value,
        confidence=0.93,
        suggested_routing="Sales",
        brief_data={
            "type": "sales_inquiry",
            "summary": "Khách hỏi giá và gói pin của VF 5 Plus.",
            "vehicle_model": "VF 5 Plus",
            "questions": ["Giá lăn bánh", "Thuê pin hay mua pin"],
        },
        ticket_status=TicketStatus.ROUTED.value,
        created_at=now - timedelta(hours=5),
    )
    sales.messages = [
        Message(sender="customer", channel="web_chat",
                content="Cho mình hỏi giá VF 5 Plus và có thuê pin được không?"),
        Message(sender="agent", channel="web_chat",
                content="Chào anh/chị, em ghi nhận nhu cầu và chuyển bộ phận Sales tư vấn chi tiết ạ."),
    ]
    sales.tickets = [Ticket(assigned_department="Sales", dispatched_at=now - timedelta(hours=4))]
    sales.feedbacks = [
        ReviewerFeedback(reviewer_name="Reviewer Demo", action=ReviewAction.approve.value,
                         final_routing="Sales", comment="Brief đủ thông tin.")
    ]

    # 2. Charging - chờ reviewer duyệt
    charging = Case(
        source_channel=SourceChannel.zalo.value,
        customer_ref="zalo_0901234567",
        intent=Intent.charging.value,
        priority=Priority.medium.value,
        confidence=0.88,
        suggested_routing="Charging",
        brief_data={
            "type": "charging_support",
            "summary": "Trụ sạc công cộng báo lỗi, xe không nhận sạc.",
            "issue": "Trụ sạc không khởi động phiên sạc",
        },
        ticket_status=TicketStatus.PENDING_REVIEW.value,
        created_at=now - timedelta(hours=3),
    )
    charging.messages = [
        Message(sender="customer", channel="zalo",
                content="Trụ sạc ở trung tâm thương mại không nhận xe của mình."),
        Message(sender="agent", channel="zalo",
                content="Em đã ghi nhận sự cố trụ sạc, đang chuyển bộ phận Sạc & Pin xem xét."),
    ]

    # 3. Complaint - nhạy cảm, độ tin cậy thấp, cần người xử lý
    complaint = Case(
        source_channel=SourceChannel.email.value,
        customer_ref="khach@example.com",
        intent=Intent.complaint.value,
        priority=Priority.high.value,
        confidence=0.71,
        suggested_routing="CSKH",
        brief_data={
            "type": "complaint",
            "summary": "Khách bức xúc về thời gian chờ sửa chữa và tranh chấp bảo hành.",
            "sentiment": "negative",
            "sensitive": True,
        },
        ticket_status=TicketStatus.PENDING_REVIEW.value,
        created_at=now - timedelta(hours=2),
    )
    complaint.messages = [
        Message(sender="customer", channel="email",
                content="Xe đã vào xưởng 3 tuần chưa xong, tôi rất không hài lòng về bảo hành."),
    ]

    # 4. Service incident - thiếu dữ kiện, đang hỏi lại khách
    service_waiting = Case(
        source_channel=SourceChannel.web_chat.value,
        customer_ref="khach_web_002",
        intent=Intent.service_incident.value,
        priority=Priority.medium.value,
        confidence=0.82,
        suggested_routing=None,
        brief_data={"type": "service_incident", "missing_fields": ["vehicle_model", "error_code"]},
        ticket_status=TicketStatus.WAITING_USER.value,
        created_at=now - timedelta(hours=1),
    )
    service_waiting.messages = [
        Message(sender="customer", channel="web_chat", content="Xe của mình báo đèn lỗi trên màn hình."),
        Message(sender="agent", channel="web_chat",
                content="Anh/chị cho em biết dòng xe và mã lỗi hiển thị để em hỗ trợ nhé?"),
    ]

    # 5. Service incident khẩn cấp - critical, reviewer đã escalate
    service_critical = Case(
        source_channel=SourceChannel.hotline_transcript.value,
        customer_ref="hotline_0987654321",
        intent=Intent.service_incident.value,
        priority=Priority.critical.value,
        confidence=0.96,
        suggested_routing="Service",
        brief_data={
            "type": "service_incident",
            "summary": "Xe bốc khói khi đang chạy trên cao tốc.",
            "vehicle_model": "VF 8",
            "location": "Cao tốc Hà Nội - Hải Phòng",
            "safety_flag": True,
        },
        ticket_status=TicketStatus.ROUTED.value,
        created_at=now - timedelta(minutes=30),
    )
    service_critical.messages = [
        Message(sender="customer", channel="hotline_transcript",
                content="Xe VF 8 của tôi đang bốc khói, tôi đang ở trên cao tốc."),
        Message(sender="agent", channel="hotline_transcript",
                content="Anh/chị hãy dừng xe an toàn, rời khỏi xe và gọi hotline cứu hộ chính thức."),
    ]
    service_critical.tickets = [
        Ticket(assigned_department="Service", dispatched_at=now - timedelta(minutes=20))
    ]
    service_critical.feedbacks = [
        ReviewerFeedback(reviewer_name="Reviewer Demo", action=ReviewAction.escalate.value,
                         final_routing="Service", comment="Ca an toàn, ưu tiên xử lý ngay.")
    ]

    # 6. Ngoài phạm vi
    out_of_scope = Case(
        source_channel=SourceChannel.web_chat.value,
        customer_ref="khach_web_003",
        intent=Intent.out_of_scope.value,
        priority=Priority.low.value,
        confidence=0.9,
        suggested_routing=None,
        brief_data={"type": "out_of_scope", "summary": "Khách hỏi về thời tiết."},
        ticket_status=TicketStatus.CLOSED.value,
        created_at=now - timedelta(days=1),
    )
    out_of_scope.messages = [
        Message(sender="customer", channel="web_chat", content="Hôm nay Hà Nội có mưa không?"),
        Message(sender="agent", channel="web_chat",
                content="Xin lỗi, em chỉ hỗ trợ các vấn đề về xe điện và dịch vụ VinFast ạ."),
    ]

    return [sales, charging, complaint, service_waiting, service_critical, out_of_scope]


def main() -> None:
    reset = "--reset" in sys.argv
    with SessionLocal() as db:
        if reset:
            for model in (ReviewerFeedback, Message, Ticket, Case):
                db.query(model).delete()
            db.commit()
            print("Đã xóa dữ liệu cũ.")
        elif db.query(Case).count() > 0:
            print("DB đã có dữ liệu, bỏ qua. Dùng --reset để seed lại.")
            return

        cases = build_cases(datetime.now(timezone.utc))
        db.add_all(cases)
        db.commit()
        print(f"Đã seed {len(cases)} case.")


if __name__ == "__main__":
    main()