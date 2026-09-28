from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import Intent, Priority, ReviewAction, SourceChannel, TicketStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Message ----------
class MessageCreate(BaseModel):
    sender: Literal["customer", "agent", "reviewer"]
    content: str = Field(min_length=1)
    channel: SourceChannel | None = None


class MessageOut(ORMModel):
    id: int
    case_id: int
    sender: str
    channel: str | None
    content: str
    created_at: datetime


# ---------- Ticket / Reviewer feedback ----------
class TicketOut(ORMModel):
    id: int
    case_id: int
    assigned_department: str | None
    dispatched_at: datetime | None
    closed_at: datetime | None
    created_at: datetime


class FeedbackOut(ORMModel):
    id: int
    case_id: int
    reviewer_name: str | None
    action: str
    edited_brief: dict | None
    final_routing: str | None
    comment: str | None
    created_at: datetime


# ---------- Case ----------
class CaseCreate(BaseModel):
    source_channel: SourceChannel
    customer_ref: str | None = None
    content: str = Field(min_length=1, description="Tin nhắn đầu tiên của khách")


class CaseUpdate(BaseModel):
    """Agent gọi PATCH để ghi kết quả phân loại/brief. Chỉ field nào gửi lên mới được cập nhật."""

    intent: Intent | None = None
    priority: Priority | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    suggested_routing: str | None = None
    brief_data: dict | None = None
    ticket_status: TicketStatus | None = None


class CaseSummary(ORMModel):
    id: int
    source_channel: str
    customer_ref: str | None
    intent: str | None
    priority: str | None
    confidence: float | None
    suggested_routing: str | None
    ticket_status: str
    created_at: datetime
    updated_at: datetime


class CaseDetail(CaseSummary):
    brief_data: dict | None
    messages: list[MessageOut]
    tickets: list[TicketOut]
    feedbacks: list[FeedbackOut]


# ---------- Review ----------
class ReviewCreate(BaseModel):
    action: ReviewAction
    reviewer_name: str | None = None
    final_routing: str | None = Field(
        default=None, description="Bộ phận nhận. Bỏ trống thì dùng suggested_routing của case"
    )
    edited_brief: dict | None = Field(
        default=None, description="Bắt buộc khi action = edit"
    )
    comment: str | None = None