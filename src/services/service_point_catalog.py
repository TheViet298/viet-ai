"""Nearby directory adapter, separate from the agent's intent-based fixtures.

The bundled catalog is illustrative and never asserts live availability. The
revision date refers to this fixture, not to on-site verification.
"""

import math
from datetime import date
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.schemas import ServicePointItem

CATALOG_PATH = Path(__file__).resolve().parents[2] / "fixtures/nearby_service_points.demo.json"


class CatalogMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(min_length=1)
    updated_at: date
    verification_status: Literal["UNVERIFIED", "VERIFIED"]
    demo: bool

    @model_validator(mode="after")
    def demo_is_unverified(self):
        if self.demo and self.verification_status != "UNVERIFIED":
            raise ValueError("Demo catalogs cannot be verified")
        return self


class CatalogPoint(ServicePointItem):
    model_config = ConfigDict(extra="forbid")
    category: Literal["CHARGING_STATION", "SHOWROOM", "SERVICE_WORKSHOP", "OTHER"]
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metadata: CatalogMetadata
    points: list[CatalogPoint]

    @model_validator(mode="after")
    def unique_ids(self):
        if len({point.id for point in self.points}) != len(self.points):
            raise ValueError("Duplicate service point IDs")
        return self


class CatalogAdapter(Protocol):
    def load(self) -> Catalog: ...


class JsonCatalogAdapter:
    def __init__(self, path: Path = CATALOG_PATH):
        self.path = path

    def load(self) -> Catalog:
        return Catalog.model_validate_json(self.path.read_text(encoding="utf-8"))


def nearby_service_points(
    lat: float, lng: float, category: str, radius_km: float, limit: int,
    adapter: CatalogAdapter | None = None,
) -> dict:
    catalog = (adapter or JsonCatalogAdapter()).load()
    metadata = catalog.metadata.model_dump(mode="json")
    matches = []
    for point in catalog.points:
        if category != "ALL" and point.category != category:
            continue
        dlat, dlng = math.radians(point.latitude - lat), math.radians(point.longitude - lng)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(point.latitude)) * math.sin(dlng / 2) ** 2
        km = 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0, 1 - a)))
        if km <= radius_km:
            matches.append((km, {**point.model_dump(), **metadata, "distance_km": round(km, 3)}))
    matches.sort(key=lambda entry: (entry[0], entry[1]["id"]))
    return {"points": [point for _, point in matches[:limit]], **metadata}
