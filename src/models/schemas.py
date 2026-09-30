from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# =====================================================================
# 1. Simplified Chat Schemas (Phục vụ Demo & Lightweight Frontend)
# =====================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Tin nhắn từ user")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Phản hồi từ agent")
    analysis: str = Field(default="", description="Phân tích nội bộ")
    intent: str | None = Field(default=None, description="Ý định phân loại")
    priority: str | None = Field(default=None, description="Mức độ ưu tiên")
    needs_staff_review: bool = Field(default=False, description="Cần chuyên viên duyệt")
    is_safety_trigger: bool = Field(default=False, description="Kích hoạt cảnh báo an toàn khẩn cấp")
    citations: list[dict[str, Any]] = Field(default_factory=list, description="Danh sách trích dẫn nguồn")


# =====================================================================
# 2. Envelope & Customer Schemas (Chuẩn API Contract docs/architecture/api-contract.md)
# =====================================================================

class CustomerChatRequest(BaseModel):
    session_id: str | None = Field(default=None, description="Mã phiên hội thoại (No-PII)")
    case_id: str | None = Field(default=None, description="Mã case nếu đang tiếp tục hội thoại")
    message: str = Field(..., min_length=1, max_length=5000, description="Nội dung tin nhắn khách hàng")
    attachment_ids: list[str] = Field(default_factory=list, description="Danh sách mã file/ảnh đính kèm")
    client_context: dict[str, Any] = Field(default_factory=dict, description="Ngữ cảnh mô phỏng (No-PII)")


class ApiResponseEnvelope(BaseModel):
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict, description="Payload dữ liệu trả về")
    error: str | None = Field(default=None, description="Thông báo lỗi nếu có")
    meta: dict[str, Any] = Field(
        default_factory=lambda: {"timestamp": datetime.now(timezone.utc).isoformat()},
        description="Metadata phản hồi"
    )
