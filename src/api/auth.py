"""Trusted demo-token adapter; production identity can replace this dependency."""

from dataclasses import dataclass
from hmac import compare_digest

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    id: str
    role: str


def optional_principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal | None:
    if credentials is None:
        return None
    settings = get_settings()
    for role, token in (("customer", settings.customer_demo_token), ("staff", settings.staff_demo_token)):
        if token and compare_digest(credentials.credentials.encode(), token.encode()):
            return Principal(f"{role}-demo", role)
    raise HTTPException(status_code=401, detail="Invalid bearer token")


def customer(principal: Principal | None = Depends(optional_principal)) -> Principal:
    if principal is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if principal.role != "customer":
        raise HTTPException(status_code=403, detail="Customer role required")
    return principal


def staff(principal: Principal | None = Depends(optional_principal)) -> Principal:
    if principal is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if principal.role != "staff":
        raise HTTPException(status_code=403, detail="Staff role required")
    return principal
