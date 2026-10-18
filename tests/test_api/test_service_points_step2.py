from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.cli.import_service_points import (
    format_operating_hours,
    generate_point_id,
    import_records,
    normalize_phone,
    normalize_time_str,
    parse_service_points,
)
from src.db import Base, get_db
from src.main import app
from src.models.db_models import Case, CaseLocation, ServicePoint, User, UserRole, utcnow
from src.services.auth import create_token


@pytest.fixture
def step2_db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'step2_test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        app.dependency_overrides[get_db] = lambda: db
        yield db
    app.dependency_overrides.clear()
    engine.dispose()


def test_id_prefix_prevents_collision_across_files():
    """Item 1: Hai bản ghi ở hai file khác nhau cùng source_id không đè nhau."""
    id1 = generate_point_id("charging_stations", "12345", "Trạm sạc VinFast", 21.0, 105.8)
    id2 = generate_point_id("showrooms", "12345", "Showroom VinFast", 21.0, 105.8)
    id3 = generate_point_id("service_2s", "12345", "Xưởng VinFast", 21.0, 105.8)

    assert id1 == "charging_stations:12345"
    assert id2 == "showrooms:12345"
    assert id3 == "service_2s:12345"
    assert len({id1, id2, id3}) == 3


def test_operating_hours_parser_handles_all_formats():
    """Item 4(e): parse đủ các giá trị 08h30, 21h00, 17h00, 18h30, 17h30."""
    assert normalize_time_str("08h30") == "08:30"
    assert normalize_time_str("21h00") == "21:00"
    assert normalize_time_str("17h00") == "17:00"
    assert normalize_time_str("18h30") == "18:30"
    assert normalize_time_str("17h30") == "17:30"
    assert normalize_time_str("08:00") == "08:00"
    assert normalize_time_str("18:00") == "18:00"

    assert format_operating_hours("08h30", "17h30") == "08:30 - 17:30"
    assert format_operating_hours(None, None) is None


def test_real_crawl_data_parsing_and_idempotency(tmp_path):
    """
    Item 4(a), (b), (c), (d):
    - 4(a): Import 2 lần, số bản ghi không đổi: 25.228 nạp, 18.189 hiển thị.
    - 4(b): Minh Đức Lâm Đồng chỉ còn 1 bản ghi.
    - 4(c): Mọi hotline_service của xưởng đúng 10 chữ số.
    - 4(d): Đúng 39 xưởng có booking_url.
    """
    crawl_dir = Path("data/crawl")
    if not crawl_dir.exists():
        pytest.skip("data/crawl directory not found")

    records, stats = parse_service_points(crawl_dir)

    # Validate counts
    assert len(records) == 25228
    visible_count = sum(1 for r in records if r["is_visible"])
    assert visible_count == 18189

    # 4(b): Minh Đức Lâm Đồng chỉ còn 1 bản ghi trong xưởng 2S
    workshops = [r for r in records if r["category"] == "workshop"]
    assert len(workshops) == 181
    minh_duc = [r for r in workshops if "minh đức" in r["name"].lower() and "lâm đồng" in r["address"].lower()]
    assert len(minh_duc) == 1

    # 4(c): Mọi hotline_service của xưởng đúng 10 chữ số (nếu có)
    for w in workshops:
        hl_svc = w["hotline_service"]
        if hl_svc:
            assert len(hl_svc) == 10, f"Hotline service {hl_svc} in {w['name']} is not 10 digits"

    # 4(d): Đúng 39 xưởng có booking_url
    booking_workshops = [w for w in workshops if w["booking_url"] is not None]
    assert len(booking_workshops) == 39
    for bw in booking_workshops:
        assert "booking" in bw["services_offered"]

    # 4(a): Chạy import 2 lần vào test DB để kiểm tra tính idempotent
    test_db_file = tmp_path / "idempotent_test.db"
    db_url = f"sqlite:///{test_db_file}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    # Lần 1
    loaded1, vis1 = import_records(records, db_url)
    assert loaded1 == 25228
    assert vis1 == 18189

    # Lần 2 (chạy lại)
    loaded2, vis2 = import_records(records, db_url)
    assert loaded2 == 25228
    assert vis2 == 18189

    with Session(engine) as sess:
        total_in_db = sess.query(ServicePoint).count()
        vis_in_db = sess.query(ServicePoint).filter(ServicePoint.is_visible.is_(True)).count()
        assert total_in_db == 25228
        assert vis_in_db == 18189
    engine.dispose()


@pytest.mark.asyncio
async def test_cross_customer_isolation_cannot_access_other_case_or_location(client, step2_db_session):
    """
    Test cách ly dữ liệu: Khách hàng A tuyệt đối không thể đọc hồ sơ hay vị trí của Khách hàng B.
    Bảo vệ bằng check_case_ownership (RBAC).
    """
    db = step2_db_session
    cust_a = User(
        id="user-cust-a",
        username="customer_a",
        password_hash="dummy",
        role=UserRole.CUSTOMER.value,
    )
    cust_b = User(
        id="user-cust-b",
        username="customer_b",
        password_hash="dummy",
        role=UserRole.CUSTOMER.value,
    )
    db.add_all([cust_a, cust_b])

    case_b = Case(
        id="CASE-B-001",
        user_id=cust_b.id,
        session_id="session-b-001",
        intent="Tire/Brake",
        priority="MEDIUM",
        status="Open",
        vehicle_model="VF8",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(case_b)

    loc_b = CaseLocation(
        id="loc-b-001",
        case_id=case_b.id,
        status="CONSENTED",
        source="BROWSER_GPS",
        location_label="Số 100 Nguyễn Huệ, Quận 1, TP.HCM",
        latitude=10.7735,
        longitude=106.7038,
        precision="EXACT",
        share_with_staff=True,
        created_at=utcnow(),
    )
    db.add(loc_b)
    db.commit()

    token_a = create_token(user_id=cust_a.id, role=cust_a.role)

    # 1. Customer A attempts to read Customer B's case details -> 403
    resp_get = await client.get(
        f"/api/v1/customer/cases/{case_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_get.status_code == 403
    assert "không có quyền truy cập" in resp_get.json()["detail"].lower()

    # 2. Customer A attempts to update Customer B's location -> 403
    resp_post = await client.post(
        "/api/v1/customer/location",
        json={
            "case_id": case_b.id,
            "status": "CONSENTED",
            "source": "BROWSER_GPS",
            "location_label": "Địa chỉ giả mạo của A",
            "latitude": 21.0285,
            "longitude": 105.8542,
            "precision": "EXACT",
            "share_with_staff": True,
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_post.status_code == 403
    assert "không có quyền truy cập" in resp_post.json()["detail"].lower()

    # 3. Customer B authenticates and accesses own case successfully -> 200
    token_b = create_token(user_id=cust_b.id, role=cust_b.role)
    resp_b = await client.get(
        f"/api/v1/customer/cases/{case_b.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b.status_code == 200
    b_data = resp_b.json()["data"]
    assert b_data["location"]["location_label"] == "Số 100 Nguyễn Huệ, Quận 1, TP.HCM"
    assert b_data["location"]["latitude"] == 10.7735
    assert b_data["location"]["longitude"] == 106.7038


def test_safe_cli_blocks_remote_host_without_flag(monkeypatch):
    """
    Test CLI an toàn:
    - Nếu trỏ host từ xa (không phải localhost/127.0.0.1/::1) mà thiếu --allow-remote -> ValueError.
    - Password trong URL được che khi in/log lỗi.
    - Khi có --allow-remote -> cho phép kết nối.
    - Nếu không truyền --db-url và settings.database_url là remote -> từ chối chạy.
    """
    from src.cli.import_service_points import get_target_db_url, is_local_db, mask_db_url

    remote_url = "postgresql://user:super_secret_pw@autorack.proxy.rlwy.net:12345/railway"
    assert not is_local_db(remote_url)
    assert is_local_db("postgresql://postgres:postgres@localhost:5432/vinfast")
    assert is_local_db("postgresql://postgres:postgres@127.0.0.1:5432/vinfast")
    assert is_local_db("sqlite:///test.db")

    masked = mask_db_url(remote_url)
    assert "super_secret_pw" not in masked
    assert "***" in masked

    # 1. Chặn khi truyền remote URL mà thiếu --allow-remote
    with pytest.raises(ValueError) as exc:
        get_target_db_url(cli_db_url=remote_url, allow_remote=False)
    assert "Thao tác bị chặn" in str(exc.value)
    assert "super_secret_pw" not in str(exc.value)

    # 2. Cho phép khi có --allow-remote
    target = get_target_db_url(cli_db_url=remote_url, allow_remote=True)
    assert target in (remote_url, remote_url.replace('postgresql://', 'postgresql+psycopg://'))

    # 3. Khi không truyền cli_db_url, và settings.database_url là remote -> từ chối
    class FakeSettings:
        database_url = remote_url

    monkeypatch.setattr("src.cli.import_service_points.get_settings", lambda: FakeSettings())
    with pytest.raises(ValueError) as exc_env:
        get_target_db_url(cli_db_url=None, allow_remote=False)
    assert "host từ xa (production)" in str(exc_env.value)
