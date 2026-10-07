import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.db import get_db
from src.models.db_models import (
    AuthorType,
    Case,
    CaseBrief,
    CaseUpdate,
    Message,
    Priority,
    SenderType,
    StaffAction,
    StaffAuditLog,
    TicketStatus,
    User,
    utcnow,
)
from datetime import UTC, datetime


def to_iso(dt: datetime | None) -> str:
    """Đảm bảo chuỗi ISO 8601 có timezone UTC để trình duyệt hiển thị chính xác theo giờ địa phương."""
    if not dt:
        return datetime.now(UTC).isoformat()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC).isoformat()
    return dt.isoformat()
from src.models.schemas import (
    ApiResponse,
    AttachmentOut,
    CaseBriefOut,
    CaseLocationOut,
    CaseUpdateOut,
    ConversationItem,
    RoutingDepartmentItem,
    RoutingDirectoryData,
    StaffActionPayload,
    StaffActionResponseData,
    StaffDashboardData,
    TicketDetailCase,
    TicketDetailData,
    TicketItem,
    TicketQueueData,
)
from src.services.auth import require_staff

router = APIRouter(prefix="/staff", tags=["staff"])


# ==============================================================================
# 1. STAFF DASHBOARD & ROUTING DIRECTORY — Nguồn: api-contract.md Mục 3.1.1
# ==============================================================================


@router.get("/dashboard", response_model=ApiResponse[StaffDashboardData])
def get_staff_dashboard(
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Counter demo thống kê vận hành Service Agent Console:
    Critical, Staff Reviewing, Needs Information, Resolved hôm nay, Tổng số case.
    """
    critical_count = (
        db.query(func.count(Case.id))
        .filter(Case.priority == Priority.CRITICAL.value, Case.status != TicketStatus.CLOSED.value)
        .scalar()
        or 0
    )
    staff_reviewing_count = (
        db.query(func.count(Case.id)).filter(Case.status == TicketStatus.STAFF_REVIEWING.value).scalar() or 0
    )
    needs_info_count = (
        db.query(func.count(Case.id)).filter(Case.status == TicketStatus.NEEDS_INFORMATION.value).scalar() or 0
    )
    resolved_today_count = (
        db.query(func.count(Case.id)).filter(Case.status == TicketStatus.RESOLVED.value).scalar() or 0
    )
    total_cases_count = db.query(func.count(Case.id)).scalar() or 0

    return ApiResponse(
        success=True,
        data=StaffDashboardData(
            critical_count=critical_count,
            staff_reviewing_count=staff_reviewing_count,
            needs_information_count=needs_info_count,
            resolved_today_count=resolved_today_count,
            total_cases_count=total_cases_count,
        ),
        error=None,
    )


ROUTING_DEPARTMENTS: list[RoutingDepartmentItem] = [
    RoutingDepartmentItem(
        id="DEPT_CHARGING_OPS",
        name="Charging Operations",
        description="Bộ phận Quản lý & Vận hành Mạng lưới Trụ sạc VinFast / V-GREEN toàn quốc.",
        contact_email="charging-ops@vinfast.vn",
    ),
    RoutingDepartmentItem(
        id="DEPT_SERVICE_CENTER",
        name="Service Center",
        description="Xưởng Dịch vụ, Kỹ thuật sửa chữa phần cứng và Bảo hành ô tô điện.",
        contact_email="service-tech@vinfast.vn",
    ),
    RoutingDepartmentItem(
        id="DEPT_CUSTOMER_CARE",
        name="Customer Care",
        description="Trung tâm Chăm sóc & Tiếp nhận Phản ánh Khách hàng 24/7.",
        contact_email="cskh@vinfast.vn",
    ),
    RoutingDepartmentItem(
        id="DEPT_SALES_ADVISOR",
        name="Sales Advisor",
        description="Đội ngũ Chuyên viên Tư vấn Sản phẩm, Bán hàng và Dịch vụ số.",
        contact_email="sales@vinfast.vn",
    ),
    RoutingDepartmentItem(
        id="DEPT_EMERGENCY_SUPPORT",
        name="Emergency Support Demo",
        description="Đội phản ứng nhanh & Điều phối Cứu hộ khẩn cấp trên Cao tốc / Đô thị.",
        contact_email="rescue-team@vinfast.vn",
    ),
]


@router.get("/routing-directory", response_model=ApiResponse[RoutingDirectoryData])
def get_routing_directory(
    current_user: User = Depends(require_staff),
):
    """
    Danh sách bộ phận tiếp nhận demo để Staff lựa chọn khi thực hiện Reroute (api-contract.md Mục 3.1.1).
    5 bộ phận P0: Charging Operations, Service Center, Customer Care, Sales Advisor, Emergency Support Demo.
    """
    return ApiResponse(
        success=True,
        data=RoutingDirectoryData(
            departments=ROUTING_DEPARTMENTS,
            total=len(ROUTING_DEPARTMENTS),
        ),
        error=None,
    )


# ==============================================================================
# 2. TICKET QUEUE & DETAIL APIs — Nguồn: api-contract.md Mục 3.1 & 3.2
# ==============================================================================


@router.get("/tickets", response_model=ApiResponse[TicketQueueData])
def get_ticket_queue(
    status: str | None = Query(None, description="Lọc theo trạng thái Ticket"),
    priority: str | None = Query(None, description="Lọc theo mức ưu tiên: LOW/MEDIUM/HIGH/CRITICAL"),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách Ticket trong hàng đợi Service Agent Console theo api-contract.md Mục 3.1.
    RBAC: Chỉ nhân viên (Staff) mới có quyền truy cập.
    """
    query = db.query(Case).options(joinedload(Case.brief), joinedload(Case.messages), joinedload(Case.user))

    if status and status != "ALL":
        query = query.filter(Case.status == status)

    if priority and priority != "ALL":
        query = query.filter(Case.priority == priority.upper())

    cases = query.order_by(Case.created_at.desc()).all()

    items: list[TicketItem] = []
    for c in cases:
        conf_score = c.brief.confidence_score if c.brief else 0.90
        summary: str | None = None
        suggested: str | None = None
        err_code: str | None = None
        has_loc: bool = False

        if c.brief:
            summary = c.brief.summary
            suggested = c.brief.suggested_action
            if c.brief.captured_fields:
                err_code = str(c.brief.captured_fields.get("error_code") or "") or None
                has_loc = bool(
                    c.brief.captured_fields.get("location_consent")
                    or c.brief.captured_fields.get("gps_coordinates")
                    or c.brief.captured_fields.get("station_location")
                )

        # Fallback tốt hơn nếu AI chưa tóm tắt: lấy 60 ký tự đầu của tin nhắn khách
        if not summary and c.messages:
            cust_msg = next((m.content for m in c.messages if m.sender_type == SenderType.CUSTOMER), None)
            if cust_msg:
                trimmed = cust_msg.strip().replace("\n", " ")
                summary = (trimmed[:60] + "...") if len(trimmed) > 60 else trimmed

        cust_name = (c.user.full_name if c.user and c.user.full_name else None) or c.mock_customer_name or None
        cust_phone = (c.user.phone if c.user and c.user.phone else None) or c.mock_customer_phone or None
        raw_cust_id = c.mock_customer_id or f"CUST_{c.id}"
        clean_cust_id = raw_cust_id.replace("CUST_MOCK_", "VF-CUST-") if "CUST_MOCK_" in raw_cust_id else raw_cust_id

        items.append(
            TicketItem(
                id=c.id,
                mock_customer_id=clean_cust_id,
                customer_name=cust_name,
                customer_phone=cust_phone,
                vehicle_model=c.vehicle_model or (c.user.vehicle_model if c.user else None) or "VF8",
                vehicle_code_mock=c.vehicle_code_mock,
                intent=c.intent,
                priority=c.priority,
                status=c.status,
                missing_info_flag=(c.status == TicketStatus.NEEDS_INFORMATION.value),
                created_at=to_iso(c.created_at),
                confidence_score=round(conf_score, 2),
                issue_summary=summary,
                suggested_action=suggested,
                has_location_consent=has_loc,
                error_code_short=err_code,
            )
        )

    return ApiResponse(
        success=True,
        data=TicketQueueData(items=items, total=len(items)),
        error=None,
    )


@router.get("/tickets/{case_id}", response_model=ApiResponse[TicketDetailData])
def get_ticket_detail(
    case_id: str,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Lấy chi tiết Ticket, Case Brief, Lịch sử hội thoại, Vị trí đã chia sẻ, Tiến độ cập nhật và Ảnh đính kèm (api-contract.md Mục 3.2).
    RBAC: Chỉ nhân viên (Staff) mới có quyền truy cập.
    """
    case = (
        db.query(Case)
        .options(
            joinedload(Case.brief),
            joinedload(Case.location),
            joinedload(Case.updates),
            joinedload(Case.messages),
            joinedload(Case.attachments),
            joinedload(Case.user),
        )
        .filter(Case.id == case_id)
        .first()
    )

    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")

    # Brief Data
    if case.brief:
        brief_out = CaseBriefOut(
            summary=case.brief.summary,
            captured_fields=case.brief.captured_fields or {},
            suggested_action=case.brief.suggested_action,
            confidence_score=case.brief.confidence_score,
            is_edited_by_staff=case.brief.is_edited_by_staff,
        )
    else:
        brief_out = CaseBriefOut(
            summary=f"Hồ sơ sự cố xe {case.vehicle_model or 'VF8'}",
            captured_fields={"vehicle_model": case.vehicle_model or "VF8"},
            suggested_action="Kiểm tra thông tin chi tiết và điều phối kỹ thuật.",
            confidence_score=0.90,
            is_edited_by_staff=False,
        )

    # Location Data
    loc_out: CaseLocationOut | None = None
    if case.location:
        loc_out = CaseLocationOut(
            case_id=case.location.case_id,
            status=case.location.status,
            source=case.location.source,
            location_label=case.location.location_label,
            latitude=case.location.latitude,
            longitude=case.location.longitude,
            precision=case.location.precision,
            share_with_staff=case.location.share_with_staff,
            created_at=to_iso(case.location.created_at),
        )

    # Updates Data
    updates_out: list[CaseUpdateOut] = []
    if case.updates:
        for u in case.updates:
            updates_out.append(
                CaseUpdateOut(
                    id=u.id,
                    case_id=u.case_id,
                    author_type=u.author_type,
                    status_after_update=u.status_after_update,
                    customer_message=u.customer_message,
                    next_step=u.next_step,
                    awaiting_customer_confirmation=u.awaiting_customer_confirmation,
                    created_at=to_iso(u.created_at),
                )
            )

    # Lịch sử hội thoại đầy đủ của ca (bao gồm cả tin nhắn trước khi tạo case trong cùng session)
    conv_items: list[ConversationItem] = []
    session_messages = (
        db.query(Message)
        .filter(
            (Message.case_id == case.id)
            | ((Message.session_id == case.session_id) & (Message.session_id.isnot(None)))
        )
        .order_by(Message.created_at.asc())
        .all()
    )
    for msg in session_messages:
        sender_role = msg.sender_type if msg.sender_type in ("CUSTOMER", "AGENT", "STAFF", "SYSTEM") else "SYSTEM"
        conv_items.append(
            ConversationItem(
                sender=sender_role,
                content=msg.content,
                created_at=to_iso(msg.created_at),
            )
        )

    # Danh sách ảnh đính kèm (private storage + OCR signals)
    attachment_items: list[AttachmentOut] = []
    if case.attachments:
        for att in case.attachments:
            attachment_items.append(
                AttachmentOut(
                    attachment_id=att.id,
                    storage_key=att.storage_key,
                    mime_type=att.mime_type,
                    analysis_status=att.analysis_status,
                    ocr_text=att.ocr_text,
                    detected_signals=att.detected_signals,
                    vision_confidence=att.vision_confidence,
                    created_at=to_iso(att.created_at),
                )
            )

    cust_name = (case.user.full_name if case.user and case.user.full_name else None) or case.mock_customer_name or None
    cust_phone = (case.user.phone if case.user and case.user.phone else None) or case.mock_customer_phone or None
    raw_cust_id = case.mock_customer_id or f"CUST_{case.id}"
    clean_cust_id = raw_cust_id.replace("CUST_MOCK_", "VF-CUST-") if "CUST_MOCK_" in raw_cust_id else raw_cust_id

    return ApiResponse(
        success=True,
        data=TicketDetailData(
            case=TicketDetailCase(
                id=case.id,
                mock_customer_id=clean_cust_id,
                customer_name=cust_name,
                customer_phone=cust_phone,
                vehicle_code_mock=case.vehicle_code_mock,
                vehicle_model=case.vehicle_model or (case.user.vehicle_model if case.user else None) or "VF8",
                intent=case.intent,
                priority=case.priority,
                status=case.status,
            ),
            case_brief=brief_out,
            conversation_history=conv_items,
            attachments=attachment_items,
            location=loc_out,
            updates=updates_out,
        ),
        error=None,
    )


# ==============================================================================
# 3. STAFF HITL ACTIONS API — Nguồn: api-contract.md Mục 3.3 & ADR-005
# ==============================================================================


@router.post("/tickets/{case_id}/actions", response_model=ApiResponse[StaffActionResponseData])
def handle_staff_action(
    case_id: str,
    payload: StaffActionPayload,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Thực hiện hành động HITL của nhân viên theo api-contract.md Mục 3.3:
    - APPROVE: Duyệt tóm tắt và chuyển sang 'In Progress'
    - EDIT_BRIEF: Hiệu chỉnh nội dung tóm tắt sự cố
    - REROUTE: Điều chuyển tuyến xử lý
    - REQUEST_INFO: Yêu cầu khách hàng bổ sung dữ kiện (chuyển 'Needs Information')
    - RESOLVE: Hoàn tất xử lý sự cố (chuyển 'Resolved' + gửi update chờ khách hàng xác nhận)
    - CLOSE: Đóng hồ sơ ('Closed')
    - REOPEN: Mở lại hồ sơ ('Reopened')
    Tự động ghi nhận vết thay đổi vào bảng staff_audit_logs và đồng bộ case_updates.
    """
    case = db.query(Case).options(joinedload(Case.brief)).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")

    previous_state = {
        "status": case.status,
        "priority": case.priority,
        "intent": case.intent,
        "brief_summary": case.brief.summary if case.brief else None,
    }

    new_status = case.status

    if payload.action == StaffAction.APPROVE.value:
        new_status = TicketStatus.IN_PROGRESS.value
    elif payload.action == StaffAction.RESOLVE.value:
        new_status = TicketStatus.RESOLVED.value
    elif payload.action == StaffAction.CLOSE.value:
        new_status = TicketStatus.CLOSED.value
    elif payload.action == StaffAction.REOPEN.value:
        new_status = TicketStatus.REOPENED.value
    elif payload.action == StaffAction.REQUEST_INFO.value:
        new_status = TicketStatus.NEEDS_INFORMATION.value
    elif payload.action == StaffAction.REROUTE.value:
        new_status = TicketStatus.STAFF_REVIEWING.value
    elif payload.action == StaffAction.EDIT_BRIEF.value:
        if payload.edited_brief:
            if not case.brief:
                case.brief = CaseBrief(
                    id=str(uuid.uuid4()),
                    case_id=case.id,
                    summary=payload.edited_brief.get("summary", ""),
                    captured_fields=payload.edited_brief.get("captured_fields", {}),
                    suggested_action=payload.edited_brief.get("suggested_action"),
                    confidence_score=1.0,
                    is_edited_by_staff=True,
                )
                db.add(case.brief)
            else:
                if "summary" in payload.edited_brief:
                    case.brief.summary = payload.edited_brief["summary"]
                if "captured_fields" in payload.edited_brief and isinstance(
                    payload.edited_brief["captured_fields"], dict
                ):
                    curr = dict(case.brief.captured_fields or {})
                    curr.update(payload.edited_brief["captured_fields"])
                    case.brief.captured_fields = curr
                if "suggested_action" in payload.edited_brief:
                    case.brief.suggested_action = payload.edited_brief["suggested_action"]
                case.brief.is_edited_by_staff = True

    if payload.updated_status:
        new_status = payload.updated_status

    case.status = new_status
    case.updated_at = utcnow()

    new_state = {
        "status": case.status,
        "priority": case.priority,
        "intent": case.intent,
        "brief_summary": case.brief.summary if case.brief else None,
    }

    # Ghi nhận Audit Log
    staff_display_id = (
        payload.staff_id
        if (payload.staff_id and not payload.staff_id.startswith("STAFF_LE_HOANG_QUAN"))
        else (current_user.full_name or current_user.username)
    )
    audit_entry = StaffAuditLog(
        id=str(uuid.uuid4()),
        case_id=case.id,
        staff_id=staff_display_id,
        action=payload.action,
        previous_state=previous_state,
        new_state=new_state,
        notes=payload.notes,
        created_at=utcnow(),
    )
    db.add(audit_entry)

    # Nếu action là RESOLVE: Tạo CaseUpdate với awaiting_customer_confirmation = True (ADR-005)
    if payload.action == StaffAction.RESOLVE.value or new_status == TicketStatus.RESOLVED.value:
        cust_msg = (
            payload.notes
            or "Sự cố đã được chuyên viên kỹ thuật xử lý xong. Quý khách vui lòng kiểm tra và xác nhận kết quả hỗ trợ."
        )
        case_update = CaseUpdate(
            id=str(uuid.uuid4()),
            case_id=case.id,
            author_type=AuthorType.STAFF.value,
            status_after_update=TicketStatus.RESOLVED.value,
            customer_message=cust_msg,
            next_step="Khách hàng xác nhận hài lòng hoặc yêu cầu hỗ trợ thêm.",
            awaiting_customer_confirmation=True,
            created_at=utcnow(),
        )
        db.add(case_update)
    elif payload.action == StaffAction.APPROVE.value:
        case_update = CaseUpdate(
            id=str(uuid.uuid4()),
            case_id=case.id,
            author_type=AuthorType.STAFF.value,
            status_after_update=TicketStatus.IN_PROGRESS.value,
            customer_message=payload.notes
            or "Chuyên viên kỹ thuật đã tiếp nhận hồ sơ và đang triển khai phương án xử lý.",
            next_step="Đang phối hợp bộ phận chuyên trách xử lý.",
            awaiting_customer_confirmation=False,
            created_at=utcnow(),
        )
        db.add(case_update)
    elif payload.action == StaffAction.REQUEST_INFO.value:
        case_update = CaseUpdate(
            id=str(uuid.uuid4()),
            case_id=case.id,
            author_type=AuthorType.STAFF.value,
            status_after_update=TicketStatus.NEEDS_INFORMATION.value,
            customer_message=payload.notes
            or "Chuyên viên kỹ thuật cần Quý khách bổ sung thêm thông tin về sự cố.",
            next_step="Vui lòng cung cấp thêm hình ảnh hoặc mô tả chi tiết tại khung chat.",
            awaiting_customer_confirmation=False,
            created_at=utcnow(),
        )
        db.add(case_update)

    db.commit()

    return ApiResponse(
        success=True,
        data=StaffActionResponseData(
            success=True,
            case_id=case.id,
        ),
        error=None,
    )
