import re
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import timedelta
from hmac import compare_digest
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db import get_db
from src.models.db_models import Case, StaffAuditLog, User, UserRole, utcnow
from src.models.schemas import (
    ApiResponse,
    AuthResponseData,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
    UserOut,
)
from src.services.auth import (
    create_token,
    get_current_user,
    hash_password,
    needs_password_rehash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_LOGIN_WINDOW_SECONDS = 300
_LOGIN_MAX_FAILURES = 20
_login_failures: dict[str, deque[float]] = defaultdict(deque)
_login_failures_lock = Lock()


def _check_login_rate_limit(request: Request) -> str:
    client_key = request.client.host if request.client else "unknown"
    cutoff = monotonic() - _LOGIN_WINDOW_SECONDS
    with _login_failures_lock:
        failures = _login_failures[client_key]
        while failures and failures[0] < cutoff:
            failures.popleft()
        if len(failures) >= _LOGIN_MAX_FAILURES:
            raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again later.")
    return client_key


def _record_login_failure(client_key: str) -> None:
    with _login_failures_lock:
        _login_failures[client_key].append(monotonic())


def _clear_login_failures(client_key: str) -> None:
    with _login_failures_lock:
        _login_failures.pop(client_key, None)


@router.post("/login", response_model=ApiResponse[AuthResponseData])
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Đăng nhập tài khoản demo Customer hoặc Staff theo api-contract.md Mục 1.1.
    """
    client_key = _check_login_rate_limit(request)
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        _record_login_failure(client_key)
        raise HTTPException(
            status_code=401,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác.",
        )

    if needs_password_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()
        db.refresh(user)
    _clear_login_failures(client_key)

    # ── Claim Guest Cases khi đăng nhập (Audit vết rõ ràng, kiểm soát chặt IDOR) ──
    raw_claim = (payload.guest_session_id or payload.session_id or request.headers.get("x-session-id") or "").strip()
    # Kiểm tra entropy: 16-64 ký tự an toàn alphanumeric/hyphen/underscore VÀ tối thiểu 8 ký tự khác nhau (chống lặp chuỗi aaaaa... hay 1234567812345678)
    is_valid_claim = bool(
        raw_claim
        and 16 <= len(raw_claim) <= 64
        and len(set(raw_claim)) >= 8
        and re.match(r"^[a-zA-Z0-9_\-]+$", raw_claim)
    )
    if is_valid_claim and user.role == UserRole.CUSTOMER.value:
        cutoff_claim = utcnow() - timedelta(hours=72)
        # Thao tác nguyên tử có điều kiện: UPDATE ... WHERE session_id = ? AND user_id IS NULL
        # Ngăn chặn hoàn toàn race condition nếu có 2 request đăng nhập/claim gửi đến đồng thời
        rows_claimed = (
            db.query(Case)
            .filter(
                Case.session_id == raw_claim,
                Case.user_id.is_(None),
                Case.created_at >= cutoff_claim,
            )
            .update({"user_id": user.id}, synchronize_session=False)
        )
        if rows_claimed > 0:
            claimed_cases = db.query(Case).filter(Case.session_id == raw_claim, Case.user_id == user.id).all()
            for uc in claimed_cases:
                db.add(
                    StaffAuditLog(
                        id=str(uuid.uuid4()),
                        case_id=uc.id,
                        staff_id=f"CUSTOMER_{user.id}",
                        action="CLAIM_CASE",
                        # Không in chi tiết session_id vào log để tránh lộ token của phiên
                        notes=f"[AUTH_CLAIM] Khách hàng '{user.username}' liên kết quyền sở hữu hồ sơ từ phiên khách vãng lai hợp lệ.",
                        created_at=utcnow(),
                    )
                )
            db.commit()

    token = create_token(user.id, user.role)
    return ApiResponse(
        success=True,
        data=AuthResponseData(
            token=token,
            user=UserOut(
                id=user.id,
                username=user.username,
                role=user.role,
                full_name=user.full_name,
                phone=user.phone,
                vehicle_model=user.vehicle_model,
                mock_customer_id=user.mock_customer_id,
            ),
        ),
        error=None,
    )


@router.post("/register", response_model=ApiResponse[AuthResponseData])
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Đăng ký tài khoản Customer mới (auth-and-rbac.md: Chỉ tạo Customer; không public register Staff).
    """
    username = payload.username.strip()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Tên tài khoản '{username}' đã tồn tại trên hệ thống.",
        )

    # Luôn gán vai trò CUSTOMER, không cho phép đăng ký STAFF công khai.
    # mock_customer_id được gán None cho mọi tài khoản thật, chỉ tài khoản demo trong seed mới có giá trị.
    new_user = User(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=hash_password(payload.password),
        role=UserRole.CUSTOMER.value,
        full_name=payload.full_name.strip() if payload.full_name else None,
        phone=payload.phone.strip() if payload.phone else None,
        vehicle_model=payload.vehicle_model.strip() if payload.vehicle_model else None,
        mock_customer_id=None,
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Tên tài khoản '{username}' đã tồn tại trên hệ thống.") from exc
    db.refresh(new_user)

    token = create_token(new_user.id, new_user.role)
    return ApiResponse(
        success=True,
        data=AuthResponseData(
            token=token,
            user=UserOut(
                id=new_user.id,
                username=new_user.username,
                role=new_user.role,
                full_name=new_user.full_name,
                phone=new_user.phone,
                vehicle_model=new_user.vehicle_model,
                mock_customer_id=new_user.mock_customer_id,
            ),
        ),
        error=None,
    )


@router.get("/me", response_model=ApiResponse[UserOut])
def get_me(current_user: User = Depends(get_current_user)):
    """
    Lấy thông tin profile và vai trò người dùng hiện tại (api-contract.md Mục 1.1).
    """
    return ApiResponse(
        success=True,
        data=UserOut(
            id=current_user.id,
            username=current_user.username,
            role=current_user.role,
            full_name=current_user.full_name,
            phone=current_user.phone,
            vehicle_model=current_user.vehicle_model,
            mock_customer_id=current_user.mock_customer_id,
        ),
        error=None,
    )


@router.patch("/me", response_model=ApiResponse[UserOut])
def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cập nhật thông tin hồ sơ của người dùng hiện tại (họ và tên, SĐT, dòng xe).
    """
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip() or None
    if payload.phone is not None:
        current_user.phone = payload.phone.strip() or None
    if payload.vehicle_model is not None:
        current_user.vehicle_model = payload.vehicle_model.strip() or None

    db.commit()
    db.refresh(current_user)

    return ApiResponse(
        success=True,
        data=UserOut(
            id=current_user.id,
            username=current_user.username,
            role=current_user.role,
            full_name=current_user.full_name,
            phone=current_user.phone,
            vehicle_model=current_user.vehicle_model,
            mock_customer_id=current_user.mock_customer_id,
        ),
        error=None,
    )


bearer = HTTPBearer(auto_error=False)


# Re-export route dependencies for backward compatibility with existing tests
from src.api.dependencies import Principal, customer, optional_principal, staff  # noqa: E402

__all__ = ["router", "Principal", "customer", "optional_principal", "staff"]
