from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from src.db import get_db
from src.models.db_models import Case, User
from src.models.schemas import ApiResponse, ServicePointsData
from src.services.auth import get_optional_user, require_staff, scoped_cases

router = APIRouter(prefix="/cases", tags=["cases-legacy"])


@router.get("")
def list_cases(
    status: str | None = None,
    priority: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """API lấy danh sách case (Tương thích ngược - Yêu cầu xác thực Staff)."""
    q = scoped_cases(db, current_user).options(joinedload(Case.brief))
    if status:
        q = q.filter(Case.status == status)
    if priority:
        q = q.filter(Case.priority == priority.upper())
    cases = q.order_by(Case.created_at.desc()).offset(offset).limit(limit).all()

    return [
        {
            "id": c.id,
            "session_id": c.session_id,
            "mock_customer_id": c.mock_customer_id,
            "vehicle_model": c.vehicle_model,
            "vehicle_code_mock": c.vehicle_code_mock,
            "intent": c.intent,
            "priority": c.priority,
            "status": c.status,
            "summary": c.brief.summary if c.brief else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in cases
    ]


@router.get("/{case_id}")
def get_case(
    case_id: str,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """API lấy chi tiết một case theo ID chuỗi (CASE-YYYYMMDD-XXX - Yêu cầu xác thực Staff)."""
    case = scoped_cases(db, current_user).options(joinedload(Case.brief), joinedload(Case.messages)).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case không tồn tại")

    return {
        "id": case.id,
        "session_id": case.session_id,
        "mock_customer_id": case.mock_customer_id,
        "vehicle_model": case.vehicle_model,
        "vehicle_code_mock": case.vehicle_code_mock,
        "intent": case.intent,
        "priority": case.priority,
        "status": case.status,
        "brief": {
            "summary": case.brief.summary,
            "captured_fields": case.brief.captured_fields,
            "suggested_action": case.brief.suggested_action,
            "confidence_score": case.brief.confidence_score,
            "is_edited_by_staff": case.brief.is_edited_by_staff,
        }
        if case.brief
        else None,
        "messages": [
            {
                "id": m.id,
                "sender_type": m.sender_type,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in case.messages
        ],
    }


@router.get("/{case_id}/service-points", response_model=ApiResponse[ServicePointsData])
def get_case_service_points(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Lấy danh sách điểm hỗ trợ / trạm sạc / xưởng dịch vụ gợi ý theo sự cố (ADR-005).
    Truy vấn bảng service_points theo khoảng cách Haversine và phân loại theo intent / triage.
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy hồ sơ có mã {case_id}")

    from src.services.service_point_service import build_case_service_points_response

    data = build_case_service_points_response(db=db, case=case)
    return ApiResponse(
        success=True,
        data=data,
        error=None,
    )

