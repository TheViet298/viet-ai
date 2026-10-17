import json

import pytest
from pydantic import ValidationError

from src.services.service_point_catalog import (
    CATALOG_PATH,
    Catalog,
    JsonCatalogAdapter,
    nearby_service_points,
)


def test_canonical_catalog_metadata_and_nearby_distance():
    catalog = JsonCatalogAdapter().load()
    result = nearby_service_points(21.0315, 105.8145, "ALL", 50, 1)
    assert result["source"] == catalog.metadata.source
    assert result["updated_at"] == "2026-10-13"
    assert result["verification_status"] == "UNVERIFIED"
    assert result["demo"] is True
    assert len(result["points"]) == 1
    point = result["points"][0]
    assert point["id"] == "SP-HN-001"
    assert point["distance_km"] == 0
    for field in ("source", "updated_at", "verification_status", "demo"):
        assert point[field] == result[field]


@pytest.mark.parametrize("invalid", ["verified_demo", "coordinates", "duplicate", "date"])
def test_invalid_catalog_is_rejected(invalid):
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if invalid == "verified_demo":
        data["metadata"]["verification_status"] = "VERIFIED"
    elif invalid == "coordinates":
        data["points"][0]["latitude"] = 91
    elif invalid == "duplicate":
        data["points"].append(data["points"][0])
    else:
        data["metadata"]["updated_at"] = "unknown"
    with pytest.raises(ValidationError):
        Catalog.model_validate(data)


def test_adapter_preserves_unverified_non_demo_metadata():
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    data["metadata"].update(demo=False, source="Test adapter; no operational verification")

    class TestAdapter:
        def load(self):
            return Catalog.model_validate(data)

    result = nearby_service_points(21.0315, 105.8145, "SHOWROOM", 50, 10, TestAdapter())
    assert [point["id"] for point in result["points"]] == ["SP-HN-002"]
    assert result["demo"] is False
    assert result["verification_status"] == "UNVERIFIED"
    assert nearby_service_points(0, 0, "ALL", 1, 10, TestAdapter())["points"] == []


@pytest.mark.parametrize("field", ["source", "id", "name", "address"])
def test_blank_provenance_or_identity_cannot_be_marked_verified(field):
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    data["metadata"].update(demo=False, verification_status="VERIFIED")
    target = data["metadata"] if field == "source" else data["points"][0]
    target[field] = "   "
    with pytest.raises(ValidationError):
        Catalog.model_validate(data)


@pytest.mark.asyncio
async def test_catalog_failure_returns_unavailable_not_verified_points(client, monkeypatch):
    def broken_catalog(self):
        raise ValueError("invalid catalog data")

    monkeypatch.setattr(JsonCatalogAdapter, "load", broken_catalog)
    response = await client.get("/api/v1/customer/service-points/nearby", params={"lat": 21, "lng": 105})
    assert response.status_code == 503
    assert "points" not in response.json()
    assert "invalid catalog data" not in response.text


@pytest.fixture(autouse=True)
def explicit_demo_catalog(monkeypatch):
    monkeypatch.setenv("GPS_CATALOG_MODE", "demo")
