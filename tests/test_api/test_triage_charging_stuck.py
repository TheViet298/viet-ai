"""
Test verifying:
- Critical case charging_stuck returns rescue_hotline and service points
- Parked / charging case preserves the new parked/charging safety guidance
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.agents.guardrails import build_emergency_safe_guidance, evaluate_hard_safety
from src.db import Base, ensure_schema
from src.models.db_models import Case, CaseBrief, CaseLocation, ServicePoint, TicketStatus, User, UserRole
from src.services.service_point_service import build_case_service_points_response, is_heavy_incident_or_needs_rescue


def test_charging_stuck_triage_and_safety_guidance(tmp_path):
    # 1. Test build_emergency_safe_guidance for parked/charging
    parked_text = "Xe VF8 của em đang cắm sạc ở trạm sạc nhưng bị kẹt súng sạc và bốc khói khét."
    guidance = build_emergency_safe_guidance(parked_text)
    assert "ngắt khẩn cấp" in guidance or "dừng phiên sạc" in guidance
    assert "tấp xe vào lề" not in guidance
    assert "1900-232389" in guidance

    # 2. Test driving keeps pull over
    driving_text = "Xe VF8 đang chạy trên cao tốc thì báo lỗi pin khẩn cấp."
    driving_guidance = build_emergency_safe_guidance(driving_text)
    assert "tấp xe vào lề" in driving_guidance

    # 3. Test service_point_service for Critical charging stuck case
    db_file = tmp_path / "triage_safety.db"
    engine = create_engine(f"sqlite:///{db_file}")
    from src import db as db_mod
    orig_engine = db_mod.engine
    db_mod.engine = engine
    try:
        ensure_schema()
        with Session(engine) as session:
            # Workshop
            sp = ServicePoint(
                id="sp_test_rescue", source_file="test", category="workshop",
                name="VinFast Workshop Rescue Test", address="Hà Nội",
                latitude=21.02, longitude=105.83, dong_son=True,
                is_car_compatible=True, is_visible=True,
            )
            session.add(sp)

            user = User(id="u_stuck", username="u_stuck", password_hash="dummy", role=UserRole.CUSTOMER.value)
            session.add(user)

            case = Case(
                id="CASE-STUCK-001",
                user_id="u_stuck",
                session_id="s_stuck",
                intent="Service/Incident",
                priority="CRITICAL",
                status=TicketStatus.NEW.value,
                safety_status="unconfirmed",
                is_demo=False,
            )
            brief = CaseBrief(
                case_id=case.id,
                summary="Xe đang sạc tại trạm bị kẹt súng sạc và phát sinh nhiệt",
                captured_fields={"operational_status": "kẹt sạc tại trạm", "incident": "charging_stuck"},
                suggested_action="Cứu hộ khẩn cấp tại trạm sạc",
                confidence_score=0.95,
            )
            loc = CaseLocation(
                id="loc_stuck",
                case_id=case.id,
                status="CONSENTED",
                source="BROWSER_GPS",
                latitude=21.025,
                longitude=105.835,
                location_label="Trạm sạc VinFast Hà Nội",
                precision="EXACT",
                share_with_staff=True,
            )
            case.brief = brief
            case.location = loc
            session.add_all([case, brief, loc])
            session.commit()

            assert is_heavy_incident_or_needs_rescue(case) is True

            resp = build_case_service_points_response(session, case)
            assert resp.rescue_hotline == "1900-232389"
            assert len(resp.recommended_points) > 0
            assert resp.recommended_points[0].id == "sp_test_rescue"

    finally:
        db_mod.engine = orig_engine
        engine.dispose()
