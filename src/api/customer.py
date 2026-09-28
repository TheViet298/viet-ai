from datetime import datetime, timezone
from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.agents.graph import agent
from src.db import get_db
from src.models.db_models import Case, Message, Priority, SourceChannel, TicketStatus

router = APIRouter(prefix="/customer", tags=["customer"])


class ClientContext(BaseModel):
    mock_customer_id: str | None = "CUST_MOCK_DEMO"
    vehicle_model: str | None = "VF8"
    vehicle_code_mock: str | None = "VF-SF-00231"


class CustomerChatRequest(BaseModel):
    session_id: str
    case_id: str | None = None
    message: str = Field(..., min_length=1)
    client_context: ClientContext | None = None


class Citation(BaseModel):
    source_id: str
    title: str
    url: str
    relevant_snippet: str | None = None


class ChatResponseData(BaseModel):
    response_type: Literal["CLARIFICATION", "FAQ_ANSWER", "CASE_CREATED"]
    message: str
    case_id: str | None = None
    clarification_turn: int | None = 1
    max_clarification_turns: int | None = 3
    suggested_replies: list[str] | None = None
    citations: list[Citation] | None = None
    safe_guidance: str | None = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = "MEDIUM"
    status: str | None = "OPEN"


class ApiResponse(BaseModel):
    success: bool
    data: Any
    error: str | None = None
    meta: dict[str, Any] | None = None


def parse_case_id(case_str: str | None) -> int | None:
    if not case_str:
        return None
    digits = "".join(ch for ch in str(case_str) if ch.isdigit())
    return int(digits) if digits else None


@router.post("/chat", response_model=ApiResponse)
async def chat_with_agent(payload: CustomerChatRequest, db: Session = Depends(get_db)):
    """Tiếp nhận tin nhắn chat từ khách hàng, phân loại và lưu trữ vào SQLite."""
    text = payload.message.strip()
    lower_text = text.lower()
    ctx = payload.client_context or ClientContext()
    vehicle_model = ctx.vehicle_model or "VF8"

    # 1. Tìm hoặc tạo Case trong DB
    case = None
    parsed_id = parse_case_id(payload.case_id)
    if parsed_id:
        case = db.get(Case, parsed_id)

    if not case:
        case = Case(
            source_channel=SourceChannel.web_chat.value,
            customer_ref=ctx.mock_customer_id or "CUST_MOCK_DEMO",
            ticket_status=TicketStatus.OPEN.value,
        )
        db.add(case)
        db.flush()

    # 2. Lưu tin nhắn của khách hàng vào bảng Message
    cust_msg = Message(
        case_id=case.id,
        sender="customer",
        channel="web_chat",
        content=text,
    )
    db.add(cust_msg)

    # 3. Phân loại nội dung và sinh phản hồi (kết hợp phân loại nghiệp vụ & AI agent)
    is_emergency = any(kw in lower_text for kw in ["cao tốc", "mất phanh", "rùa vàng", "cháy", "bốc khói", "tai nạn"])
    is_charging = any(kw in lower_text for kw in ["sạc", "trụ", "pin", "cc01", "không vào điện", "trạm sạc"])
    is_sales = any(kw in lower_text for kw in ["giá", "mua", "thuê pin", "ưu đãi", "lăn bánh", "đặt cọc"])

    citations = None
    safe_guidance = None
    response_priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"

    if is_emergency:
        response_type = "CASE_CREATED"
        response_priority = "CRITICAL"
        case.priority = Priority.critical.value
        case.intent = "service_incident"
        case.ticket_status = TicketStatus.PENDING_REVIEW.value
        safe_guidance = "Bật đèn cảnh báo khẩn cấp (hazard), tấp xe vào làn dừng an toàn và rời khỏi xe ngay lập tức."
        agent_reply = (
            f"Em đã ghi nhận tình huống khẩn cấp của xe {vehicle_model}! "
            "Hệ thống đã kích hoạt báo động mức ƯU TIÊN TỐI CAO và chuyển ngay thông tin đến đội phản ứng nhanh & cứu hộ."
        )
        suggested_replies = [
            "Xe đã dừng an toàn",
            "Cần xe cứu hộ ngay",
            "Đang ở trên cao tốc"
        ]
        brief_summary = f"Sự cố khẩn cấp trên xe {vehicle_model}: {text}"
        suggested_action = "Kích hoạt cứu hộ khẩn cấp và gọi trực tiếp khách hàng."

    elif is_charging:
        has_details = any(kw in lower_text for kw in ["cc01", "trụ", "p0", "p1", "vincom", "18%"])
        if has_details:
            response_type = "CASE_CREATED"
            response_priority = "HIGH"
            case.priority = Priority.high.value
            case.intent = "charging"
            case.ticket_status = TicketStatus.PENDING_REVIEW.value
            agent_reply = (
                f"Hệ thống đã ghi nhận đầy đủ dữ kiện kỹ thuật sạc của xe {vehicle_model} và lập hồ sơ hỗ trợ CASE-{case.id:04d}. "
                "Hồ sơ đã được chuyển tới chuyên viên kỹ thuật trạm sạc để xử lý."
            )
            suggested_replies = [
                "Tôi đã thử rút cáp cắm lại",
                "Trụ báo đèn đỏ",
                "Cần mở khóa cổng sạc"
            ]
            brief_summary = f"Sự cố sạc pin xe {vehicle_model}: {text}"
            suggested_action = "Kiểm tra tín hiệu handshake giao tiếp trụ sạc từ xa hoặc cử kỹ thuật viên trạm hỗ trợ."
        else:
            response_type = "CLARIFICATION"
            response_priority = "HIGH"
            case.priority = Priority.high.value
            case.intent = "charging"
            case.ticket_status = TicketStatus.WAITING_USER.value
            agent_reply = (
                f"Dạ em ghi nhận xe {vehicle_model} đang gặp trở ngại khi sạc pin. "
                "Màn hình xe có hiển thị mã lỗi (ví dụ: CC01) hoặc đèn tín hiệu trên trụ sạc báo màu gì không ạ?"
            )
            suggested_replies = [
                "Mã lỗi CC01, trụ P02",
                "Đèn trụ nháy đỏ",
                "Xe dừng hẳn, an toàn"
            ]
            brief_summary = f"Khách báo xe {vehicle_model} sạc không vào (đang làm rõ mã lỗi/trụ sạc)."
            suggested_action = "Làm rõ mã lỗi sạc trước khi dispatch kỹ thuật."

        citations = [
            Citation(
                source_id="HD-SAC-01",
                title="Cẩm nang xử lý sự cố sạc trụ công cộng VinFast",
                url="https://vinfastauto.com/vn-vi/huong-dan-sac",
                relevant_snippet="Kiểm tra trạng thái đèn LED trên trụ sạc và đảm bảo chốt khóa cổng sạc đã khớp hoàn toàn."
            )
        ]

    elif is_sales:
        response_type = "FAQ_ANSWER"
        response_priority = "LOW"
        case.priority = Priority.low.value
        case.intent = "sales"
        case.ticket_status = TicketStatus.ROUTED.value
        agent_reply = (
            f"Dạ em đã ghi nhận nhu cầu tư vấn xe {vehicle_model}. "
            "Thông tin đã được chuyển tiếp đến đội ngũ Chuyên viên Bán hàng VinFast gần nhất để liên hệ hỗ trợ báo giá và lái thử ạ."
        )
        suggested_replies = [
            "Chính sách thuê pin",
            "Bảng giá lăn bánh",
            "Đăng ký lái thử"
        ]
        brief_summary = f"Tư vấn bán hàng xe {vehicle_model}: {text}"
        suggested_action = "Bộ phận Sales liên hệ tư vấn bảng giá và chương trình ưu đãi."

    else:
        # Gọi LangGraph agent để phân tích
        try:
            agent_res = await agent.ainvoke({"query": text})
            llm_text = agent_res.get("response", "")
        except Exception:
            llm_text = ""

        response_type = "FAQ_ANSWER"
        response_priority = "MEDIUM"
        case.priority = Priority.medium.value
        case.intent = "service_incident"
        case.ticket_status = TicketStatus.PENDING_REVIEW.value
        agent_reply = (
            llm_text
            if llm_text
            else f"Dạ em đã ghi nhận thông tin yêu cầu của anh/chị về xe {vehicle_model}. "
                 f"Hồ sơ hỗ trợ CASE-{case.id:04d} đã được tạo và gửi đến bộ phận Chăm sóc Khách hàng VinFast."
        )
        suggested_replies = [
            "Tra cứu trạm bảo hành gần nhất",
            "Gặp tổng đài viên",
            "Cập nhật thêm thông tin"
        ]
        brief_summary = f"Yêu cầu hỗ trợ dịch vụ xe {vehicle_model}: {text}"
        suggested_action = "Chuyên viên dịch vụ kiểm tra lịch sử xe và liên hệ hỗ trợ."

    # Cập nhật brief_data trong DB
    case.confidence = 0.92
    case.brief_data = {
        "vehicle_model": vehicle_model,
        "summary": brief_summary,
        "suggested_action": suggested_action,
        "confidence_score": 0.92,
        "captured_fields": {
            "vehicle_model": vehicle_model,
            "vehicle_code_mock": ctx.vehicle_code_mock or f"VF-{vehicle_model}-8899",
            "mock_customer_id": ctx.mock_customer_id or "CUST_MOCK_DEMO",
            "session_id": payload.session_id,
        }
    }

    # 4. Lưu phản hồi của Agent vào bảng Message
    agent_msg = Message(
        case_id=case.id,
        sender="agent",
        channel="web_chat",
        content=agent_reply,
    )
    db.add(agent_msg)
    db.commit()
    db.refresh(case)

    data = ChatResponseData(
        response_type=response_type,
        message=agent_reply,
        case_id=f"CASE-{case.id:04d}",
        clarification_turn=1,
        max_clarification_turns=3,
        suggested_replies=suggested_replies,
        citations=citations,
        safe_guidance=safe_guidance,
        priority=response_priority,
        status=case.ticket_status,
    )

    return ApiResponse(
        success=True,
        data=data,
        error=None,
        meta={"timestamp": datetime.now(timezone.utc).isoformat()}
    )


@router.get("/cases/{case_id}/status", response_model=ApiResponse)
def get_customer_case_status(case_id: str, db: Session = Depends(get_db)):
    """Tra cứu trạng thái của Case cho khách hàng."""
    parsed_id = parse_case_id(case_id)
    if not parsed_id:
        raise HTTPException(status_code=400, detail="Mã hồ sơ không hợp lệ")

    case = db.get(Case, parsed_id)
    if not case:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ")

    return ApiResponse(
        success=True,
        data={
            "case_id": f"CASE-{case.id:04d}",
            "status": case.ticket_status,
            "priority": (case.priority or "medium").upper(),
            "updated_at": case.updated_at.isoformat() if case.updated_at else None,
        },
        error=None
    )
