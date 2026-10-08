from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

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

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = None
    phone: str | None = None
    vehicle_model: str | None = None
    mock_customer_id: str | None = None

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    vehicle_model: str | None = None


class UserOut(BaseModel):
    id: str
    username: str
    role: Literal["CUSTOMER", "STAFF", "GUEST"]
    full_name: str | None = None
    phone: str | None = None
    vehicle_model: str | None = None
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
    vehicle_model: str | None = None
    vehicle_code_mock: str | None = None
    customer_name: str | None = None


class CustomerChatRequest(BaseModel):
    request_id: str | None = Field(default=None, min_length=1, max_length=100)
    session_id: str = Field(default="sess_default", description="Mã phiên hội thoại (No-PII)")
    case_id: str | None = None  # e.g. CASE-20260924-001, null nếu là tin nhắn đầu tiên
    message: str = Field(..., min_length=1, max_length=5000, description="Nội dung tin nhắn khách hàng")
    attachment_ids: list[str] | None = Field(default_factory=list, description="Danh sách mã file/ảnh đính kèm")
    guest_session_id: str | None = Field(default=None, description="Dùng khi chưa login (giới hạn 5 lượt)")
    client_context: ClientContext | None = Field(default=None, description="Ngữ cảnh mô phỏng (No-PII)")


class ApiResponseEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict, description="Payload dữ liệu trả về")
    error: str | None = Field(default=None, description="Thông báo lỗi nếu có")
    meta: dict[str, Any] = Field(
        default_factory=lambda: {"timestamp": datetime.now(UTC).isoformat()},
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


class EmergencyContext(BaseModel):
    case_id: str
    incident_version: int
    safety_status: str
    safety_acknowledged_at: str | None = None


class ChatResponseData(BaseModel):
    emergency_context: EmergencyContext | None = None
    safety_status: Literal['unconfirmed', 'customer_reported_safe'] = 'unconfirmed'
    safety_acknowledged_at: str | None = None
    incident_version: int | None = None
    visual_evidence: dict[str, Any] | None = None
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
    show_emergency_banner: bool = False
    request_location: bool = False
    remaining_guest_messages: int | None = None  # Số lượt chat còn lại cho Guest trial (tối đa 5)


class SessionHistoryMessageItem(BaseModel):
    id: str
    sender: Literal["CUSTOMER", "AGENT", "STAFF", "SYSTEM"]
    content: str
    timestamp: str
    response_type: Literal["CLARIFICATION", "FAQ_ANSWER", "CASE_CREATED"] | None = None
    citations: list[Citation] = Field(default_factory=list)
    suggested_replies: list[str] = Field(default_factory=list)
    safe_guidance: str | None = None
    case_id: str | None = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None


class SessionHistoryResponseData(BaseModel):
    session_id: str
    case_id: str | None = None
    messages: list[SessionHistoryMessageItem] = Field(default_factory=list)
    total: int = 0


class CustomerCaseStatusData(BaseModel):
    emergency_context: EmergencyContext | None = None
    priority: str | None = None
    safety_status: str = 'unconfirmed'
    safety_acknowledged_at: str | None = None
    incident_version: int = 1
    case_id: str
    status: str
    status_description: str | None = None
    customer_message: str | None = None
    created_at: str
    updated_at: str | None = None



class CustomerCaseItem(BaseModel):
    safety_status: str = 'unconfirmed'
    safety_acknowledged_at: str | None = None
    incident_version: int = 1
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
# LOCATION & SERVICE POINTS SCHEMAS — Nguồn: ADR-005 & api-contract.md 1.1
# ==============================================================================


class CaseLocationPayload(BaseModel):
    case_id: str
    status: Literal["CONSENTED", "MANUAL", "NOT_SHARED", "UNKNOWN"] = "CONSENTED"
    source: Literal["BROWSER_GPS", "USER_TEXT", "MAP_PICKER"] = "USER_TEXT"
    location_label: str = Field(..., min_length=1)
    latitude: float | None = None
    longitude: float | None = None
    precision: Literal["APPROXIMATE", "EXACT"] = "APPROXIMATE"
    share_with_staff: bool = True


class CaseLocationOut(BaseModel):
    case_id: str
    status: str
    source: str
    location_label: str
    latitude: float | None = None
    longitude: float | None = None
    precision: str
    share_with_staff: bool
    created_at: str


class ServicePointItem(BaseModel):
    id: str
    name: str
    category: Literal["CHARGING_STATION", "SERVICE_CENTER", "RESCUE_POST", "SHOWROOM"]
    address: str
    distance_km: float | None = None
    latitude: float
    longitude: float
    hotline: str | None = None
    operating_hours: str | None = None
    charger_types: list[str] | None = None


class ServicePointsData(BaseModel):
    case_id: str
    recommended_points: list[ServicePointItem]


# ==============================================================================
# CUSTOMER CONFIRMATION & CASE UPDATES — Nguồn: ADR-005 & api-contract.md 2.3
# ==============================================================================


class CustomerConfirmationPayload(BaseModel):
    confirmation: Literal["RESOLVED_CONFIRMED", "STILL_UNRESOLVED"]
    feedback_note: str | None = None


class CustomerConfirmationResponseData(BaseModel):
    success: bool = True
    case_id: str
    status: str
    message: str


class CustomerActionPayload(BaseModel):
    action: Literal["CONFIRM_RESOLUTION", "REOPEN"]
    reason: str | None = None
    feedback_note: str | None = None


class CustomerActionResponseData(BaseModel):
    case_id: str
    status: str
    updated_at: str | None = None
    customer_message: str | None = None



class CaseUpdateOut(BaseModel):
    id: str
    case_id: str
    author_type: Literal["STAFF", "SYSTEM"]
    status_after_update: str
    customer_message: str
    next_step: str | None = None
    awaiting_customer_confirmation: bool = False
    created_at: str


# ==============================================================================
# PUBLIC SUPPORT INSIGHTS — Nguồn: ADR-005 & api-contract.md 2.3
# ==============================================================================


class SupportInsightItem(BaseModel):
    id: str
    title: str
    category: str
    vehicle_models: list[str]
    symptom: str
    recommended_action: str
    hotline_support: str | None = None


class PublicSupportInsightsData(BaseModel):
    items: list[SupportInsightItem]
    total: int


# ==============================================================================
# STAFF API SCHEMAS — Nguồn: docs/architecture/api-contract.md Mục 3
# ==============================================================================


class TicketItem(BaseModel):
    id: str
    mock_customer_id: str
    customer_name: str | None = None
    customer_phone: str | None = None
    vehicle_model: str
    vehicle_code_mock: str | None = None
    intent: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    status: str
    missing_info_flag: bool = False
    created_at: str
    confidence_score: float
    issue_summary: str | None = None
    suggested_action: str | None = None
    has_location_consent: bool = False
    error_code_short: str | None = None


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
    safety_status: str = "unconfirmed"
    safety_acknowledged_at: str | None = None
    incident_version: int = 1
    id: str
    mock_customer_id: str
    customer_name: str | None = None
    customer_phone: str | None = None
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
    location: CaseLocationOut | None = None
    updates: list[CaseUpdateOut] = Field(default_factory=list)


class CustomerCaseDetailData(BaseModel):
    case: CustomerCaseItem
    case_brief: CaseBriefOut | None = None
    location: CaseLocationOut | None = None
    updates: list[CaseUpdateOut] = Field(default_factory=list)
    attachments: list[AttachmentOut] = Field(default_factory=list)
    conversation_history: list[ConversationItem] = Field(default_factory=list)


class SafetyAcknowledgementPayload(BaseModel):
    incident_version: int = Field(ge=1)


class SafetyAcknowledgementData(BaseModel):
    emergency_context: EmergencyContext | None = None
    case_id: str
    safety_status: str
    safety_acknowledged_at: str | None = None
    incident_version: int


class StaffActionPayload(BaseModel):
    action: Literal["APPROVE", "EDIT_BRIEF", "REROUTE", "REQUEST_INFO", "RESOLVE", "CLOSE", "REOPEN"]
    staff_id: str
    updated_status: str | None = None
    edited_brief: dict[str, Any] | None = None
    notes: str | None = None


class StaffActionResponseData(BaseModel):
    success: bool = True
    case_id: str


class StaffDashboardData(BaseModel):
    critical_count: int
    staff_reviewing_count: int
    needs_information_count: int
    resolved_today_count: int
    total_cases_count: int


class RoutingDepartmentItem(BaseModel):
    id: str
    name: str
    description: str
    contact_email: str | None = None


class RoutingDirectoryData(BaseModel):
    departments: list[RoutingDepartmentItem]
    total: int
