"""Provision one real staff account (is_demo=False) for ServiceFlow.

Usage:
    python -m src.create_staff staff@example.com
    # Or non-interactively via arguments/env:
    python -m src.create_staff --username staff@vinfast.vn --password MySecretPassword123!
    # Or reading from environment:
    STAFF_SEED_USERNAME=... STAFF_SEED_PASSWORD=... python -m src.create_staff
"""

import argparse
import os
import sys
import uuid
from getpass import getpass

from sqlalchemy.exc import IntegrityError

from src.config import get_settings
from src.db import SessionLocal, ensure_schema
from src.models.db_models import User, UserRole
from src.services.auth import hash_password


def create_or_update_staff(username: str, password: str) -> None:
    username = username.strip()
    if len(username) < 3:
        raise ValueError("username must contain at least 3 characters")
    if len(password) < 12:
        raise ValueError("staff password must contain at least 12 characters")

    ensure_schema()
    with SessionLocal() as db:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            existing.password_hash = hash_password(password)
            existing.role = UserRole.STAFF.value
            existing.is_demo = False
            db.commit()
            print(f"[create_staff] Updated existing staff account: {username} (is_demo=False)")
            return

        user = User(
            id=f"STAFF_{uuid.uuid4().hex[:8]}",
            username=username,
            password_hash=hash_password(password),
            role=UserRole.STAFF.value,
            full_name="Nhân viên Dịch vụ VinFast",
            phone="1900232389",
            vehicle_model=None,
            mock_customer_id=None,
            is_demo=False,
        )
        db.add(user)
        try:
            db.commit()
            print(f"[create_staff] Created staff account: {username} (is_demo=False)")
        except IntegrityError:
            db.rollback()
            raise ValueError(f"Username {username} already exists")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a real ServiceFlow staff account (is_demo=False)")
    parser.add_argument("pos_username", nargs="?", default=None, help="Staff login username or email")
    parser.add_argument("--username", "-u", default=None, help="Staff login username or email")
    parser.add_argument("--password", "-p", default=None, help="Staff password (min 12 chars)")
    args = parser.parse_args()

    username = args.username or args.pos_username or os.environ.get("STAFF_SEED_USERNAME")
    password = args.password or os.environ.get("STAFF_SEED_PASSWORD")

    if not username:
        if sys.stdin.isatty():
            username = input("Staff username / email: ").strip()
        else:
            parser.error("Username is required via argument or STAFF_SEED_USERNAME env var")

    if not password:
        if sys.stdin.isatty():
            password = getpass("Password (minimum 12 characters): ")
            confirmation = getpass("Confirm password: ")
            if password != confirmation:
                parser.error("Passwords do not match")
        else:
            parser.error("Password is required via --password or STAFF_SEED_PASSWORD env var")

    settings = get_settings()
    if settings.app_env == "production" and len(settings.auth_secret_key.get_secret_value()) < 32:
        parser.error("AUTH_SECRET_KEY must be configured with >=32 chars before provisioning production staff")

    try:
        create_or_update_staff(username, password)
        return 0
    except Exception as exc:
        print(f"[create_staff ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
