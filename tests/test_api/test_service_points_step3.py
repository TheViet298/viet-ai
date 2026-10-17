from datetime import UTC, datetime
import math
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.agents.guardrails import VINFAST_HOTLINE
from src.cli.import_service_points import parse_service_points
from src.db import Base, get_db
from src.main import app
from src.models.db_models import Case, CaseBrief, CaseLocation, Message, Priority, ServicePoint, User, UserRole, utcnow
from src.services.auth import create_token
from src.services.service_point_service import (
    build_case_service_points_response,
    find_nearby_service_points,
    haversine_km,
    is_heavy_incident_or_needs_rescue,
)


@pytest.fixture
def step3_db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'step3_test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        app.dependency_overrides[get_db] = lambda: db
        yield db
    app.dependency_overrides.clear()
    engine.dispose()


def test_haversine_formula_against_known_points():
    """Haversine đúng với cặp điểm đã biết khoảng cách."""
    dist = haversine_km(21.0285, 105.8542, 21.0544, 105.8236)
    assert 4.1 <= dist <= 4.5
    assert haversine_km(21.0, 105.0, 21.0, 105.0) == 0.0
    hn_hcm = haversine_km(21.0285, 105.8542, 10.8231, 106.6297)
    assert 1120 <= hn_hcm <= 1160


def test_inactive_and_restricted_stations_do_not_appear(step3_db_session):
    """Trạm sạc INACTIVE / UNAVAILABLE / OUTOFSERVICE / Restricted không bao giờ xuất hiện."""
    db = step3_db_session
    now = utcnow()
    active_pub = ServicePoint(
        id="cs_active_pub", source_file="charging_stations", category="charging_station",
        name="Trạm sạc Active Public", address="Hà Nội", latitude=21.02, longitude=105.85,
        status="ACTIVE", access_type="Public", is_car_compatible=True, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    busy_pub = ServicePoint(
        id="cs_busy_pub", source_file="charging_stations", category="charging_station",
        name="Trạm sạc Busy Public", address="Hà Nội", latitude=21.021, longitude=105.851,
        status="BUSY", access_type="Public", is_car_compatible=True, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    inactive = ServicePoint(
        id="cs_inactive", source_file="charging_stations", category="charging_station",
        name="Trạm sạc Inactive", address="Hà Nội", latitude=21.022, longitude=105.852,
        status="INACTIVE", access_type="Public", is_car_compatible=True, is_visible=False,
        crawled_at=now, created_at=now, updated_at=now,
    )
    restricted = ServicePoint(
        id="cs_restricted", source_file="charging_stations", category="charging_station",
        name="Trạm sạc Restricted", address="Hà Nội", latitude=21.023, longitude=105.853,
        status="ACTIVE", access_type="Restricted", is_car_compatible=True, is_visible=False,
        crawled_at=now, created_at=now, updated_at=now,
    )
    db.add_all([active_pub, busy_pub, inactive, restricted])
    db.commit()

    results = find_nearby_service_points(db, lat=21.02, lng=105.85, category="charging_station", radius_km=10)
    result_ids = [sp.id for sp, _ in results]

    assert "cs_active_pub" in result_ids
    assert "cs_busy_pub" in result_ids
    assert "cs_inactive" not in result_ids
    assert "cs_restricted" not in result_ids


def test_no_two_wheeler_or_bus_service_points(step3_db_session):
    """Không bao giờ trả về xe máy / tủ đổi pin / xưởng xe máy / VinBus."""
    db = step3_db_session
    now = utcnow()
    car_workshop = ServicePoint(
        id="ws_car", source_file="service_2s", category="workshop", category_slug="service_car",
        name="Xưởng Ô tô VinFast", address="Hà Nội", latitude=21.02, longitude=105.85,
        status="ACTIVE", access_type="Public", is_car_compatible=True, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    escooter_ws = ServicePoint(
        id="ws_escooter", source_file="service_2s", category="workshop", category_slug="service_escooter",
        name="Xưởng Xe Máy Điện", address="Hà Nội", latitude=21.021, longitude=105.851,
        status="ACTIVE", access_type="Public", is_car_compatible=False, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    bus_ws = ServicePoint(
        id="ws_bus", source_file="service_2s", category="workshop", category_slug="service_bus",
        name="Xưởng VinBus", address="Hà Nội", latitude=21.022, longitude=105.852,
        status="ACTIVE", access_type="Public", is_car_compatible=False, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    db.add_all([car_workshop, escooter_ws, bus_ws])
    db.commit()

    results = find_nearby_service_points(db, lat=21.02, lng=105.85, category="workshop", radius_km=10)
    result_ids = [sp.id for sp, _ in results]

    assert "ws_car" in result_ids
    assert "ws_escooter" not in result_ids
    assert "ws_bus" not in result_ids


def test_gsm_ranking_car_and_partner_always_rank_first_regardless_of_distance(step3_db_session):
    """
    Item 1: Mọi xưởng service_car/service_car_partner trong bán kính tìm kiếm xếp TRƯỚC service_gsm
    bất kể khoảng cách. service_gsm chỉ hiện khi không đủ xưởng car/partner trong bán kính.
    """
    db = step3_db_session
    now = utcnow()

    # GSM gần hơn (2 km)
    ws_gsm = ServicePoint(
        id="ws_gsm_close", source_file="service_2s", category="workshop", category_slug="service_gsm",
        name="VinFast GSM Gần", address="Đà Nẵng", latitude=16.035, longitude=108.210,
        status="ACTIVE", access_type="Public", is_car_compatible=True, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    # Partner xa hơn (8 km)
    ws_partner = ServicePoint(
        id="ws_partner_far", source_file="service_2s", category="workshop", category_slug="service_car_partner",
        name="VinFast Partner Xa", address="Đà Nẵng", latitude=16.110, longitude=108.240,
        status="ACTIVE", access_type="Public", is_car_compatible=True, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    # Car xa hơn (5 km)
    ws_car = ServicePoint(
        id="ws_car_mid", source_file="service_2s", category="workshop", category_slug="service_car",
        name="VinFast Car Vừa", address="Đà Nẵng", latitude=16.070, longitude=108.220,
        status="ACTIVE", access_type="Public", is_car_compatible=True, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    db.add_all([ws_gsm, ws_partner, ws_car])
    db.commit()

    results = find_nearby_service_points(db, lat=16.0544, lng=108.2022, category="workshop", radius_km=15, limit=5)
    ids = [sp.id for sp, _ in results]

    # Partner (8km) và Car (5km) đều phải đứng TRƯỚC GSM (2km)!
    assert ids.index("ws_car_mid") < ids.index("ws_gsm_close")
    assert ids.index("ws_partner_far") < ids.index("ws_gsm_close")

    # Kiểm tra note của GSM khi qua build_case_service_points_response
    user = User(id="u_gsm", username="u_gsm", password_hash="dummy", role=UserRole.CUSTOMER.value)
    case_gsm = Case(id="CASE-GSM-01", user_id=user.id, session_id="sgsm", intent="Service/Incident", priority="LOW")
    loc_gsm = CaseLocation(id="lgsm", case_id=case_gsm.id, status="CONSENTED", source="MAP_PICKER",
                           latitude=16.0544, longitude=108.2022, precision="EXACT", location_label="Đà Nẵng")
    db.add_all([user, case_gsm, loc_gsm])
    db.commit()

    resp = build_case_service_points_response(db, case_gsm)
    gsm_item = next(p for p in resp.recommended_points if p.id == "ws_gsm_close")
    assert gsm_item.note is not None
    assert "taxi GSM" in gsm_item.note


def test_heavy_incident_triage_triggers_rescue_hotline(step3_db_session):
    """
    Item 2: Triage sự cố nặng:
    - Rùa vàng, xe không di chuyển được, tai nạn -> có rescue_hotline
    - Bảo dưỡng định kỳ -> KHÔNG có rescue_hotline
    - Service/Incident thiếu dữ liệu phân loại -> ƯU TIÊN có rescue_hotline
    """
    db = step3_db_session
    now = utcnow()
    user = User(id="u_triage", username="u_triage", password_hash="dummy", role=UserRole.CUSTOMER.value)
    db.add(user)

    # 1. Rùa vàng -> có rescue_hotline
    case_turtle = Case(id="C_TURTLE", user_id=user.id, session_id="st", intent="Service/Incident", priority="MEDIUM")
    brief_turtle = CaseBrief(id="bt", case_id=case_turtle.id, summary="Xe VF8 báo rùa vàng trên taplo, giảm tốc độ")
    case_turtle.brief = brief_turtle
    assert is_heavy_incident_or_needs_rescue(case_turtle) is True

    # 2. Xe không di chuyển được -> có rescue_hotline
    case_stuck = Case(id="C_STUCK", user_id=user.id, session_id="ss", intent="Service/Incident", priority="MEDIUM")
    brief_stuck = CaseBrief(id="bs", case_id=case_stuck.id, summary="Xe không di chuyển được, chết máy giữa đường")
    case_stuck.brief = brief_stuck
    db.add_all([case_stuck, brief_stuck])
    assert is_heavy_incident_or_needs_rescue(case_stuck) is True

    # 3. Tai nạn / va chạm -> có rescue_hotline
    case_accident = Case(id="C_ACCIDENT", user_id=user.id, session_id="sa", intent="Service/Incident", priority="CRITICAL")
    brief_accident = CaseBrief(id="ba", case_id=case_accident.id, summary="Va chạm giao thông móp đầu xe")
    case_accident.brief = brief_accident
    db.add_all([case_accident, brief_accident])
    assert is_heavy_incident_or_needs_rescue(case_accident) is True

    # 4. Bảo dưỡng định kỳ -> KHÔNG có rescue_hotline
    case_maint = Case(id="C_MAINT", user_id=user.id, session_id="sm", intent="Service/Incident", priority="LOW")
    brief_maint = CaseBrief(id="bm", case_id=case_maint.id, summary="Khách hàng cần bảo dưỡng định kỳ 12.000 km và thay dầu phanh")
    case_maint.brief = brief_maint
    db.add_all([case_maint, brief_maint])
    assert is_heavy_incident_or_needs_rescue(case_maint) is False

    # 5. Intent Service/Incident thiếu dữ liệu phân loại -> ƯU TIÊN bật rescue_hotline
    case_unknown = Case(id="C_UNKNOWN", user_id=user.id, session_id="su", intent="Service/Incident", priority="MEDIUM")
    assert is_heavy_incident_or_needs_rescue(case_unknown) is True


@pytest.mark.asyncio
async def test_location_update_branch_clears_coords_on_manual_or_not_shared(client, step3_db_session):
    """
    Item 4(a): Khi cập nhật vị trí sang MANUAL hoặc NOT_SHARED, tọa độ cũ trong DB PHẢI bị xóa (None).
    """
    db = step3_db_session
    user = User(id="u_priv", username="u_priv", password_hash="dummy", role=UserRole.CUSTOMER.value)
    db.add(user)
    case = Case(id="CASE-PRIV-01", user_id=user.id, session_id="spriv", intent="Service/Incident", priority="LOW")
    db.add(case)
    db.commit()

    token = create_token(user_id=user.id, role=user.role)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Gửi CONSENTED có tọa độ
    payload_gps = {
        "case_id": case.id, "status": "CONSENTED", "source": "BROWSER_GPS",
        "location_label": "29 Liễu Giai, Hà Nội", "latitude": 21.0315, "longitude": 105.8145,
        "precision": "EXACT", "share_with_staff": True,
    }
    r1 = await client.post("/api/v1/customer/location", json=payload_gps, headers=headers)
    assert r1.status_code == 200
    loc_db1 = db.query(CaseLocation).filter(CaseLocation.case_id == case.id).first()
    assert loc_db1.latitude == 21.0315
    assert loc_db1.longitude == 105.8145

    # 2. Cập nhật nhánh UPDATE sang MANUAL -> latitude & longitude phải bị xóa (None)
    payload_manual = {
        "case_id": case.id, "status": "MANUAL", "source": "USER_TEXT",
        "location_label": "Ba Đình, Hà Nội", "latitude": 21.0315, "longitude": 105.8145,
        "precision": "APPROXIMATE", "share_with_staff": True,
    }
    r2 = await client.post("/api/v1/customer/location", json=payload_manual, headers=headers)
    assert r2.status_code == 200
    db.expire_all()
    loc_db2 = db.query(CaseLocation).filter(CaseLocation.case_id == case.id).first()
    assert loc_db2.latitude is None
    assert loc_db2.longitude is None

    # 3. Cập nhật sang NOT_SHARED -> latitude & longitude phải là None
    payload_not_shared = {
        "case_id": case.id, "status": "NOT_SHARED", "source": "USER_TEXT",
        "location_label": "Không chia sẻ", "latitude": None, "longitude": None,
        "precision": "APPROXIMATE", "share_with_staff": False,
    }
    r3 = await client.post("/api/v1/customer/location", json=payload_not_shared, headers=headers)
    assert r3.status_code == 200
    db.expire_all()
    loc_db3 = db.query(CaseLocation).filter(CaseLocation.case_id == case.id).first()
    assert loc_db3.latitude is None
    assert loc_db3.longitude is None


def test_sparse_area_stepwise_radius_expansion(step3_db_session):
    """
    Item 5: Vùng thưa: Không có điểm trong 50km, mở rộng theo bậc lên 100km, 150km.
    Nếu ngoài 150km trả về rỗng.
    """
    db = step3_db_session
    now = utcnow()

    # Tạo điểm cách mốc Hà Giang ~75 km (nằm giữa 50km và 100km)
    # Tọa độ Hà Giang: (22.8233, 104.9839)
    # Tọa độ điểm cách ~75km: (22.20, 104.98)
    sp_mid = ServicePoint(
        id="sp_sparse_75km", source_file="service_2s", category="workshop", category_slug="service_car",
        name="VinFast Xưởng Tuyên Quang", address="Tuyên Quang", latitude=22.20, longitude=104.98,
        status="ACTIVE", access_type="Public", is_car_compatible=True, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    db.add(sp_mid)
    db.commit()

    dist = haversine_km(22.8233, 104.9839, 22.20, 104.98)
    assert 60.0 <= dist <= 80.0

    # Tìm kiếm với bán kính mặc định 50km -> Tự động mở rộng lên 100km và tìm thấy sp_sparse_75km
    results = find_nearby_service_points(db, lat=22.8233, lng=104.9839, category="workshop", radius_km=50.0)
    assert len(results) > 0
    assert results[0][0].id == "sp_sparse_75km"

    # Tìm kiếm tại tọa độ quá xa (> 200km, ví dụ giữa biển Đông hoặc Côn Đảo chưa có xưởng)
    results_empty = find_nearby_service_points(db, lat=8.68, lng=106.60, category="workshop", radius_km=50.0)
    assert results_empty == []
