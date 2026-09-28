from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourceChannel(str, Enum):
    web_chat = "web_chat"
    zalo = "zalo"
    email = "email"
    hotline_transcript = "hotline_transcript"


class Intent(str, Enum):
    sales = "sales"
    charging = "charging"
    complaint = "complaint"
    service_incident = "service_incident"
    out_of_scope = "out_of_scope"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    WAITING_USER = "WAITING_USER"
    PENDING_REVIEW = "PENDING_REVIEW"
    ROUTED = "ROUTED"
    CLOSED = "CLOSED"


class ReviewAction(str, Enum):
    approve = "approve"
    edit = "edit"
    escalate = "escalate"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_channel: Mapped[str] = mapped_column(String(30))
    customer_ref: Mapped[str | None] = mapped_column(String(100))
    intent: Mapped[str | None] = mapped_column(String(30))
    priority: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float)
    suggested_routing: Mapped[str | None] = mapped_column(String(50))
    brief_data: Mapped[dict | None] = mapped_column(JSON)
    ticket_status: Mapped[str] = mapped_column(String(20), default=TicketStatus.OPEN.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["ReviewerFeedback"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    assigned_department: Mapped[str | None] = mapped_column(String(50))
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["Case"] = relationship(back_populates="tickets")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    sender: Mapped[str] = mapped_column(String(20))  # customer | agent | reviewer
    channel: Mapped[str | None] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["Case"] = relationship(back_populates="messages")


class ReviewerFeedback(Base):
    __tablename__ = "reviewer_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    reviewer_name: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(20))  # approve | edit | escalate
    edited_brief: Mapped[dict | None] = mapped_column(JSON)
    final_routing: Mapped[str | None] = mapped_column(String(50))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped["Case"] = relationship(back_populates="feedbacks")
