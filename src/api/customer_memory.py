"""Current-principal personal facts and explicit, idempotent forget operations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.db_models import User
from src.models.schemas import ApiResponse
from src.services.auth import require_customer
from src.services.user_memory import KEYS, MemoryChange, MemorySnapshot, apply_user_memory_changes, load_user_memory

router = APIRouter(prefix='/customer/memory', tags=['customer-memory'])


@router.get('', response_model=ApiResponse[MemorySnapshot])
def get_personal_memory(current_user: User = Depends(require_customer), db: Session = Depends(get_db)):
    return ApiResponse(data=load_user_memory(db, current_user))


def _forget(keys: list[str], user: User, db: Session):
    snapshot = load_user_memory(db, user)
    result = apply_user_memory_changes(db, user, [MemoryChange(key=key, value=None, status='retracted') for key in keys],
        expected_revision=snapshot.revision, source_kind='profile', source_session_id=None, source_message_id=None)
    if result.status == 'conflict':
        db.rollback()
        raise HTTPException(409, 'Thông tin đã thay đổi ở phiên khác. Vui lòng thử lại.')
    db.commit()
    return ApiResponse(data={'deleted': keys, 'revision': result.revision})


@router.delete('', response_model=ApiResponse[dict])
async def forget_all_personal_memory(current_user: User = Depends(require_customer), db: Session = Depends(get_db)):
    from src.services.sqlite_admission import chat_writer
    async with chat_writer(db):
        return _forget(list(KEYS), current_user, db)


@router.delete('/{key}', response_model=ApiResponse[dict])
async def forget_personal_memory_key(key: str, current_user: User = Depends(require_customer), db: Session = Depends(get_db)):
    if key not in KEYS:
        raise HTTPException(400, 'Không hỗ trợ trường ghi nhớ này.')
    from src.services.sqlite_admission import chat_writer
    async with chat_writer(db):
        return _forget([key], current_user, db)
