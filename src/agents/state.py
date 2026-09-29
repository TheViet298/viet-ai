from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# =====================================================================
# Enums chuẩn hóa theo Data Model & Architecture Docs (VFO2O-18)
# =====================================================================

IntentType = Literal[
    "Charging/Battery",
    "Service/Incident",
    "Sales/General Info",
    "Complaint/Feedback",
    "Out_of_Scope",
]

PriorityLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

TicketStatus = Literal[
    "New",
    "Needs Information",
    "Staff Reviewing",
    "In Progress",
    "Resolved",
    "Closed",
    "Reopened",
]

ResponseType = Literal[
    "CLARIFICATION",
    "FAQ_ANSWER",
    "CASE_CREATED",
    "OUT_OF_SCOPE",
    "EMERGENCY_ALERT",
]


class CitationSource(TypedDict, total=False):
    """Metadata trích dẫn nguồn RAG đã được kiểm chứng."""

    source_id: str
    title: str
    url: str
    verified_at: str
    status_code: int
    applicable_models: list[str]
    source_type: str


class CaseBriefData(TypedDict, total=False):
    """Cấu trúc dữ liệu Case Brief chuẩn hóa đẩy vào Staff Queue."""

    summary: str
    vehicle_model: str | None
    station_location: str | None
    charger_id: str | None
    error_code: str | None
    warning_symbol: str | None
    captured_fields: dict[str, Any]
    suggested_action: str
    confidence_score: float
    is_edited_by_staff: bool


class GuardrailAuditFlags(TypedDict, total=False):
    """Trạng thái ghi nhận các tầng Guardrails."""

    pii_detected_and_masked: bool
    masked_pii_types: list[str]
    hard_safety_triggered: bool
    safety_rule_name: str | None
    clarification_limit_reached: bool
    low_confidence_escalated: bool
    sentiment_sensitive_escalated: bool
    out_of_scope_detected: bool


class AgentState(TypedDict, total=False):
    """State schema toàn diện cho LangGraph Agent (VinFast ServiceFlow AI).

    Lưu trữ trạng thái hội thoại, kết quả triage, thông tin trích xuất,
    bản tóm tắt Case Brief và nhật ký các tầng Guardrails.
    """

    # -------------------------------------------------------------
    # 1. Tương thích ngược (Legacy / Boilerplate compatibility)
    # -------------------------------------------------------------
    query: str
    context: str
    analysis: str
    response: str
    error: str | None
    metadata: dict[str, Any]

    # -------------------------------------------------------------
    # 2. Session & Client Context (Tuyệt đối không lưu PII thật)
    # -------------------------------------------------------------
    session_id: str
    case_id: str | None
    mock_customer_id: str | None
    vehicle_model: str | None  # e.g. "VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"
    vehicle_code_mock: str | None  # e.g. "VF-SF-00231"

    # -------------------------------------------------------------
    # 3. Conversation History & Clarification Tracking
    # -------------------------------------------------------------
    messages: Annotated[list[BaseMessage], add_messages]
    latest_user_message: str
    clarification_turn: int  # 0, 1, hoặc 2
    max_clarification_turns: int  # Giới hạn cứng = 2
    suggested_replies: list[str]  # Quick replies cho Frontend

    # -------------------------------------------------------------
    # 4. Triage & Safety Classification
    # -------------------------------------------------------------
    intent: IntentType | None
    priority: PriorityLevel  # LOW, MEDIUM, HIGH, CRITICAL
    confidence_score: float  # 0.0 - 1.0
    is_critical: bool  # True nếu phát hiện cháy/nổ/mất phanh/rùa cao tốc
    safety_trigger: str | None  # e.g. SMOKE_OR_FIRE, BRAKE_FAILURE

    # -------------------------------------------------------------
    # 5. Fact Extraction & Slot Completeness
    # -------------------------------------------------------------
    captured_fields: dict[str, Any]
    missing_fields: list[str]

    # -------------------------------------------------------------
    # 6. RAG & Knowledge Grounding
    # -------------------------------------------------------------
    is_rag_query: bool
    rag_context: list[str]
    rag_citations: list[CitationSource]
    rag_similarity_score: float

    # -------------------------------------------------------------
    # 7. Case Brief & Output Formatting
    # -------------------------------------------------------------
    case_brief: CaseBriefData | None
    ticket_status: TicketStatus  # New, Needs Information, Staff Reviewing, ...
    response_type: ResponseType  # CLARIFICATION, FAQ_ANSWER, CASE_CREATED, ...
    final_response: str
    safe_guidance: str | None

    # -------------------------------------------------------------
    # 8. Guardrails Diagnostics
    # -------------------------------------------------------------
    guardrails: GuardrailAuditFlags
