"""Authorized case lookup and response integrity for the customer application."""
import re
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.models.db_models import Case, CaseBrief, Message, TicketStatus, User

ACTIVE_CASE_STATUSES = tuple(s.value for s in TicketStatus if s not in (TicketStatus.RESOLVED, TicketStatus.CLOSED))


def generate_case_id(db: Session) -> str:
    # Fits existing String(32), independent of counts/deletes/concurrent requests.
    return f"CASE-{datetime.now(UTC):%Y%m%d}-{uuid4().hex[:16]}"


def resolve_authorized_active_case(db: Session, user: User | None, session_id: str, case_id: str | None, guest_session_id: str | None = None) -> Case | None:
    if case_id:
        case = db.get(Case, case_id)
        if not case:
            return None
        if not user:
            # Guest: cho phép nếu case thuộc session này hoặc không có user_id
            if case.session_id == session_id or case.user_id is None:
                pass
            else:
                # Case cũ từ localStorage thuộc user khác -> bỏ qua thay vì bắn lỗi 403 chặn chat
                return None
        elif case.user_id and case.user_id != user.id:
            raise HTTPException(403, 'Hồ sơ không thuộc khách hàng này.')
    else:
        case = None
    # Guard sessions against cross-user tampering: chỉ chặn khi người dùng A cố tình truy cập session của người dùng B khác
    if user:
        for existing in db.query(Case).filter_by(session_id=session_id).all():
            if existing.user_id and existing.user_id != user.id:
                raise HTTPException(403, 'Phiên hội thoại không thuộc khách hàng này.')
        for message in db.query(Message).filter_by(session_id=session_id, sender_type='CUSTOMER').all():
            meta = message.msg_metadata or {}
            if meta.get('user_id') and meta['user_id'] != user.id:
                raise HTTPException(403, 'Phiên hội thoại không thuộc khách hàng này.')
    if case:
        # Closed IDs supplied by a stale client cannot silently reopen a case.
        return case if case.status in ACTIVE_CASE_STATUSES else None
    return db.query(Case).filter(Case.session_id == session_id, Case.status.in_(ACTIVE_CASE_STATUSES)).order_by(Case.created_at.desc()).first()


def clean_case_references(text: str, case_id: str | None) -> str:
    text = re.sub(r'(?im)^.*(?:mã hồ sơ|ma ho so|mã case)\s*[:：].*$', '', text)
    text = re.sub(r'\bCASE-[A-Za-z0-9_-]+\b', 'hồ sơ hỗ trợ', text)
    return text.strip()


def upsert_case_brief(db: Session, **values) -> CaseBrief:
    brief = db.query(CaseBrief).filter_by(case_id=values['case_id']).first()
    if not brief:
        return CaseBrief(**values)
    if not brief.is_edited_by_staff:
        for key, value in values.items():
            if key not in {'id', 'case_id'}:
                setattr(brief, key, value)
    return brief
