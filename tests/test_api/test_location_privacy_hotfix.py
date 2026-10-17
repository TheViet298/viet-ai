import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, get_db
from src.main import app
from src.models.db_models import Case, CaseLocation, User, UserRole, utcnow
from src.services.auth import create_token
from src.services.observability import mask_telemetry


@pytest.fixture
def test_db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'privacy_test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        app.dependency_overrides[get_db] = lambda: db
        yield db
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.asyncio
async def test_staff_cannot_see_coordinates_when_share_with_staff_is_false(client, test_db_session):
    db = test_db_session
    staff = User(
        id="staff-priv-01",
        username="staff_priv_01",
        password_hash="dummy",
        role=UserRole.STAFF.value,
    )
    customer = User(
        id="cust-priv-01",
        username="cust_priv_01",
        password_hash="dummy",
        role=UserRole.CUSTOMER.value,
    )
    db.add_all([staff, customer])

    case = Case(
        id="CASE-PRIV-001",
        user_id="cust-priv-01",
        session_id="session-priv-01",
        intent="Charging/Battery",
        priority="HIGH",
        status="Open",
        vehicle_model="VF8",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(case)

    loc = CaseLocation(
        id="loc-priv-01",
        case_id="CASE-PRIV-001",
        status="CONSENTED",
        source="BROWSER_GPS",
        location_label="Tòa nhà Landmark 81, TP.HCM",
        latitude=10.795123,
        longitude=106.721845,
        precision="EXACT",
        share_with_staff=False,
        created_at=utcnow(),
    )
    db.add(loc)
    db.commit()

    staff_token = create_token(user_id=staff.id, role=staff.role)

    response = await client.get(
        "/api/v1/staff/tickets/CASE-PRIV-001",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    ticket_loc = data["data"]["location"]
    assert ticket_loc is not None
    assert ticket_loc["latitude"] is None
    assert ticket_loc["longitude"] is None
    assert ticket_loc["share_with_staff"] is False
    assert ticket_loc["location_label"] == "Khách hàng không chia sẻ vị trí với nhân viên"


@pytest.mark.asyncio
async def test_staff_sees_rounded_coordinates_when_precision_is_approximate(client, test_db_session):
    db = test_db_session
    staff = User(
        id="staff-priv-02",
        username="staff_priv_02",
        password_hash="dummy",
        role=UserRole.STAFF.value,
    )
    customer = User(
        id="cust-priv-02",
        username="cust_priv_02",
        password_hash="dummy",
        role=UserRole.CUSTOMER.value,
    )
    db.add_all([staff, customer])

    case = Case(
        id="CASE-PRIV-002",
        user_id="cust-priv-02",
        session_id="session-priv-02",
        intent="Charging/Battery",
        priority="HIGH",
        status="Open",
        vehicle_model="VF8",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(case)

    loc = CaseLocation(
        id="loc-priv-02",
        case_id="CASE-PRIV-002",
        status="CONSENTED",
        source="BROWSER_GPS",
        location_label="Hồ Hoàn Kiếm, Hà Nội",
        latitude=21.028511,
        longitude=105.854199,
        precision="APPROXIMATE",
        share_with_staff=True,
        created_at=utcnow(),
    )
    db.add(loc)
    db.commit()

    staff_token = create_token(user_id=staff.id, role=staff.role)

    response = await client.get(
        "/api/v1/staff/tickets/CASE-PRIV-002",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert response.status_code == 200
    ticket_loc = response.json()["data"]["location"]
    assert ticket_loc is not None
    # 21.028511 rounded to 2 decimals is 21.03
    assert ticket_loc["latitude"] == 21.03
    # 105.854199 rounded to 2 decimals is 105.85
    assert ticket_loc["longitude"] == 105.85


@pytest.mark.asyncio
async def test_post_customer_location_outside_vietnam_returns_422(client, test_db_session):
    db = test_db_session
    customer = User(
        id="cust-priv-03",
        username="cust_priv_03",
        password_hash="dummy",
        role=UserRole.CUSTOMER.value,
    )
    db.add(customer)

    case = Case(
        id="CASE-PRIV-003",
        user_id="cust-priv-03",
        session_id="session-priv-03",
        intent="Charging/Battery",
        priority="HIGH",
        status="Open",
        vehicle_model="VF8",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(case)
    db.commit()

    cust_token = create_token(user_id=customer.id, role=customer.role)

    # Coordinates in Paris: lat 48.8566, lng 2.3522
    payload = {
        "case_id": "CASE-PRIV-003",
        "status": "CONSENTED",
        "source": "BROWSER_GPS",
        "location_label": "Tháp Eiffel, Paris",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "precision": "EXACT",
        "share_with_staff": True,
    }
    response = await client.post(
        "/api/v1/customer/location",
        json=payload,
        headers={"Authorization": f"Bearer {cust_token}"},
    )
    assert response.status_code == 422
    assert "lãnh thổ Việt Nam" in response.json()["detail"]


def test_observability_masks_customer_coordinates():
    sample_data = {
        "name": "vinfast_nearby_search",
        "latitude": 21.031522,
        "longitude": 105.852411,
        "location_label": "123 Phố Huế",
        "lat": 21.03,
        "lng": 105.85,
        "query": "vinfast_nearby_search(latitude=21.0315, longitude=105.8524)",
    }
    masked = mask_telemetry(data=sample_data)
    assert masked["latitude"] == "[REDACTED]"
    assert masked["longitude"] == "[REDACTED]"
    assert masked["lat"] == "[REDACTED]"
    assert masked["lng"] == "[REDACTED]"
    assert masked["location_label"] == "[REDACTED]"
    assert "21.0315" not in masked["query"]
    assert "105.8524" not in masked["query"]


@pytest.mark.asyncio
async def test_staff_receives_none_coords_when_status_is_not_shared_even_if_coords_in_db(client, test_db_session):
    db = test_db_session
    staff = User(
        id="staff-priv-04",
        username="staff_priv_04",
        password_hash="dummy",
        role=UserRole.STAFF.value,
    )
    customer = User(
        id="cust-priv-04",
        username="cust_priv_04",
        password_hash="dummy",
        role=UserRole.CUSTOMER.value,
    )
    db.add_all([staff, customer])

    case = Case(
        id="CASE-PRIV-004",
        user_id="cust-priv-04",
        session_id="session-priv-04",
        intent="General",
        priority="MEDIUM",
        status="Open",
        vehicle_model="VF8",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(case)

    # DB still has stale coordinates, but status is NOT_SHARED
    loc = CaseLocation(
        id="loc-priv-04",
        case_id="CASE-PRIV-004",
        status="NOT_SHARED",
        source="BROWSER_GPS",
        location_label="Số 10 Tràng Thi, Hàng Trống, Hoàn Kiếm, Hà Nội",
        latitude=21.0285,
        longitude=105.8542,
        precision="EXACT",
        share_with_staff=True,
        created_at=utcnow(),
    )
    db.add(loc)
    db.commit()

    staff_token = create_token(user_id=staff.id, role=staff.role)

    response = await client.get(
        "/api/v1/staff/tickets/CASE-PRIV-004",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]["location"]
    assert data["latitude"] is None
    assert data["longitude"] is None
    assert data["location_label"] == "Khách hàng không chia sẻ vị trí với nhân viên"


@pytest.mark.asyncio
async def test_staff_approximate_label_does_not_contain_exact_house_address(client, test_db_session):
    db = test_db_session
    staff = User(
        id="staff-priv-05",
        username="staff_priv_05",
        password_hash="dummy",
        role=UserRole.STAFF.value,
    )
    customer = User(
        id="cust-priv-05",
        username="cust_priv_05",
        password_hash="dummy",
        role=UserRole.CUSTOMER.value,
    )
    db.add_all([staff, customer])

    case = Case(
        id="CASE-PRIV-005",
        user_id="cust-priv-05",
        session_id="session-priv-05",
        intent="General",
        priority="MEDIUM",
        status="Open",
        vehicle_model="VF8",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(case)

    # EXACT address in DB: "Số 458 Minh Khai, Phường Vĩnh Tuy, Quận Hai Bà Trưng, Hà Nội"
    loc = CaseLocation(
        id="loc-priv-05",
        case_id="CASE-PRIV-005",
        status="CONSENTED",
        source="BROWSER_GPS",
        location_label="Số 458 Minh Khai, Phường Vĩnh Tuy, Quận Hai Bà Trưng, Hà Nội",
        latitude=20.998123,
        longitude=105.868789,
        precision="APPROXIMATE",
        share_with_staff=True,
        created_at=utcnow(),
    )
    db.add(loc)
    db.commit()

    staff_token = create_token(user_id=staff.id, role=staff.role)

    response = await client.get(
        "/api/v1/staff/tickets/CASE-PRIV-005",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]["location"]
    # Exact house number "Số 458 Minh Khai" must be stripped
    assert "Số 458 Minh Khai" not in data["location_label"]
    assert "Phường Vĩnh Tuy" in data["location_label"]
    assert data["latitude"] == 21.0
    assert data["longitude"] == 105.87

    # Customer viewing own case still sees full address
    cust_token = create_token(user_id=customer.id, role=customer.role)
    cust_resp = await client.get(
        "/api/v1/customer/cases/CASE-PRIV-005",
        headers={"Authorization": f"Bearer {cust_token}"},
    )
    assert cust_resp.status_code == 200
    cust_loc = cust_resp.json()["data"]["location"]
    assert cust_loc["location_label"] == "Số 458 Minh Khai, Phường Vĩnh Tuy, Quận Hai Bà Trưng, Hà Nội"
    assert cust_loc["latitude"] == 20.998123
    assert cust_loc["longitude"] == 105.868789


def test_real_langfuse_callback_masks_customer_coordinates():
    """Verify that real Langfuse CallbackHandler masks location coordinates and labels."""
    from langfuse.langchain import CallbackHandler
    from src.services.langfuse_callback import safe_callback

    captured = []

    class BaseLangfuseHandler(CallbackHandler):
        def __init__(self):
            pass

        def on_tool_start(self, serialized, input_str, **kwargs):
            captured.append(input_str)

    SafeHandler = safe_callback(BaseLangfuseHandler)
    handler = SafeHandler()
    handler.on_tool_start(
        {"name": "vinfast_nearby_search"},
        "vinfast_nearby_search(latitude=21.0315, longitude=105.8524)",
    )

    assert len(captured) == 1
    sanitized = captured[0]
    assert "21.0315" not in sanitized
    assert "105.8524" not in sanitized
    assert "latitude=[REDACTED]" in sanitized
    assert "longitude=[REDACTED]" in sanitized


def test_extract_approximate_label_whole_word_matching():
    """Verify that extract_approximate_label matches admin keywords at start of comma parts."""
    from src.api.staff import extract_approximate_label

    # "Số 5 Xã Đàn, Đống Đa, Hà Nội" must not reveal "Số 5"
    res1 = extract_approximate_label("Số 5 Xã Đàn, Đống Đa, Hà Nội")
    assert res1 is not None
    assert "Số 5" not in res1
    assert res1 == "Đống Đa, Hà Nội"

    # "Số 97 An Dương Vương, Phường An Đông, Thành phố Huế" -> "Phường An Đông, Thành phố Huế"
    res2 = extract_approximate_label("Số 97 An Dương Vương, Phường An Đông, Thành phố Huế")
    assert res2 == "Phường An Đông, Thành phố Huế"


def test_observability_does_not_redact_normal_decimal_numbers():
    """Verify that price, latency, and confidence score are not redacted."""
    text = "Độ trễ: 0.45s, điểm tin cậy: 0.95, chi phí bảo dưỡng: 150000.50 VND"
    masked = mask_telemetry(data=text)
    assert "0.45" in masked
    assert "0.95" in masked
    assert "150000.50" in masked

    # But raw coordinates in VN bounding box (8..24, 102..110) are masked
    coord_text = "Vị trí xe hiện tại: 21.0285, 105.8542"
    masked_coord = mask_telemetry(data=coord_text)
    assert "21.0285" not in masked_coord
    assert "105.8542" not in masked_coord
    assert "[COORDINATES_REDACTED]" in masked_coord

