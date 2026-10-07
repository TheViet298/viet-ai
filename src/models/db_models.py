import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


def utcnow() -> datetime:
    """Trả về thời gian hiện tại chuẩn UTC."""
    return datetime.now(UTC)


# ==============================================================================
# ENUMS — Nguồn chân lý: docs/architecture/data-model.md & ADR-005
# ==============================================================================


class UserRole(StrEnum):
    """Vai trò người dùng trong hệ thống (RBAC theo auth-and-rbac.md & ADR-005)."""

    GUEST = "GUEST"
    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"


class AttachmentStatus(StrEnum):
    """Trạng thái xử lý file đính kèm/ảnh táp-lô theo ADR-004."""

    UPLOADED = "UPLOADED"
    ANALYZED = "ANALYZED"
    FAILED = "FAILED"


class LocationStatus(StrEnum):
    """Trạng thái chia sẻ vị trí của khách hàng (ADR-005)."""

    CONSENTED = "CONSENTED"
    MANUAL = "MANUAL"
    NOT_SHARED = "NOT_SHARED"
    UNKNOWN = "UNKNOWN"


class LocationSource(StrEnum):
    """Nguồn thu thập vị trí."""

    BROWSER_GPS = "BROWSER_GPS"
    USER_TEXT = "USER_TEXT"
    MAP_PICKER = "MAP_PICKER"


class LocationPrecision(StrEnum):
    """Độ chính xác của vị trí."""

    APPROXIMATE = "APPROXIMATE"
    EXACT = "EXACT"


class AuthorType(StrEnum):
    """Tác giả của bản cập nhật CaseUpdate."""

    STAFF = "STAFF"
    SYSTEM = "SYSTEM"


class ConfirmationChoice(StrEnum):
    """Lựa chọn xác nhận của khách hàng khi case Resolved."""

    RESOLVED_CONFIRMED = "RESOLVED_CONFIRMED"
    STILL_UNRESOLVED = "STILL_UNRESOLVED"


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
    """Hành động của nhân viên HITL trên Console (Cập nhật api-contract.md 3.3)."""

    APPROVE = "APPROVE"
    EDIT_BRIEF = "EDIT_BRIEF"
    REROUTE = "REROUTE"
    REQUEST_INFO = "REQUEST_INFO"
    RESOLVE = "RESOLVE"
    CLOSE = "CLOSE"
    REOPEN = "REOPEN"


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
# DATABASE MODELS — Chuẩn theo data-model.md mới nhất
# ==============================================================================


class User(Base):
    """
    Bảng users: Quản lý người dùng cho Web Support Hub (RBAC).
    Chỉ cho phép đăng ký Customer; Staff dùng tài khoản seed/invite.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.CUSTOMER.value)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vehicle_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mock_customer_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    cases: Mapped[list["Case"]] = relationship(back_populates="user")


class Case(Base):
    """
    Bảng cases: Lưu trữ hồ sơ sự cố / ticket hỗ trợ.
    Khóa chính id là dạng chuỗi 'CASE-YYYYMMDD-XXX' (không dùng số nguyên tự tăng).
    Tuân thủ No-PII: chỉ lưu mock_customer_id, vehicle_code_mock, session_id.
    """

    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # e.g. CASE-20260924-001
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mock_customer_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. CUST_MOCK_01
    mock_customer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Demo seed only
    mock_customer_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Demo seed only
    vehicle_code_mock: Mapped[str | None] = mapped_column(String(50), nullable=True)  # format VF-SF-xxxxx
    vehicle_model: Mapped[str | None] = mapped_column(String(50), nullable=True)  # VF3 | VF5 | VF6...
    intent: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default=Priority.MEDIUM.value)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=TicketStatus.NEW.value)
    safety_status: Mapped[str] = mapped_column(String(30), nullable=False, default='unconfirmed', server_default='unconfirmed')
    safety_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    incident_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    assigned_staff_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Quan hệ với User
    user: Mapped["User | None"] = relationship(back_populates="cases")
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
    # Quan hệ 1-N với attachments
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="Attachment.created_at.asc()"
    )
    # Quan hệ 1-N với customer_feedback
    feedback: Mapped[list["CustomerFeedback"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="CustomerFeedback.created_at.desc()"
    )
    # Quan hệ 1-1 với case_locations (ADR-005)
    location: Mapped["CaseLocation | None"] = relationship(
        back_populates="case", cascade="all, delete-orphan", uselist=False
    )
    # Quan hệ 1-N với case_updates (ADR-005)
    updates: Mapped[list["CaseUpdate"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="CaseUpdate.created_at.asc()"
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


class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    memory_states: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default='{}')


class ChatRequestRecord(Base):
    __tablename__ = 'chat_request_records'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response: Mapped[dict] = mapped_column(JSON, nullable=False)


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
    action: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # APPROVE | EDIT_BRIEF | REROUTE | RESOLVE | CLOSE...
    previous_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["Case"] = relationship(back_populates="audit_logs")


class Attachment(Base):
    """
    Bảng attachments: Lưu trữ thông tin ảnh đính kèm (ảnh táp-lô, đèn báo, trụ sạc).
    Lưu trữ riêng tư (private path), chỉ trích xuất tín hiệu sơ bộ qua OCR/Vision.
    """

    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # e.g. ATT-20260930-001 or UUID
    case_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("cases.id"), nullable=True, index=True)
    message_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("messages.id"), nullable=True, index=True)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)  # Đường dẫn file riêng tư
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False, default="image/jpeg")
    analysis_status: Mapped[str] = mapped_column(String(20), nullable=False, default=AttachmentStatus.UPLOADED.value)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_signals: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    vision_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["Case | None"] = relationship(back_populates="attachments")
    message: Mapped["Message | None"] = relationship()


class CustomerFeedback(Base):
    """
    Bảng customer_feedback: Lưu trữ đánh giá của khách hàng sau khi case được giải quyết.
    """

    __tablename__ = "customer_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("cases.id"), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5 sao
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["Case"] = relationship(back_populates="feedback")


class CaseLocation(Base):
    """
    Bảng case_locations: Lưu vị trí sự cố khi khách hàng đồng ý (consent) hoặc tự nhập (ADR-005).
    Tuyệt đối không tự động đọc vị trí từ EXIF ảnh.
    """

    __tablename__ = "case_locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("cases.id"), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=LocationStatus.NOT_SHARED.value)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default=LocationSource.USER_TEXT.value)
    location_label: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision: Mapped[str] = mapped_column(String(20), nullable=False, default=LocationPrecision.APPROXIMATE.value)
    share_with_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["Case"] = relationship(back_populates="location")


class CaseUpdate(Base):
    """
    Bảng case_updates: Lưu các cập nhật tiến độ an toàn gửi tới Customer (ADR-005).
    """

    __tablename__ = "case_updates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("cases.id"), nullable=False, index=True)
    author_type: Mapped[str] = mapped_column(String(20), nullable=False, default=AuthorType.STAFF.value)
    status_after_update: Mapped[str] = mapped_column(String(30), nullable=False)
    customer_message: Mapped[str] = mapped_column(Text, nullable=False)
    next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    awaiting_customer_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["Case"] = relationship(back_populates="updates")
