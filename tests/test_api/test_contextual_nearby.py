import gzip
import hashlib
import json
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db import get_db
from src.main import app
from src.services.nearby_intent import classify_location_request
from src.services.service_point_catalog import SNAPSHOT_PATH, SnapshotCatalogAdapter, nearby_service_points


@pytest.mark.asyncio
@pytest.mark.parametrize("text,expected", [
    ("Tìm trạm sạc gần đây", "CHARGING_STATION"), ("tim tru sac gan day", "CHARGING_STATION"),
    ("Quanh đây có chỗ sạc không?", "CHARGING_STATION"), ("showroom ở Huế", "SHOWROOM"),
    ("chỉ đường tới đại lý gần nhất", "SHOWROOM"), ("tìm chỗ sửa xe gần tôi", "SERVICE_WORKSHOP"),
    ("sạc bao lâu", None), ("trạm sạc là gì", None), ("hướng dẫn sạc tại trạm sạc", None),
    ("tìm hiểu trạm sạc", None), ("không tìm trạm sạc nữa", None), ("không muốn tìm showroom", None),
    ("Trạm sạc VinFast tính phí thế nào?", None), ("Trạm sạc gần tôi bị hỏng", None),
    ("Trạm sạc quanh đây không hoạt động", None), ("giá sạc tại trạm sạc", None), ("tìm nhà hàng gần đây", None), ("xin chào", None),
])
async def test_intent_positive_negative_and_unaccented(text, expected):
    result = await classify_location_request(text)
    assert (result or {}).get("category") == expected


@pytest.mark.asyncio
async def test_context_vehicle_area_and_topic_change():
    first = await classify_location_request("tìm trạm sạc xe máy gần tôi")
    assert first["vehicle_type"] == "TWO_WHEELER"
    follow = await classify_location_request("còn showroom thì sao", first, vehicle_model="VF8")
    assert follow["category"] == "SHOWROOM" and follow["vehicle_type"] == "TWO_WHEELER"
    assert await classify_location_request("bảo hành pin bao lâu", follow) is None
    area = await classify_location_request("showroom ở Huế")
    assert area["area_text"] == "Huế" and area["requires_location"] is False
    assert (await classify_location_request("chỉ đường tới chỗ đầu tiên", area))["area_text"] == "Huế"
    assert (await classify_location_request("tìm gần đây"))["category"] == "ALL"


@pytest.mark.skipif(not SNAPSHOT_PATH.exists(), reason="service_points.snapshot.csv.gz not present")
def test_snapshot_integrity_vehicle_filter_distance_and_cache():
    metadata = json.loads(SNAPSHOT_PATH.with_suffix("").with_suffix(".metadata.json").read_text())
    assert hashlib.sha256(gzip.decompress(SNAPSHOT_PATH.read_bytes())).hexdigest() == metadata["normalized_sha256"]
    adapter = SnapshotCatalogAdapter()
    catalog = adapter.load()
    assert adapter.load() is catalog
    car = [p for p in catalog.points if p.vehicle_type == "CAR"]
    assert len(car) == 17008
    assert sum(p.category == "CHARGING_STATION" for p in car) == 16657
    assert sum(p.category == "SHOWROOM" for p in car) == 351
    start = time.perf_counter()
    result = nearby_service_points(10.7769, 106.7009, "CHARGING_STATION", 50, 100)
    assert len(result["points"]) == 5
    assert result["demo"] is False and result["updated_at"] is None
    assert result["distance_method"] == "AIRLINE"
    assert all(p["vehicle_type"] == "CAR" for p in result["points"])
    assert [p["distance_km"] for p in result["points"]] == sorted(p["distance_km"] for p in result["points"])
    assert time.perf_counter() - start < 5  # Broad guard against reparse/accidental quadratic work.
    assert nearby_service_points(10.7769, 106.7009, "SERVICE_WORKSHOP", 50, 5)["points"] == []
    assert all(p["vehicle_type"] == "TWO_WHEELER" for p in nearby_service_points(21, 105.8, "ALL", 50, 5, vehicle_type="TWO_WHEELER")["points"])


@pytest.fixture
def database(tmp_path, monkeypatch):
    from src import seed
    from src.models.db_models import User, UserRole
    from src.services.auth import hash_password
    engine = create_engine(f"sqlite:///{tmp_path / 'nearby.db'}", connect_args={"check_same_thread": False})
    sessions = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(seed, "engine", engine)
    monkeypatch.setattr(seed, "SessionLocal", sessions)
    monkeypatch.setenv("DEMO_SEED_PASSWORD", "demo123456")
    seed.seed_database(demo=True)
    with sessions() as db:
        cust = User(id="test_cust_fixed", username="customer@vinfast.vn", password_hash=hash_password("customer123"), role=UserRole.CUSTOMER.value, is_demo=False)
        db.add(cust)
        db.commit()
    def override():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = override
    yield
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


@pytest.mark.asyncio
async def test_real_chat_action_followup_and_no_automatic_case(client, database):
    auth = await client.post("/api/v1/auth/login", json={"username": "customer@vinfast.vn", "password": "customer123"})
    headers = {"Authorization": f"Bearer {auth.json()['data']['token']}"}
    async def chat(message):
        response = await client.post("/api/v1/customer/chat", headers=headers, json={"session_id": "nearby-context", "message": message})
        assert response.status_code == 200, response.text
        return response.json()["data"]
    first = await chat("Tìm trạm sạc gần đây")
    assert first["case_id"] is None
    assert first["nearby_action"]["category"] == "CHARGING_STATION"
    unaccented = await chat("tim tru sac gan day")
    assert unaccented["nearby_action"]["category"] == "CHARGING_STATION"
    assert unaccented["response_type"] == "FAQ_ANSWER"
    second = await chat("còn showroom thì sao")
    assert second["nearby_action"]["category"] == "SHOWROOM"
    area = await chat("showroom ở Huế")
    assert area["nearby_action"]["area_text"] == "Huế"
    assert area["request_location"] is False
    danger = await chat("Xe đang bốc khói, tìm trạm gần đây")
    assert danger["nearby_action"] is None
    assert danger["priority"] == "CRITICAL" or danger["show_emergency_banner"]


@pytest.mark.skipif(not SNAPSHOT_PATH.exists(), reason="service_points.snapshot.csv.gz not present")
@pytest.mark.asyncio
async def test_nearby_api_snapshot_limit_empty_invalid_and_failure(client, monkeypatch):
    url = "/api/v1/customer/service-points/nearby"
    response = await client.get(url, params={"lat": 10.7769, "lng": 106.7009, "limit": 100})
    assert response.status_code == 200
    assert len(response.json()["data"]["points"]) == 5
    assert response.json()["data"]["demo"] is False
    for query in ({"lat": 91, "lng": 0}, {"lat": "nan", "lng": 0}, {"lat": 21, "lng": 105, "vehicle_type": "BIKE"}):
        assert (await client.get(url, params=query)).status_code == 422
    def broken(self):
        raise ValueError("private catalog detail")
    monkeypatch.setattr(SnapshotCatalogAdapter, "load", broken)
    response = await client.get(url, params={"lat": 21, "lng": 105})
    assert response.status_code == 503 and "private catalog detail" not in response.text


@pytest.mark.asyncio
async def test_optional_model_fallback_validates_confidence_and_keeps_unsupported_places_out(monkeypatch):
    from src.services import nearby_intent
    calls = []
    async def classify(state, prompt, schema):
        calls.append(state)
        assert state["latest_user_message"] == "Em cần ghé showroom"
        return schema(find_nearby=True, category="SHOWROOM", confidence=0.95)
    monkeypatch.setattr(nearby_intent, "structured_call", classify)
    assert (await classify_location_request("Em cần ghé showroom"))["category"] == "SHOWROOM"
    assert await classify_location_request("Tìm khách sạn gần đây") is None
    assert await classify_location_request("Trạm sạc VinFast tính phí thế nào?") is None
    assert len(calls) == 1
    async def uncertain(*args):
        return nearby_intent.LocationClassification(find_nearby=True, category="SHOWROOM", confidence=0.6)
    monkeypatch.setattr(nearby_intent, "structured_call", uncertain)
    assert await classify_location_request("Em cần ghé showroom") is None
