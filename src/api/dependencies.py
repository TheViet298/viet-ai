"""Authentication dependencies shared by every API route."""

from dataclasses import dataclass

from fastapi import Depends, HTTPException

from src.models.db_models import UserRole
from src.services.auth import get_current_user, get_optional_user
from src.models.db_models import User


@dataclass(frozen=True)
class Principal:
    """Small route-facing identity backed by a real database user."""

    id: str
    role: str


def _to_principal(user: User) -> Principal:
    return Principal(id=user.id, role=user.role.lower())


def optional_principal(user: User | None = Depends(get_optional_user)) -> Principal | None:
    return _to_principal(user) if user else None


def customer(principal: Principal | None = Depends(optional_principal)) -> Principal:
    if principal is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if principal.role.lower() != UserRole.CUSTOMER.value.lower():
        raise HTTPException(status_code=403, detail="Customer role required")
    return principal


def staff(principal: Principal | None = Depends(optional_principal)) -> Principal:
    if principal is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if principal.role.lower() != UserRole.STAFF.value.lower():
        raise HTTPException(status_code=403, detail="Staff role required")
    return principal


__all__ = ["Principal", "customer", "optional_principal", "staff", "get_current_user"]
