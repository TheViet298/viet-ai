import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from src.db import SessionLocal
from src.models.db_models import (
    AuthorType,
    Case,
    CaseUpdate,
    StaffAction,
    StaffAuditLog,
    TicketStatus,
    utcnow,
)

logger = logging.getLogger("case_lifecycle")

AUTO_CLOSE_HOURS = 72  # 72 giờ (3 ngày) chuẩn cho khách hàng xe điện


def process_auto_close_expired_cases(db: Session, expired_hours: int = AUTO_CLOSE_HOURS) -> int:
    """
    Quét và tự động đóng các ca đã ở trạng thái Resolved quá `expired_hours` giờ
    mà khách hàng không có phản hồi xác nhận hay khiếu nại thêm.
    Ghi vết rõ ràng: StaffAuditLog và CaseUpdate với nhãn [SYSTEM AUTO-CLOSE].
    """
    now_utc = utcnow()
    cutoff_time = now_utc - timedelta(hours=expired_hours)

    expired_cases = (
        db.query(Case)
        .filter(Case.status == TicketStatus.RESOLVED.value, Case.updated_at < cutoff_time)
        .all()
    )

    if not expired_cases:
        return 0

    closed_count = 0
    for ec in expired_cases:
        # Thao tác Idempotent: Chỉ update khi status tại thời điểm thực thi vẫn là Resolved
        rows_affected = (
            db.query(Case)
            .filter(Case.id == ec.id, Case.status == TicketStatus.RESOLVED.value)
            .update(
                {"status": TicketStatus.CLOSED.value, "updated_at": now_utc},
                synchronize_session=False,
            )
        )
        if rows_affected > 0:
            db.add(
                StaffAuditLog(
                    id=str(uuid.uuid4()),
                    case_id=ec.id,
                    staff_id="SYSTEM_AUTO_CLOSE",
                    action=StaffAction.CLOSE.value,
                    previous_state={"status": TicketStatus.RESOLVED.value},
                    new_state={"status": TicketStatus.CLOSED.value},
                    notes=f"[SYSTEM AUTO-CLOSE] Tự động đóng hồ sơ sau {expired_hours}h không có phản hồi từ khách hàng.",
                    created_at=now_utc,
                )
            )
            db.add(
                CaseUpdate(
                    id=str(uuid.uuid4()),
                    case_id=ec.id,
                    author_type=AuthorType.SYSTEM.value,
                    status_after_update=TicketStatus.CLOSED.value,
                    customer_message=f"Hồ sơ sự cố đã được hệ thống tự động lưu trữ và đóng sau {expired_hours} giờ không có phản hồi thêm.",
                    next_step="Quý khách có thể yêu cầu mở lại nếu sự cố phát sinh trở lại.",
                    awaiting_customer_confirmation=False,
                    created_at=now_utc,
                )
            )
            closed_count += 1

    if closed_count > 0:
        db.commit()
        logger.info(f"[AUTO-CLOSE] Đã tự động đóng {closed_count} hồ sơ Resolved quá hạn {expired_hours}h.")
    return closed_count


async def auto_close_background_loop(interval_seconds: int = 600):
    """
    Vòng lặp job nền chạy định kỳ (mặc định mỗi 10 phút) độc lập với thao tác của Staff.
    Được bọc try/except toàn diện để không bao giờ bị dừng đột ngột bởi lỗi ngoại lệ.
    """
    logger.info(f"[AUTO-CLOSE WORKER] Khởi động job nền tự động đóng hồ sơ (quét mỗi {interval_seconds}s, hạn {AUTO_CLOSE_HOURS}h).")
    while True:
        try:
            db = SessionLocal()
            try:
                process_auto_close_expired_cases(db, AUTO_CLOSE_HOURS)
            finally:
                db.close()
        except asyncio.CancelledError:
            logger.info("[AUTO-CLOSE WORKER] Job nền đã được hủy theo tín hiệu dừng server.")
            break
        except Exception as e:
            logger.exception(f"[AUTO-CLOSE WORKER ERROR] Lỗi không mong muốn trong job nền (sẽ thử lại sau {interval_seconds}s): {e}")

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("[AUTO-CLOSE WORKER] Job nền đã được hủy theo tín hiệu dừng server.")
            break
