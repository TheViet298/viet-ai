import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.db import get_db
from src.models.db_models import User, UserRole
from src.models.schemas import (
    ApiResponse,
    AuthResponseData,
    LoginRequest,
    RegisterRequest,
    UserOut,
)
from src.services.auth import (
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[AuthResponseData])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Đăng nhập tài khoản demo Customer hoặc Staff theo api-contract.md Mục 1.1.
    """
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác.",
        )

    token = create_token(user.id, user.role)
    return ApiResponse(
        success=True,
        data=AuthResponseData(
            token=token,
            user=UserOut(
                id=user.id,
                username=user.username,
                role=user.role,
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

    # Luôn gán vai trò CUSTOMER, không cho phép đăng ký STAFF công khai
    new_user = User(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=hash_password(payload.password),
        role=UserRole.CUSTOMER.value,
        mock_customer_id=payload.mock_customer_id or f"CUST_MOCK_{uuid.uuid4().hex[:4].upper()}",
    )
    db.add(new_user)
    db.commit()
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
            mock_customer_id=current_user.mock_customer_id,
        ),
        error=None,
    )
