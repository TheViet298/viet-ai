from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from src.db import get_db
from src.models.db_models import Case

router = APIRouter(prefix="/cases", tags=["cases-legacy"])


@router.get("")
def list_cases(
    status: str | None = None,
    priority: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """API lấy danh sách case (Tương thích ngược)."""
    q = db.query(Case).options(joinedload(Case.brief))
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
def get_case(case_id: str, db: Session = Depends(get_db)):
    """API lấy chi tiết một case theo ID chuỗi (CASE-YYYYMMDD-XXX)."""
    case = db.query(Case).options(joinedload(Case.brief), joinedload(Case.messages)).filter(Case.id == case_id).first()
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
