import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


def utcnow() -> datetime:
    """Trả về thời gian hiện tại chuẩn UTC."""
    return datetime.now(UTC)


# ==============================================================================
# ENUMS — Nguồn chân lý: docs/architecture/data-model.md & triage-and-hitl-rules.md
# ==============================================================================


class TicketStatus(StrEnum):
    """
    Vòng đời trạng thái Ticket chuẩn hóa (Duy nhất 7 trạng thái).
    Quy định: Tuyệt đối không dùng các tên trạng thái khác nhau giữa UI, Backend, DB.
    New -> Needs Information -> Staff Reviewing -> In Progress -> Resolved -> Closed (và Reopened)
    """

    NEW = "New"
    NEEDS_INFORMATION = "Needs Information"
    STAFF_REVIEWING = "Staff Reviewing"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    REOPENED = "Reopened"


class Priority(StrEnum):
    """Mức độ ưu tiên chuẩn hóa (Chữ HOA)."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Intent(StrEnum):
    """4 nhóm phân loại Intent theo đặc tả."""

    CHARGING_BATTERY = "Charging/Battery"
    SERVICE_INCIDENT = "Service/Incident"
    SALES_GENERAL_INFO = "Sales/General Info"
    COMPLAINT_FEEDBACK = "Complaint/Feedback"
    # Giữ alias ngắn gọn để tương thích khi FE/triage gửi chuỗi rút gọn
    SALES = "Sales"
    COMPLAINT = "Complaint"


class SenderType(StrEnum):
    """Người gửi tin nhắn."""

    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"
    STAFF = "STAFF"
    SYSTEM = "SYSTEM"


class StaffAction(StrEnum):
    """Hành động của nhân viên HITL trên Console."""

    APPROVE = "APPROVE"
    EDIT_BRIEF = "EDIT_BRIEF"
    REROUTE = "REROUTE"
    CLOSE = "CLOSE"
    REOPEN = "REOPEN"
    REQUEST_INFO = "REQUEST_INFO"


class VehicleModel(StrEnum):
    """Các dòng xe điện VinFast hỗ trợ."""

    VF3 = "VF3"
    VF5 = "VF5"
    VF6 = "VF6"
    VF7 = "VF7"
    VF8 = "VF8"
    VF9 = "VF9"
    E34 = "e34"


# ==============================================================================
# DATABASE MODELS — 4 bảng chuẩn theo data-model.md
# ==============================================================================


class Case(Base):
    """
    Bảng cases: Lưu trữ hồ sơ sự cố / ticket hỗ trợ.
    Khóa chính id là dạng chuỗi 'CASE-YYYYMMDD-XXX' (không dùng số nguyên tự tăng).
    Tuân thủ No-PII: chỉ lưu mock_customer_id, vehicle_code_mock, session_id.
    """

    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # e.g. CASE-20260924-001
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mock_customer_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. CUST_MOCK_01
    mock_customer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Demo seed only
    mock_customer_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Demo seed only
    vehicle_code_mock: Mapped[str | None] = mapped_column(String(50), nullable=True)  # format VF-SF-xxxxx
    vehicle_model: Mapped[str | None] = mapped_column(String(50), nullable=True)  # VF3 | VF5 | VF6...
    intent: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default=Priority.MEDIUM.value)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=TicketStatus.STAFF_REVIEWING.value)
    assigned_staff_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Quan hệ 1-N với messages
    messages: Mapped[list["Message"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="Message.created_at.asc()"
    )
    # Quan hệ 1-1 với case_briefs
    brief: Mapped["CaseBrief | None"] = relationship(back_populates="case", cascade="all, delete-orphan", uselist=False)
    # Quan hệ 1-N với staff_audit_logs
    audit_logs: Mapped[list["StaffAuditLog"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="StaffAuditLog.created_at.desc()"
    )


class Message(Base):
    """
    Bảng messages: Lưu lịch sử hội thoại giữa khách hàng, agent và nhân viên.
    Khóa chính id là UUID dạng string.
    """

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("cases.id"), nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # CUSTOMER | AGENT | STAFF | SYSTEM
    content: Mapped[str] = mapped_column(Text, nullable=False)
    msg_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)  # Citations, quick replies...
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["Case | None"] = relationship(back_populates="messages")


class CaseBrief(Base):
    """
    Bảng case_briefs: Lưu tóm tắt sự cố kỹ thuật do AI Agent sinh ra (Quan hệ 1-1 với cases).
    Khóa chính id là UUID dạng string.
    """

    __tablename__ = "case_briefs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("cases.id"), unique=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    captured_fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # SOC, error_code, charger_id...
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.90)  # 0.0 to 1.0
    is_edited_by_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["Case"] = relationship(back_populates="brief")


class StaffAuditLog(Base):
    """
    Bảng staff_audit_logs: Ghi nhận lịch sử thao tác của nhân viên trên Console.
    Khóa chính id là UUID dạng string.
    """

    __tablename__ = "staff_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("cases.id"), nullable=False, index=True)
    staff_id: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)  # APPROVE | EDIT_BRIEF | REROUTE | CLOSE...
    previous_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["Case"] = relationship(back_populates="audit_logs")
