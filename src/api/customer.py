import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.db_models import (
    Case,
    CaseBrief,
    Intent,
    Message,
    Priority,
    SenderType,
    TicketStatus,
    utcnow,
)
from src.models.schemas import (
    ApiResponse,
    ChatResponseData,
    Citation,
    CustomerCaseStatusData,
    CustomerChatRequest,
    ServiceHandoff,
)

router = APIRouter(prefix="/customer", tags=["customer"])


def generate_case_id(db: Session) -> str:
    """Tạo mã Case chuẩn hóa dạng CASE-YYYYMMDD-XXX theo data-model.md."""
    today_str = datetime.now(UTC).strftime("%Y%m%d")
    prefix = f"CASE-{today_str}-"

    # Đếm số lượng case đã tạo trong ngày hôm nay
    count = db.query(func.count(Case.id)).filter(Case.id.like(f"{prefix}%")).scalar() or 0
    return f"{prefix}{count + 1:03d}"


@router.post("/chat", response_model=ApiResponse[ChatResponseData])
async def customer_chat(payload: CustomerChatRequest, db: Session = Depends(get_db)):
    """
    Tiếp nhận tin nhắn chat từ khách hàng:
    - Áp dụng Hard Safety Rules (CRITICAL)
    - Clarification tối đa 2 lượt kèm Quick Replies
    - Phản hồi FAQ kèm Trích dẫn nguồn
    - Sinh Case Brief và lưu vết vào Database SQLite
    """
    text = payload.message.strip()
    lower_text = text.lower()
    ctx = payload.client_context
    mock_cust_id = ctx.mock_customer_id if ctx else "CUST_MOCK_01"
    vehicle_model = (ctx.vehicle_model if ctx and ctx.vehicle_model else "VF8").upper()
    vehicle_code = ctx.vehicle_code_mock if ctx else "VF-SF-00231"

    # 1. Lưu tin nhắn của Khách hàng vào bảng messages
    cust_msg = Message(
        id=str(uuid.uuid4()),
        case_id=payload.case_id,
        session_id=payload.session_id,
        sender_type=SenderType.CUSTOMER.value,
        content=text,
        msg_metadata={"client_context": ctx.model_dump() if ctx else {}},
    )
    db.add(cust_msg)
    db.flush()

    # Đếm số lượt tương tác trong session này để kiểm soát clarification turn (Tối đa 2 lượt)
    prior_turns = (
        db.query(func.count(Message.id))
        .filter(
            Message.session_id == payload.session_id,
            Message.sender_type == SenderType.CUSTOMER.value,
        )
        .scalar()
        or 1
    )

    # 2. KIỂM TRA HARD SAFETY RULES (Bắt buộc theo triage-and-hitl-rules.md)
    # Tổ hợp 1: Từ khóa nguy hiểm trực tiếp
    danger_keywords = ["cháy", "khói", "mất phanh", "nổ lốp", "tai nạn", "kẹt chân ga", "ngập nước đến sàn"]
    is_direct_danger = any(kw in lower_text for kw in danger_keywords)

    # Tổ hợp 2: rùa vàng + điều kiện nguy hiểm (cao tốc, không kiểm soát, mất công suất, dừng giữa đường)
    has_turtle = "rùa vàng" in lower_text
    dangerous_conditions = ["cao tốc", "không kiểm soát", "giảm công suất", "dừng giữa đường", "giật"]
    is_turtle_critical = has_turtle and any(c in lower_text for c in dangerous_conditions)

    if is_direct_danger or is_turtle_critical:
        # BỎ QUA HỎI LÀM RÕ -> TẠO CASE CRITICAL NGAY LẬP TỨC
        new_case_id = payload.case_id or generate_case_id(db)
        case = db.get(Case, new_case_id)
        if not case:
            case = Case(
                id=new_case_id,
                session_id=payload.session_id,
                mock_customer_id=mock_cust_id,
                vehicle_code_mock=vehicle_code,
                vehicle_model=vehicle_model,
                intent=Intent.SERVICE_INCIDENT.value,
                priority=Priority.CRITICAL.value,
                status=TicketStatus.STAFF_REVIEWING.value,
            )
            db.add(case)
            db.flush()

        # Tạo / Cập nhật CaseBrief
        brief_summary = f"Sự cố khẩn cấp trên xe {vehicle_model}: {text}"
        suggested_action = "Kích hoạt cứu hộ khẩn cấp cao tốc và liên hệ trực tiếp khách hàng qua Hotline."
        case_brief = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case.id,
            summary=brief_summary,
            captured_fields={
                "vehicle_model": vehicle_model,
                "vehicle_code_mock": vehicle_code,
                "incident_type": "CRITICAL_SAFETY",
                "raw_trigger": "rùa vàng cao tốc / nguy cơ an toàn",
            },
            suggested_action=suggested_action,
            confidence_score=0.98,
            is_edited_by_staff=False,
        )
        db.add(case_brief)

        # Cập nhật case_id cho tin nhắn
        cust_msg.case_id = case.id

        safe_guidance = (
            "Anh/chị vui lòng bật đèn khẩn cấp (Hazard), từ từ tấp xe vào làn dừng khẩn cấp an toàn "
            "và gọi hotline cứu hộ 1900-232389."
        )
        agent_reply = (
            f"Hệ thống đã kích hoạt cảnh báo an toàn mức CRITICAL cho xe {vehicle_model}! "
            "Hồ sơ hỗ trợ khẩn cấp đã được đẩy lên đầu hàng đợi của chuyên viên dịch vụ và đội cứu hộ. "
            "Hotline cứu hộ VinFast: 1900-232389."
        )

        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=case.id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=agent_reply,
            msg_metadata={"safe_guidance": safe_guidance, "priority": Priority.CRITICAL.value},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="CASE_CREATED",
                case_id=case.id,
                status=TicketStatus.STAFF_REVIEWING.value,
                priority=Priority.CRITICAL.value,
                message=agent_reply,
                safe_guidance=safe_guidance,
            ),
            error=None,
        )

    # 3. KIỂM TRA FAQ / TRA CỨU HƯỚNG DẪN ỨNG DỤNG VINFAST (RAG FAQ)
    faq_keywords = [
        "tính năng app",
        "ứng dụng",
        "theo dõi pin",
        "đặt lịch",
        "bảo hành",
        "hướng dẫn app",
        "hướng dẫn",
        "chi phí",
        "giá",
        "bảng giá",
        "chính sách",
    ]
    is_faq = any(kw in lower_text for kw in faq_keywords)
    if is_faq and not any(kw in lower_text for kw in ["lỗi", "hỏng", "không sạc", "sự cố", "rùa vàng"]):
        agent_reply = (
            "Theo Hướng dẫn sử dụng Ứng dụng VinFast, anh/chị có thể dễ dàng quản lý tình trạng xe, "
            "kiểm tra mức pin/sạc và chủ động đặt lịch dịch vụ bảo dưỡng/sửa chữa trực tiếp trên Ứng dụng VinFast."
        )
        citations = [
            Citation(
                source_id="SRC-APP-001",
                title="Hướng dẫn sử dụng Ứng dụng VinFast",
                url="https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
                verified_at="2026-09-24",
                status_code=200,
                applicable_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"],
                source_type="OFFICIAL_APP_GUIDE",
                relevant_snippet="Khách hàng có thể theo dõi tình trạng xe, kiểm tra dung lượng pin, đặt lịch dịch vụ và theo dõi tiến độ sửa chữa trực tiếp trên ứng dụng VinFast.",
            )
        ]
        service_handoff = ServiceHandoff(
            has_app_feature=True,
            app_feature_name="Đặt lịch dịch vụ / Theo dõi xe",
            guide_url="https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
        )

        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=None,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=agent_reply,
            msg_metadata={"citations": [c.model_dump() for c in citations]},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="FAQ_ANSWER",
                message=agent_reply,
                case_id=None,
                citations=citations,
                service_handoff=service_handoff,
            ),
            error=None,
        )

    # 4. SỰ CỐ SẠC / KỸ THUẬT / CHARGING & BATTERY
    is_charging = any(kw in lower_text for kw in ["sạc", "trụ", "pin", "cc01", "bms", "không nhận sạc", "trạm"])
    has_sufficient_detail = any(kw in lower_text for kw in ["cc01", "p02", "vn-cs", "18%", "trụ p"])

    # TRƯỜNG HỢP A: ĐÃ ĐỦ DỮ KIỆN KỸ THUẬT -> TẠO CASE (Staff Reviewing)
    if is_charging and has_sufficient_detail:
        new_case_id = payload.case_id or generate_case_id(db)
        case = db.get(Case, new_case_id)
        if not case:
            case = Case(
                id=new_case_id,
                session_id=payload.session_id,
                mock_customer_id=mock_cust_id,
                vehicle_code_mock=vehicle_code,
                vehicle_model=vehicle_model,
                intent=Intent.CHARGING_BATTERY.value,
                priority=Priority.HIGH.value,
                status=TicketStatus.STAFF_REVIEWING.value,
            )
            db.add(case)
            db.flush()

        cust_msg.case_id = case.id

        # Trích xuất dữ kiện cho brief
        charger_match = re.search(r"(vn-cs-[^\s,]+|trụ\s*p\d+|p\d+)", lower_text)
        charger_id = charger_match.group(0).upper() if charger_match else "VN-CS-HN042-P02"
        error_code = "CC01" if "cc01" in lower_text else "BMS_01"

        case_brief = CaseBrief(
            id=str(uuid.uuid4()),
            case_id=case.id,
            summary=f"Xe {vehicle_model} không nhận sạc DC tại trạm, báo lỗi {error_code} tại trụ {charger_id}.",
            captured_fields={
                "vehicle_model": vehicle_model,
                "station_location": "Vincom Metropolis",
                "charger_id": charger_id,
                "error_code": error_code,
            },
            suggested_action="Kiểm tra tín hiệu giao tiếp trụ sạc từ xa hoặc cử nhân viên trạm hỗ trợ khách hàng.",
            confidence_score=0.92,
            is_edited_by_staff=False,
        )
        db.add(case_brief)

        safe_guidance = "Anh/chị vui lòng giữ xe ở vị trí đỗ an toàn và theo dõi cập nhật trên giao diện này."
        agent_reply = (
            "Hệ thống đã ghi nhận sự cố và tạo hồ sơ hỗ trợ. Thông tin sẽ được hiển thị cho nhân viên "
            "xử lý trên môi trường demo; vui lòng theo dõi cập nhật trên giao diện này."
        )

        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=case.id,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=agent_reply,
            msg_metadata={"safe_guidance": safe_guidance, "priority": Priority.HIGH.value},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="CASE_CREATED",
                case_id=case.id,
                status=TicketStatus.STAFF_REVIEWING.value,
                priority=Priority.HIGH.value,
                message=agent_reply,
                safe_guidance=safe_guidance,
            ),
            error=None,
        )

    # TRƯỜNG HỢP B: CHƯA ĐỦ DỮ KIỆN VÀ CÒN LƯỢT LÀM RÕ (Clarification Turn <= 2)
    if prior_turns < 2:
        clarification_msg = (
            f"Dạ em ghi nhận xe {vehicle_model} đang gặp trở ngại khi sạc pin. "
            "Màn hình xe có hiển thị mã lỗi (ví dụ: CC01, BMS_012) hoặc anh/chị có mã trụ sạc không ạ?"
        )
        suggested_replies = [
            "Mã lỗi CC01, trụ P02",
            "Đèn trụ nháy đỏ, không hiện mã",
            "Không thấy mã lỗi",
        ]

        agent_msg = Message(
            id=str(uuid.uuid4()),
            case_id=None,
            session_id=payload.session_id,
            sender_type=SenderType.AGENT.value,
            content=clarification_msg,
            msg_metadata={"suggested_replies": suggested_replies, "turn": prior_turns},
        )
        db.add(agent_msg)
        db.commit()

        return ApiResponse(
            success=True,
            data=ChatResponseData(
                response_type="CLARIFICATION",
                clarification_turn=prior_turns,
                max_clarification_turns=2,
                message=clarification_msg,
                suggested_replies=suggested_replies,
                case_id=None,
            ),
            error=None,
        )

    # TRƯỜNG HỢP C: SAU 2 LƯỢT VẪN THIẾU DỮ KIỆN -> TẠO CASE (Needs Information)
    new_case_id = payload.case_id or generate_case_id(db)
    case = db.get(Case, new_case_id)
    if not case:
        case = Case(
            id=new_case_id,
            session_id=payload.session_id,
            mock_customer_id=mock_cust_id,
            vehicle_code_mock=vehicle_code,
            vehicle_model=vehicle_model,
            intent=Intent.SERVICE_INCIDENT.value if not is_charging else Intent.CHARGING_BATTERY.value,
            priority=Priority.MEDIUM.value,
            status=TicketStatus.NEEDS_INFORMATION.value,
        )
        db.add(case)
        db.flush()

    cust_msg.case_id = case.id

    case_brief = CaseBrief(
        id=str(uuid.uuid4()),
        case_id=case.id,
        summary=f"Sự cố xe {vehicle_model}: {text} (Sau 2 lượt vẫn thiếu một số trường kỹ thuật cụ thể).",
        captured_fields={"vehicle_model": vehicle_model, "missing_fields": ["error_code", "station_id"]},
        suggested_action="Nhân viên kiểm tra lại thông tin hoặc nhắn yêu cầu khách bổ sung.",
        confidence_score=0.65,
        is_edited_by_staff=False,
    )
    db.add(case_brief)

    safe_guidance = "Vui lòng giữ kết nối và theo dõi cập nhật trên giao diện này."
    agent_reply = (
        "Hệ thống đã tạo hồ sơ ghi nhận. Do chưa đủ một số dữ kiện kỹ thuật, hồ sơ được chuyển sang "
        "hàng đợi nhân viên hỗ trợ; nhân viên sẽ kiểm tra hoặc yêu cầu bổ sung thông tin."
    )

    agent_msg = Message(
        id=str(uuid.uuid4()),
        case_id=case.id,
        session_id=payload.session_id,
        sender_type=SenderType.AGENT.value,
        content=agent_reply,
        msg_metadata={"safe_guidance": safe_guidance},
    )
    db.add(agent_msg)
    db.commit()

    return ApiResponse(
        success=True,
        data=ChatResponseData(
            response_type="CASE_CREATED",
            case_id=case.id,
            status=TicketStatus.NEEDS_INFORMATION.value,
            priority=Priority.MEDIUM.value,
            message=agent_reply,
            safe_guidance=safe_guidance,
        ),
        error=None,
    )


@router.get("/cases/{case_id}/status", response_model=ApiResponse[CustomerCaseStatusData])
def get_customer_case_status(case_id: str, db: Session = Depends(get_db)):
    """
    Tra cứu trạng thái hồ sơ của khách hàng theo api-contract.md Mục 2.2.
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")

    # Tạo mô tả tiến độ phù hợp với trạng thái
    status_descriptions = {
        TicketStatus.NEW.value: "Hệ thống đã tiếp nhận hồ sơ và đang đưa vào hàng đợi phân loại.",
        TicketStatus.NEEDS_INFORMATION.value: "Hồ sơ đang chờ nhân viên kiểm tra hoặc liên hệ bổ sung dữ kiện.",
        TicketStatus.STAFF_REVIEWING.value: "Chuyên viên dịch vụ đang xem xét hồ sơ và phương án xử lý.",
        TicketStatus.IN_PROGRESS.value: "Chuyên viên kỹ thuật đang kiểm tra và tiến hành xử lý sự cố.",
        TicketStatus.RESOLVED.value: "Sự cố đã được xử lý hoàn tất.",
        TicketStatus.CLOSED.value: "Hồ sơ đã được đóng thành công.",
        TicketStatus.REOPENED.value: "Hồ sơ đang được mở lại để kiểm tra bổ sung.",
    }

    status_desc = status_descriptions.get(case.status, f"Hồ sơ đang ở trạng thái {case.status}.")

    data = CustomerCaseStatusData(
        case_id=case.id,
        status=case.status,
        status_description=status_desc,
        created_at=case.created_at.isoformat() if case.created_at else utcnow().isoformat(),
        updated_at=case.updated_at.isoformat() if case.updated_at else None,
    )

    return ApiResponse(
        success=True,
        data=data,
        error=None,
    )
