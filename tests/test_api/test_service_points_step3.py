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
    infer_coordinates_from_label,
    is_heavy_incident_or_needs_rescue,
    search_service_points_catalog,
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


def test_sparse_area_no_points_nearby_flag_and_needs_location(step3_db_session):
    """
    Item B: Vùng thưa: Khi khách đã chia sẻ GPS nhưng trong 150km không có điểm nào:
    - no_points_nearby = True
    - message = "Chưa có điểm dịch vụ trong 150 km quanh vị trí của bạn; vui lòng gọi hotline"
    - recommended_points = []
    - needs_location = False (khách ĐÃ chia sẻ vị trí thành công)
    - Nếu sự cố nặng: vẫn giữ rescue_hotline
    """
    db = step3_db_session
    user = User(id="u_sparse", username="u_sparse", password_hash="dummy", role=UserRole.CUSTOMER.value)
    db.add(user)

    case = Case(
        id="CASE-SPARSE-01",
        user_id=user.id,
        session_id="s_sparse",
        intent="Service/Incident",
        priority="CRITICAL",  # Sự cố nặng
    )
    loc = CaseLocation(
        id="loc_sparse_01",
        case_id=case.id,
        status="CONSENTED",
        source="BROWSER_GPS",
        location_label="Vùng biển xa",
        latitude=8.68,  # Ngoài 150km so với mọi điểm trong DB test
        longitude=106.60,
        precision="EXACT",
        share_with_staff=True,
    )
    case.location = loc
    db.add_all([case, loc])
    db.commit()

    resp = build_case_service_points_response(db, case)
    assert resp.no_points_nearby is True
    assert "150 km" in (resp.message or "")
    assert resp.recommended_points == []
    assert resp.needs_location is False
    assert resp.rescue_hotline == VINFAST_HOTLINE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,input_lat,input_lng,label,share_staff,expected_lat,expected_lng,expected_label,expected_share",
    [
        ("CONSENTED", 21.0315, 105.8145, "29 Liễu Giai, Hà Nội", True, 21.0315, 105.8145, "29 Liễu Giai, Hà Nội", True),
        ("MANUAL", 21.0315, 105.8145, "Ba Đình, Hà Nội", True, None, None, "Ba Đình, Hà Nội", True),
        ("NOT_SHARED", 21.0315, 105.8145, "Không muốn chia sẻ", False, None, None, "", False),
        ("UNKNOWN", 21.0315, 105.8145, "Khu vực chung", True, None, None, "Khu vực chung", True),
    ],
)
async def test_location_create_vs_update_consistency_table(
    client, step3_db_session, status, input_lat, input_lng, label, share_staff,
    expected_lat, expected_lng, expected_label, expected_share
):
    """
    Item D: Nhất quán POST /customer/location:
    So sánh nhánh tạo mới và nhánh cập nhật cho từng status (CONSENTED, MANUAL, NOT_SHARED, UNKNOWN)
    về latitude, longitude, location_label, share_with_staff.
    Cả 2 nhánh phải cho ra kết quả hoàn toàn giống nhau!
    """
    db = step3_db_session
    user = User(id=f"u_eq_{status}", username=f"u_eq_{status}", password_hash="dummy", role=UserRole.CUSTOMER.value)
    db.add(user)

    case_create = Case(id=f"CASE-CREATE-{status}", user_id=user.id, session_id=f"sc_{status}", intent="Service/Incident")
    case_update = Case(id=f"CASE-UPDATE-{status}", user_id=user.id, session_id=f"su_{status}", intent="Service/Incident")
    # Cho case_update có sẵn vị trí ban đầu để kích hoạt nhánh UPDATE
    initial_loc = CaseLocation(
        id=f"loc_init_{status}",
        case_id=case_update.id,
        status="CONSENTED",
        source="BROWSER_GPS",
        location_label="Tọa độ cũ",
        latitude=10.0,
        longitude=105.0,
        precision="EXACT",
        share_with_staff=False,
    )
    db.add_all([case_create, case_update, initial_loc])
    db.commit()

    token = create_token(user_id=user.id, role=user.role)
    headers = {"Authorization": f"Bearer {token}"}

    payload_create = {
        "case_id": case_create.id,
        "status": status,
        "source": "BROWSER_GPS" if status == "CONSENTED" else "USER_TEXT",
        "location_label": label,
        "latitude": input_lat,
        "longitude": input_lng,
        "precision": "EXACT" if status == "CONSENTED" else "APPROXIMATE",
        "share_with_staff": share_staff,
    }
    payload_update = dict(payload_create, case_id=case_update.id)

    # 1. Gọi nhánh CREATE (chưa có CaseLocation)
    res_create = await client.post("/api/v1/customer/location", json=payload_create, headers=headers)
    assert res_create.status_code == 200
    data_c = res_create.json()["data"]

    # 2. Gọi nhánh UPDATE (đã có CaseLocation)
    res_update = await client.post("/api/v1/customer/location", json=payload_update, headers=headers)
    assert res_update.status_code == 200
    data_u = res_update.json()["data"]

    # 3. Đối chiếu cả hai nhánh với kỳ vọng và đối chiếu lẫn nhau
    for field, expected in [
        ("latitude", expected_lat),
        ("longitude", expected_lng),
        ("location_label", expected_label),
        ("share_with_staff", expected_share),
    ]:
        assert data_c[field] == expected, f"CREATE field {field} mismatch: {data_c[field]} vs {expected}"
        assert data_u[field] == expected, f"UPDATE field {field} mismatch: {data_u[field]} vs {expected}"
        assert data_c[field] == data_u[field], f"CREATE vs UPDATE mismatch on field {field}"


def test_area_matching_without_gps_fallback_and_unrecognized(step3_db_session):
    """
    Item E: Khớp khu vực không GPS:
    - Quận không có trong bảng (nhưng có tỉnh): fallback về tâm tỉnh.
    - Tỉnh không nhận diện được: trả về None -> needs_location = True, recommended_points = [].
    - Nhãn chỉ có phường (không khớp quận, không có tỉnh): trả về None -> needs_location = True.
    """
    # 1. Quận không có trong bảng DISTRICT_CENTERS: Chương Mỹ -> fallback về tâm Hà Nội (21.0285, 105.8542)
    coords_district_fallback = infer_coordinates_from_label("Huyện Chương Mỹ, Hà Nội")
    assert coords_district_fallback == (21.0285, 105.8542)

    # 2. Tỉnh không nhận diện được -> None
    coords_unknown_prov = infer_coordinates_from_label("Quận Nowhere, Tỉnh Fantasyland")
    assert coords_unknown_prov is None

    # 3. Nhãn chỉ có phường đơn lẻ (không có quận/huyện trong bảng và không có tỉnh) -> None
    coords_ward_only = infer_coordinates_from_label("Phường Bến Nghé")
    assert coords_ward_only is None

    # Kiểm tra hành vi end-to-end với case
    db = step3_db_session
    user = User(id="u_area", username="u_area", password_hash="dummy", role=UserRole.CUSTOMER.value)
    db.add(user)

    case_unknown = Case(id="CASE-AREA-UNREC", user_id=user.id, session_id="s_area", intent="Service/Incident")
    loc_unknown = CaseLocation(
        id="loc_unrec", case_id=case_unknown.id, status="MANUAL", source="USER_TEXT",
        location_label="Địa danh không xác định", precision="APPROXIMATE", share_with_staff=True
    )
    case_unknown.location = loc_unknown
    db.add_all([case_unknown, loc_unknown])
    db.commit()

    resp_unrec = build_case_service_points_response(db, case_unknown)
    assert resp_unrec.needs_location is True
    assert resp_unrec.recommended_points == []


def test_search_service_points_catalog_direct(step3_db_session):
    """
    Item C: Kiểm tra search_service_points_catalog truy vấn qua service_point_service:
    - is_visible=True, is_car_compatible=True
    - GSM xếp sau xưởng car/partner
    """
    db = step3_db_session
    now = utcnow()
    sp_car = ServicePoint(
        id="ws_catalog_car", source_file="service_2s", category="workshop", category_slug="service_car",
        name="Xưởng Ô tô VinFast Test", address="Hà Nội", latitude=21.028, longitude=105.854,
        status="ACTIVE", access_type="Public", is_car_compatible=True, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    sp_gsm = ServicePoint(
        id="ws_catalog_gsm", source_file="service_2s", category="workshop", category_slug="service_gsm",
        name="Xưởng Taxi GSM Test", address="Hà Nội", latitude=21.027, longitude=105.853,
        status="ACTIVE", access_type="Public", is_car_compatible=True, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    db.add_all([sp_car, sp_gsm])
    db.commit()

    res = search_service_points_catalog(
        lat=21.0285, lng=105.8542, category="SERVICE_WORKSHOP", radius_km=10.0, limit=5, vehicle_type="CAR", db=db
    )
    assert res["source"] == "VinFast (dữ liệu thu thập)"
    assert res["verification_status"] == "SNAPSHOT"
    assert len(res["points"]) >= 2
    # car workshop phải xếp trước GSM bất kể khoảng cách
    assert res["points"][0]["id"] == "ws_catalog_car"
    assert res["points"][0]["province"] == "Hà Nội"


def test_area_matching_prioritizes_same_province_and_out_of_area_warning(step3_db_session):
    """
    Item 3(c): Khi không có GPS:
    - Ưu tiên điểm có địa chỉ cùng tỉnh với nhãn
    - Nếu không có điểm nào cùng tỉnh thì trả thêm message nói rõ 'Chưa có xưởng trong khu vực bạn nhập; điểm gần nhất ở [tỉnh khác]'
      và KHÔNG hiển thị như gợi ý bình thường (is_out_of_area=True).
    - Mỗi điểm trả thêm trường province (từ address).
    """
    db = step3_db_session
    now = utcnow()
    user = User(id="u_area_check", username="u_area_check", password_hash="dummy", role=UserRole.CUSTOMER.value)
    db.add(user)

    # 1. Trường hợp có điểm cùng tỉnh và khác tỉnh
    # Điểm Hà Nội (gần hơn) và điểm Bắc Ninh (xa hơn)
    sp_hanoi = ServicePoint(
        id="ws_hanoi_p", source_file="service_2s", category="workshop", category_slug="service_car",
        name="VinFast Hà Nội", address="Số 1 Tràng Tiền, Thành phố Hà Nội", latitude=21.025, longitude=105.855,
        status="ACTIVE", access_type="Public", is_car_compatible=True, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    sp_bacninh = ServicePoint(
        id="ws_bacninh_p", source_file="service_2s", category="workshop", category_slug="service_car",
        name="VinFast Bắc Ninh", address="Đường Lý Thái Tổ, Thành phố Bắc Ninh", latitude=21.186, longitude=106.076,
        status="ACTIVE", access_type="Public", is_car_compatible=True, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    sp_angiang = ServicePoint(
        id="ws_angiang_p", source_file="service_2s", category="workshop", category_slug="service_car",
        name="VinFast An Giang", address="Đường Trần Hưng Đạo, Tỉnh An Giang", latitude=10.383, longitude=105.416,
        status="ACTIVE", access_type="Public", is_car_compatible=True, is_visible=True,
        crawled_at=now, created_at=now, updated_at=now,
    )
    db.add_all([sp_hanoi, sp_bacninh, sp_angiang])
    db.commit()

    case_bn = Case(id="CASE-AREA-BN", user_id=user.id, session_id="s_bn", intent="Service/Incident")
    loc_bn = CaseLocation(
        id="loc_bn", case_id=case_bn.id, status="MANUAL", source="USER_TEXT",
        location_label="Thành phố Bắc Ninh", precision="APPROXIMATE", share_with_staff=True
    )
    case_bn.location = loc_bn
    db.add_all([case_bn, loc_bn])
    db.commit()

    resp_bn = build_case_service_points_response(db, case_bn)
    assert len(resp_bn.recommended_points) >= 1
    # Điểm Bắc Ninh phải được ưu tiên lên đầu vì cùng tỉnh với nhãn
    assert resp_bn.recommended_points[0].id == "ws_bacninh_p"
    assert resp_bn.recommended_points[0].province == "Thành phố Bắc Ninh"
    assert resp_bn.is_out_of_area is False

    # 2. Trường hợp nhãn không có điểm nào trong cùng tỉnh (ví dụ Cần Thơ không có xưởng, tìm thấy An Giang lân cận)
    case_ct = Case(id="CASE-AREA-CT", user_id=user.id, session_id="s_ct", intent="Service/Incident")
    loc_ct = CaseLocation(
        id="loc_ct", case_id=case_ct.id, status="MANUAL", source="USER_TEXT",
        location_label="Quận Ninh Kiều, Cần Thơ", precision="APPROXIMATE", share_with_staff=True
    )
    case_ct.location = loc_ct
    db.add_all([case_ct, loc_ct])
    db.commit()

    resp_ct = build_case_service_points_response(db, case_ct)
    assert resp_ct.is_out_of_area is True
    assert "Chưa có xưởng trong khu vực bạn nhập; điểm gần nhất ở Tỉnh An Giang" in resp_ct.message
    for pt in resp_ct.recommended_points:
        assert pt.is_out_of_area is True
        assert pt.province is not None


def test_rescue_hotline_unmasked_in_real_api_response(step3_db_session):
    """
    Item 5: Khẳng định response thật trả rescue_hotline đúng nguyên giá trị VINFAST_HOTLINE
    (1900-232389, không che), che 4 số chỉ được làm trong reporting script.
    """
    db = step3_db_session
    user = User(id="u_rescue_val", username="u_rescue_val", password_hash="dummy", role=UserRole.CUSTOMER.value)
    db.add(user)

    case = Case(
        id="CASE-RESCUE-UNMASKED-CHECK",
        user_id=user.id,
        session_id="s_rescue_val",
        intent="Service/Incident",
        priority="CRITICAL",
        safety_status="DANGER",
    )
    loc = CaseLocation(
        id="loc_rescue_val",
        case_id=case.id,
        status="MANUAL",
        source="BROWSER_GPS",
        location_label="Hà Nội",
        latitude=21.0285,
        longitude=105.8542,
        precision="EXACT",
        share_with_staff=True,
    )
    case.location = loc
    db.add_all([case, loc])
    db.commit()

    resp = build_case_service_points_response(db, case)
    assert resp.rescue_hotline == "1900-232389"
    assert resp.rescue_hotline == VINFAST_HOTLINE
    assert "****" not in resp.rescue_hotline

