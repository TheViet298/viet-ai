from datetime import UTC, datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ==============================================================================
# RESPONSE ENVELOPE — Nguồn: docs/architecture/api-contract.md Mục 1
# ==============================================================================


class ApiMeta(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ApiResponse(BaseModel, Generic[T]):
    """Chuẩn envelope bắt buộc cho toàn bộ response API."""

    success: bool = True
    data: T
    error: str | None = None
    meta: ApiMeta = Field(default_factory=ApiMeta)


# ==============================================================================
# LEGACY / TEMPLATE SCHEMAS (Giữ nguyên để tương thích bài test gốc của template)
# ==============================================================================


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Tin nhắn từ user")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Phản hồi từ agent")
    analysis: str = Field(default="", description="Phân tích nội bộ")


# ==============================================================================
# CUSTOMER API SCHEMAS — Nguồn: docs/architecture/api-contract.md Mục 2
# ==============================================================================


class ClientContext(BaseModel):
    mock_customer_id: str | None = "CUST_MOCK_01"
    vehicle_model: str | None = "VF8"
    vehicle_code_mock: str | None = "VF-SF-00231"


class CustomerChatRequest(BaseModel):
    session_id: str
    case_id: str | None = None  # e.g. CASE-20260924-001, null nếu là tin nhắn đầu tiên
    message: str = Field(..., min_length=1)
    client_context: ClientContext | None = None


class Citation(BaseModel):
    source_id: str
    title: str
    url: str
    verified_at: str | None = "2026-09-24"
    status_code: int | None = 200
    applicable_models: list[str] | None = None
    source_type: str | None = "OFFICIAL_APP_GUIDE"
    relevant_snippet: str | None = None


class ServiceHandoff(BaseModel):
    has_app_feature: bool = True
    app_feature_name: str
    guide_url: str


class ChatResponseData(BaseModel):
    response_type: Literal["CLARIFICATION", "FAQ_ANSWER", "CASE_CREATED"]
    message: str
    case_id: str | None = None
    status: str | None = None  # New, Staff Reviewing, Needs Information...
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    clarification_turn: int | None = None
    max_clarification_turns: int | None = None
    suggested_replies: list[str] | None = None
    citations: list[Citation] | None = None
    service_handoff: ServiceHandoff | None = None
    safe_guidance: str | None = None


class CustomerCaseStatusData(BaseModel):
    case_id: str
    status: str
    status_description: str | None = None
    created_at: str
    updated_at: str | None = None


# ==============================================================================
# STAFF API SCHEMAS — Nguồn: docs/architecture/api-contract.md Mục 3
# ==============================================================================


class TicketItem(BaseModel):
    id: str
    mock_customer_id: str
    vehicle_model: str
    intent: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    status: str
    missing_info_flag: bool = False
    created_at: str
    confidence_score: float


class TicketQueueData(BaseModel):
    items: list[TicketItem]
    total: int


class CaseBriefOut(BaseModel):
    summary: str
    captured_fields: dict[str, Any] = Field(default_factory=dict)
    suggested_action: str | None = None
    confidence_score: float = 0.90
    is_edited_by_staff: bool = False


class ConversationItem(BaseModel):
    sender: Literal["CUSTOMER", "AGENT", "STAFF", "SYSTEM"]
    content: str
    created_at: str


class TicketDetailCase(BaseModel):
    id: str
    mock_customer_id: str
    vehicle_code_mock: str | None = None
    vehicle_model: str
    intent: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    status: str


class TicketDetailData(BaseModel):
    case: TicketDetailCase
    case_brief: CaseBriefOut
    conversation_history: list[ConversationItem]


class StaffActionPayload(BaseModel):
    action: Literal["APPROVE", "EDIT_BRIEF", "REROUTE", "CLOSE", "REOPEN", "REQUEST_INFO"]
    staff_id: str
    updated_status: str | None = None
    edited_brief: dict[str, Any] | None = None
    notes: str | None = None


class StaffActionResponseData(BaseModel):
    success: bool = True
    case_id: str
