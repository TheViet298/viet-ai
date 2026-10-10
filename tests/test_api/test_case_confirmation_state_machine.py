import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from datetime import UTC, datetime

from src.db import Base, get_db
from src.main import app
from src.models.db_models import Case, TicketStatus, User, Priority, Intent
from src.services.auth import create_token

@pytest.fixture
def state_machine_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'state_machine.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(id="cust-sm-1", username="cust_sm@vinfast.vn", password_hash="hash", role="CUSTOMER")
        db.add(user)
        db.commit()

        case = Case(
            id="CASE-SM-001",
            user_id="cust-sm-1",
            session_id="sess-sm-1",
            vehicle_model="VF8",
            intent=Intent.SERVICE_INCIDENT.value,
            priority=Priority.HIGH.value,
            status=TicketStatus.STAFF_REVIEWING.value,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(case)
        db.commit()

        app.dependency_overrides[get_db] = lambda: db
        yield db, case
    app.dependency_overrides.clear()
    engine.dispose()

@pytest.mark.asyncio
async def test_cannot_confirm_case_when_staff_reviewing(client, state_machine_db):
    db, case = state_machine_db
    token = create_token(user_id="cust-sm-1", role="CUSTOMER")
    headers = {"Authorization": f"Bearer {token}"}

    # Case đang ở Staff Reviewing -> không được phép xác nhận đóng
    res = await client.post(
        f"/api/v1/customer/cases/{case.id}/confirmation",
        headers=headers,
        json={"confirmation": "RESOLVED_CONFIRMED", "feedback_note": "Tự đóng"},
    )
    assert res.status_code == 409
    assert "Resolved" in res.text

@pytest.mark.asyncio
async def test_cannot_confirm_via_actions_endpoint_when_in_progress(client, state_machine_db):
    db, case = state_machine_db
    token = create_token(user_id="cust-sm-1", role="CUSTOMER")
    headers = {"Authorization": f"Bearer {token}"}

    case.status = TicketStatus.IN_PROGRESS.value
    db.commit()

    res = await client.post(
        f"/api/v1/customer/cases/{case.id}/actions",
        headers=headers,
        json={"action": "CONFIRM_RESOLUTION", "feedback_note": "Tự đóng khi đang xử lý"},
    )
    assert res.status_code == 409
    assert "Resolved" in res.text

@pytest.mark.asyncio
async def test_can_confirm_resolution_when_resolved(client, state_machine_db):
    db, case = state_machine_db
    token = create_token(user_id="cust-sm-1", role="CUSTOMER")
    headers = {"Authorization": f"Bearer {token}"}

    case.status = TicketStatus.RESOLVED.value
    db.commit()

    res = await client.post(
        f"/api/v1/customer/cases/{case.id}/confirmation",
        headers=headers,
        json={"confirmation": "RESOLVED_CONFIRMED", "feedback_note": "Hài lòng"},
    )
    assert res.status_code == 200
    db.refresh(case)
    assert case.status == TicketStatus.CLOSED.value
