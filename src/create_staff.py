"""Provision one staff account without exposing staff registration publicly.

Usage: python -m src.create_staff staff@example.com
The password is entered interactively and stored only as an Argon2id hash.
"""

import argparse
from getpass import getpass
import uuid

from sqlalchemy.exc import IntegrityError

from src.config import get_settings
from src.db import SessionLocal
from src.models.db_models import User, UserRole
from src.services.auth import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an internal ServiceFlow staff account")
    parser.add_argument("username", help="Staff login username or internal email")
    args = parser.parse_args()
    username = args.username.strip()
    if len(username) < 3:
        parser.error("username must contain at least 3 characters")

    password = getpass("Password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if len(password) < 12:
        parser.error("staff password must contain at least 12 characters")
    if password != confirmation:
        parser.error("passwords do not match")

    settings = get_settings()
    if settings.app_env == "production" and len(settings.auth_secret_key.get_secret_value()) < 32:
        parser.error("AUTH_SECRET_KEY must be configured before provisioning production staff")

    with SessionLocal() as db:
        if db.query(User.id).filter(User.username == username).first():
            parser.error("username already exists")
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=hash_password(password),
            role=UserRole.STAFF.value,
            mock_customer_id=None,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            parser.error("username already exists")

    print(f"Staff account created: {username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
