import base64
import hashlib
import hmac
import json
import time

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db import get_db
from src.models.db_models import Case, User, UserRole

SETTINGS = get_settings()
SECRET_KEY = getattr(SETTINGS, "secret_key", "vinfast-serviceflow-secret-key-2026")
SALT = "vinfast-salt-2026"


def hash_password(password: str) -> str:
    """Hash mật khẩu bằng SHA-256 kèm salt."""
    return hashlib.sha256((SALT + password).encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Xác thực mật khẩu."""
    return hash_password(plain_password) == hashed_password


def create_token(user_id: str, role: str, expires_in_seconds: int = 86400 * 7) -> str:
    """Tạo signed token cho session người dùng."""
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": int(time.time()) + expires_in_seconds,
    }
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_token(token: str) -> dict | None:
    """Giải mã và kiểm tra tính hợp lệ của token."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        # Kiểm tra chữ ký HMAC
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Thêm padding b64 nếu thiếu
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += "=" * (4 - rem)
        payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        payload = json.loads(payload_bytes.decode("utf-8"))

        if payload.get("exp", 0) < int(time.time()):
            return None  # Đã hết hạn
        return payload
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

    user = db.query(User).filter(User.id == payload["user_id"]).first()
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
        return None
    return db.query(User).filter(User.id == payload["user_id"]).first()


def require_customer(current_user: User = Depends(get_current_user)) -> User:
    """RBAC Dependency: Yêu cầu vai trò CUSTOMER (hoặc STAFF)."""
    if current_user.role not in (UserRole.CUSTOMER.value, UserRole.STAFF.value):
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


def check_case_ownership(case: Case, user: User) -> None:
    """Kiểm tra quyền sở hữu Case: Customer chỉ được xem case của mình, Staff được xem tất cả."""
    if user.role == UserRole.STAFF.value:
        return
    # Customer ownership: match user_id or mock_customer_id
    is_owner = False
    if case.user_id and case.user_id == user.id:
        is_owner = True
    elif user.mock_customer_id and case.mock_customer_id == user.mock_customer_id:
        is_owner = True

    if not is_owner:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền truy cập vào hồ sơ này.",
        )
