from __future__ import annotations

from datetime import UTC, datetime, timezone
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

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
# AUTH & RBAC SCHEMAS — Nguồn: docs/architecture/api-contract.md Mục 1.1 & auth-and-rbac.md
# ==============================================================================


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    mock_customer_id: str | None = "CUST_MOCK_01"


class UserOut(BaseModel):
    id: str
    username: str
    role: Literal["CUSTOMER", "STAFF", "GUEST"]
    mock_customer_id: str | None = None


class AuthResponseData(BaseModel):
    token: str
    user: UserOut


# ==============================================================================
# PUBLIC KNOWLEDGE / ARTICLES SCHEMAS — Nguồn: rag-and-data-sources.md Mục 5
# ==============================================================================


class ArticleItem(BaseModel):
    id: str
    title: str
    category: str
    summary: str
    content: str
    source_url: str
    verified_at: str
    applicable_models: list[str] | None = None


class PublicArticlesData(BaseModel):
    articles: list[ArticleItem]
    total: int


# ==============================================================================
# ATTACHMENT SCHEMAS — Nguồn: ADR-004 & api-contract.md Mục 1.1
# ==============================================================================


class AttachmentOut(BaseModel):
    attachment_id: str
    storage_key: str
    mime_type: str
    analysis_status: Literal["UPLOADED", "ANALYZED", "FAILED"]
    ocr_text: str | None = None
    detected_signals: dict[str, Any] | None = None
    vision_confidence: float | None = None
    created_at: str


# ==============================================================================
# LEGACY / TEMPLATE SCHEMAS (Giữ nguyên để tương thích bài test gốc của template)
# ==============================================================================


# =====================================================================
# 1. Simplified Chat Schemas (Phục vụ Demo & Lightweight Frontend)
# =====================================================================

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


class ClientContext(BaseModel):
    mock_customer_id: str | None = "CUST_MOCK_01"
    vehicle_model: str | None = "VF8"
    vehicle_code_mock: str | None = "VF-SF-00231"


class CustomerChatRequest(BaseModel):
    session_id: str = Field(default="sess_default", description="Mã phiên hội thoại (No-PII)")
    case_id: str | None = None  # e.g. CASE-20260924-001, null nếu là tin nhắn đầu tiên
    message: str = Field(..., min_length=1, max_length=5000, description="Nội dung tin nhắn khách hàng")
    attachment_ids: list[str] | None = Field(default_factory=list, description="Danh sách mã file/ảnh đính kèm")
    client_context: ClientContext | None = Field(default=None, description="Ngữ cảnh mô phỏng (No-PII)")


class ApiResponseEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict, description="Payload dữ liệu trả về")
    error: str | None = Field(default=None, description="Thông báo lỗi nếu có")
    meta: dict[str, Any] = Field(
        default_factory=lambda: {"timestamp": datetime.now(timezone.utc).isoformat()},
        description="Metadata phản hồi",
    )


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


class CustomerCaseItem(BaseModel):
    id: str
    vehicle_model: str | None = None
    vehicle_code_mock: str | None = None
    intent: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    status: str
    summary: str | None = None
    created_at: str
    updated_at: str | None = None


class CustomerCaseListData(BaseModel):
    cases: list[CustomerCaseItem]
    total: int


class CustomerFeedbackPayload(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Đánh giá từ 1 đến 5 sao")
    comment: str | None = None


class CustomerFeedbackResponseData(BaseModel):
    success: bool = True
    feedback_id: str
    case_id: str


class ReopenCaseResponseData(BaseModel):
    success: bool = True
    case_id: str
    status: str


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
    attachments: list[AttachmentOut] = Field(default_factory=list)


class StaffActionPayload(BaseModel):
    action: Literal["APPROVE", "EDIT_BRIEF", "REROUTE", "REQUEST_INFO", "RESOLVE", "CLOSE", "REOPEN"]
    staff_id: str
    updated_status: str | None = None
    edited_brief: dict[str, Any] | None = None
    notes: str | None = None


class StaffActionResponseData(BaseModel):
    success: bool = True
    case_id: str
