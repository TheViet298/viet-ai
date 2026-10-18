import pytest


@pytest.mark.asyncio
async def test_nearby_demo_distance_categories_and_privacy(client):
    url = "/api/v1/customer/service-points/nearby"
    response = await client.get(url, params={"lat": 21.0315, "lng": 105.8145, "radius_km": 50})
    assert response.status_code == 200
    points = response.json()["data"]["points"]
    assert points[0]["id"] == "SP-HN-001"
    assert points[0]["distance_km"] == 0
    assert all(point["demo"] is True for point in points)
    assert all(point["verification_status"] == "UNVERIFIED" for point in points)
    assert all(point["source"] and point["updated_at"] for point in points)
    assert {point["category"] for point in points} >= {"CHARGING_STATION", "SHOWROOM"}
    showroom = await client.get(url, params={"lat": 21.0315, "lng": 105.8145, "category": "SHOWROOM", "radius_km": 50})
    assert [point["id"] for point in showroom.json()["data"]["points"]] == ["SP-HN-002"]


@pytest.mark.asyncio
async def test_nearby_rejects_invalid_query(client):
    url = "/api/v1/customer/service-points/nearby"
    for query in ({"lat": 91, "lng": 0}, {"lat": 0, "lng": 181}, {"lat": 0, "lng": 0, "category": "RESCUE_POST"}, {"lat": 0, "lng": 0, "radius_km": 0}, {"lat": 0, "lng": 0, "limit": 0}):
        assert (await client.get(url, params=query)).status_code == 422


@pytest.fixture(autouse=True)
def explicit_demo_catalog(monkeypatch):
    monkeypatch.setenv("GPS_CATALOG_MODE", "demo")
