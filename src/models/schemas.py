from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(..., min_length=1, max_length=5000, description="Tin nhắn từ user")
    session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,64}$")
    guest_session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,64}$")
    case_id: str | None = None
    client_context: dict[str, str] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response: str = Field(..., description="Phản hồi từ agent")
    analysis: str = Field(default="", description="Phân tích nội bộ")
    session_id: str
    response_type: str
    intent: str | None = None
    priority: str = "MEDIUM"
    confidence_score: float = 0
    needs_staff_review: bool = False
    is_safety_trigger: bool = False
    is_no_source: bool = False
    citations: list[dict] = Field(default_factory=list)
    suggested_replies: list[str] = Field(default_factory=list)
    case_id: str | None = None
    ticket_status: str | None = None
    clarification_turn: int = 0
    max_clarification_turns: int = 2
    remaining_guest_messages: int = 0
    login_required: bool = False
    routing: str | None = None


class ConfirmationRequest(BaseModel):
    action: Literal["RESOLVED_CONFIRMED", "STILL_UNRESOLVED"]


class StaffActionRequest(BaseModel):
    action: Literal["APPROVE", "REQUEST_INFO", "RESOLVE", "CLOSE", "REOPEN"]


class LocationRequest(BaseModel):
    case_id: str
    status: Literal["CONSENTED", "MANUAL", "NOT_SHARED"]
    location_label: str = Field(default="", max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
