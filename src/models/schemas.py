from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CaseStatus(str, Enum):
    NEW = "New"
    NEEDS_INFORMATION = "Needs Information"
    STAFF_REVIEWING = "Staff Reviewing"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    REOPENED = "Reopened"


class ClientContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mock_customer_id: str | None = Field(default=None, max_length=50)
    vehicle_model: str | None = Field(default=None, max_length=50)
    vehicle_code_mock: str | None = Field(default=None, max_length=50)


class CustomerChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=8, max_length=64)
    case_id: str | None = None
    message: str = Field(min_length=1, max_length=5000)
    client_context: ClientContext = Field(default_factory=ClientContext)


class CustomerActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["CONFIRM_RESOLUTION", "REOPEN"]
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_reopen_reason(self):
        if self.action == "REOPEN" and not (self.reason or "").strip():
            raise ValueError("REOPEN requires a reason")
        return self


class CaseBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=5000)
    captured_fields: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    suggested_action: str | None = None
    suggested_routing: str | None = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    safety_flags: list[str] = Field(default_factory=list)
    is_edited_by_staff: bool = False


class StaffActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "APPROVE", "EDIT_BRIEF", "REROUTE", "REQUEST_INFO", "RESOLVE", "CLOSE", "REOPEN"
    ]
    edited_brief: CaseBrief | None = None
    notes: str | None = Field(default=None, max_length=2000)
    target_team: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.action == "EDIT_BRIEF" and self.edited_brief is None:
            raise ValueError("EDIT_BRIEF requires edited_brief")
        if self.action == "REROUTE" and not (self.target_team or "").strip():
            raise ValueError("REROUTE requires target_team")
        if self.action in {"REQUEST_INFO", "RESOLVE", "CLOSE", "REOPEN"} and not (self.notes or "").strip():
            raise ValueError(f"{self.action} requires notes")
        return self


class Envelope(BaseModel):
    success: bool
    data: Any = None
    error: dict[str, str] | None = None
    meta: dict[str, str]
