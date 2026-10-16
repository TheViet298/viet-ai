import hashlib
import hmac
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db import get_db
from src.models.db_models import Case, User, UserRole

LEGACY_SALT = "vinfast-salt-2026"
DEVELOPMENT_SECRET = "serviceflow-local-development-secret-not-for-production"
TOKEN_ISSUER = "vinfast-serviceflow"
_password_hasher = PasswordHasher()


def _token_secret() -> str:
    configured = get_settings().auth_secret_key.get_secret_value()
    if configured:
        return configured
    if get_settings().app_env == "production":
        raise RuntimeError("AUTH_SECRET_KEY must be configured in production")
    return DEVELOPMENT_SECRET


def hash_password(password: str) -> str:
    """Hash a password with Argon2id and a per-password random salt."""
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify current Argon2id hashes and legacy demo hashes."""
    if hashed_password.startswith("$argon2"):
        try:
            return _password_hasher.verify(hashed_password, plain_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
    # Existing demo accounts are upgraded to Argon2id at the next successful login.
    legacy_hash = hashlib.sha256((LEGACY_SALT + plain_password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy_hash, hashed_password)


def needs_password_rehash(hashed_password: str) -> bool:
    if not hashed_password.startswith("$argon2"):
        return True
    try:
        return _password_hasher.check_needs_rehash(hashed_password)
    except (VerificationError, InvalidHashError):
        return True


def create_token(user_id: str, role: str, expires_in_seconds: int = 86400 * 7) -> str:
    """Create an HS256 JWT. Authorization always reloads role from the database."""
    import time

    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + expires_in_seconds,
        "iss": TOKEN_ISSUER,
    }
    return jwt.encode(payload, _token_secret(), algorithm="HS256")


def verify_token(token: str) -> dict | None:
    """Decode and verify signature, issuer, expiry, and required claims."""
    try:
        return jwt.decode(
            token,
            _token_secret(),
            algorithms=["HS256"],
            issuer=TOKEN_ISSUER,
            options={"require": ["sub", "iat", "exp", "iss"]},
        )
    except Exception:
        return None


def get_token_from_header(authorization: str | None = Header(None)) -> str | None:
    """Trích xuất Bearer token từ Authorization Header."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user(
    token: str | None = Depends(get_token_from_header),
    db: Session = Depends(get_db),
) -> User:
    """Dependency bắt buộc: lấy thông tin User hiện tại từ Token."""
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Chưa đăng nhập. Vui lòng đăng nhập tài khoản để tiếp tục.",
        )
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.",
        )

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Người dùng không tồn tại trên hệ thống.",
        )
    return user


def get_optional_user(
    token: str | None = Depends(get_token_from_header),
    db: Session = Depends(get_db),
) -> User | None:
    """Dependency tùy chọn: lấy thông tin User nếu có token, ngược lại trả về None."""
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired bearer token")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return user


def require_customer(current_user: User = Depends(get_current_user)) -> User:
    """Require a customer account; staff preview uses the separate agent chat."""
    if current_user.role != UserRole.CUSTOMER.value:
        raise HTTPException(
            status_code=403,
            detail="Chức năng chỉ dành cho Khách hàng đã đăng nhập.",
        )
    return current_user


def require_staff(current_user: User = Depends(get_current_user)) -> User:
    """RBAC Dependency: Yêu cầu vai trò STAFF."""
    if current_user.role != UserRole.STAFF.value:
        raise HTTPException(
            status_code=403,
            detail="Từ chối truy cập: Chức năng chỉ dành cho Nhân viên Dịch vụ (Staff).",
        )
    return current_user


def is_demo_user(db: Session, user: User | None) -> bool:
    """Đọc cờ is_demo chuẩn xác từ database theo user.id, không tin JWT client."""
    if not user:
        return False
    db_user = db.get(User, user.id)
    if db_user:
        return bool(db_user.is_demo)
    return bool(getattr(user, "is_demo", False))


def scoped_cases(db: Session, user: User | None = None):
    """
    Query Case cách ly tuyệt đối 2 chiều:
    - User/Staff thật (hoặc Guest): CHỈ thấy case thật (is_demo == False).
    - User/Staff demo: CHỈ thấy case demo (is_demo == True).
    """
    demo_flag = is_demo_user(db, user)
    return db.query(Case).filter(Case.is_demo == demo_flag)


def scoped_sessions(db: Session, user: User | None = None):
    """
    Query ChatSession cách ly tuyệt đối 2 chiều:
    - User thật (hoặc Guest): CHỈ thấy session thật (is_demo == False).
    - User demo: CHỈ thấy session demo (is_demo == True).
    """
    from src.models.db_models import ChatSession

    demo_flag = is_demo_user(db, user)
    return db.query(ChatSession).filter(ChatSession.is_demo == demo_flag)


def check_case_ownership(case: Case, user: User | None = None, session_id: str | None = None) -> None:
    """
    Xác thực quyền sở hữu hồ sơ sự cố (Chống triệt để lỗ hổng IDOR và cách ly 2 chiều Demo/Real).
    Quy tắc:
    1. Cách ly 2 chiều is_demo:
       - user.is_demo phải khớp case.is_demo (Guest coi như is_demo=False).
       - Khi khác is_demo: Trả 404 Not Found (chặn rò rỉ ID giữa môi trường demo và thật).
    2. Phân quyền vai trò:
       - Nhân viên (STAFF): Toàn quyền truy cập ca trong cùng phân vùng is_demo.
       - Khách hàng đã đăng nhập (CUSTOMER): Phải khớp định danh `case.user_id == user.id`.
       - Khách hàng dùng thử (Guest): Phải khớp `case.session_id == session_id` và case.is_demo == False.
       - Nếu sai ownership: Trả 403 Forbidden.
    """
    user_is_demo = bool(getattr(user, "is_demo", False)) if user else None
    case_is_demo = bool(getattr(case, "is_demo", False))

    # Cách ly 2 chiều khi có thông tin người dùng: khác phân vùng demo/thật trả 404 Not Found
    if user is not None and user_is_demo != case_is_demo:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy hồ sơ sự cố yêu cầu.",
        )

    if user and user.role == UserRole.STAFF.value:
        return

    is_owner = False
    if user and case.user_id and case.user_id == user.id:
        is_owner = True
    elif session_id and case.session_id and case.session_id == session_id:
        is_owner = True

    if not is_owner:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền truy cập vào hồ sơ này.",
        )
