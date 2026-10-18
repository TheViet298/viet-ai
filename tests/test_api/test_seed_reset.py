import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, ensure_schema
from src.models.db_models import Case, Priority, ServicePoint, TicketStatus, User, UserRole, utcnow
from src.seed import reset_demo_data, seed_database


def test_seed_reset_preserves_service_points_and_real_cases(tmp_path):
    db_file = tmp_path / "test_seed_reset.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)

    from src import db as db_mod
    orig_engine = db_mod.engine
    db_mod.engine = engine
    try:
        ensure_schema()
        with Session(engine) as session:
            # 1. Thêm service_points
            sp = ServicePoint(
                id="sp_test_1",
                source_file="test",
                category="workshop",
                name="Xưởng VinFast Test",
                address="123 Test St",
                latitude=21.0,
                longitude=105.8,
                dong_son=True,
                is_car_compatible=True,
                is_visible=True,
            )
            session.add(sp)

            # 2. Thêm Real User & Real Case (is_demo=False)
            real_user = User(
                id="real_user_001",
                username="real.cust@vinfast.vn",
                password_hash="fakehash",
                role=UserRole.CUSTOMER.value,
                is_demo=False,
            )
            session.add(real_user)

            real_case = Case(
                id="REAL-CASE-001",
                user_id="real_user_001",
                session_id="session_real_001",
                mock_customer_phone="0912345678",
                vehicle_model="VF8",
                intent="Service/Incident",
                priority=Priority.MEDIUM.value,
                status=TicketStatus.NEW.value,
                is_demo=False,
            )
            session.add(real_case)

            # 3. Thêm Demo Case (is_demo=True)
            demo_case = Case(
                id="DEMO-CASE-001",
                session_id="session_demo_001",
                mock_customer_phone="0912345679",
                vehicle_model="VF9",
                intent="Service/Incident",
                priority=Priority.HIGH.value,
                status=TicketStatus.NEW.value,
                is_demo=True,
            )
            session.add(demo_case)
            session.commit()

            # Kiểm tra trước khi reset
            assert session.query(ServicePoint).count() == 1
            assert session.query(Case).filter(Case.is_demo.is_(False)).count() == 1
            assert session.query(Case).filter(Case.is_demo.is_(True)).count() == 1

            # Thực hiện reset_demo_data
            reset_demo_data(session)

            # Kiểm tra sau khi reset
            assert session.query(ServicePoint).count() == 1, "service_points KHÔNG được bị xóa"
            assert session.query(Case).filter(Case.is_demo.is_(False)).count() == 1, "Case thật (is_demo=False) KHÔNG được bị xóa"
            assert session.query(Case).filter(Case.is_demo.is_(True)).count() == 0, "Case demo (is_demo=True) phải bị xóa"

    finally:
        db_mod.engine = orig_engine
        engine.dispose()
