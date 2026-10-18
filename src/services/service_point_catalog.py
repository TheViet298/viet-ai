"""Shared nearby engine with cached, checksummed CSV snapshot and explicit demo mode.

Source status never asserts live availability; unknown source dates remain null.
"""

import csv
import gzip
import hashlib
import io
import json
import math
import os
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.schemas import ServicePointItem

CATALOG_PATH = Path(__file__).resolve().parents[2] / "fixtures/nearby_service_points.demo.json"


class CatalogMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source: str = Field(min_length=1)
    updated_at: date | None
    imported_at: date | None = None
    verification_status: Literal["UNVERIFIED", "SNAPSHOT", "VERIFIED"]
    demo: bool

    @model_validator(mode="after")
    def demo_is_unverified(self):
        if self.demo and self.verification_status != "UNVERIFIED":
            raise ValueError("Demo catalogs cannot be verified")
        return self


class CatalogPoint(ServicePointItem):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    address: str = Field(min_length=1)
    category: Literal["CHARGING_STATION", "SHOWROOM", "SERVICE_WORKSHOP", "OTHER"]
    vehicle_type: Literal["CAR", "TWO_WHEELER", "ANY"] = "ANY"
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


SNAPSHOT_PATH = CATALOG_PATH.parent / "gps/service_points.snapshot.csv.gz"


@lru_cache(maxsize=2)
def _load_snapshot(path: str, modified: int, metadata_modified: int, size: int) -> Catalog:
    snapshot = Path(path)
    provenance = json.loads(snapshot.with_suffix("").with_suffix(".metadata.json").read_text())
    normalized = gzip.decompress(snapshot.read_bytes())
    if hashlib.sha256(normalized).hexdigest() != provenance["normalized_sha256"]:
        raise ValueError("Snapshot checksum mismatch")
    points = []
    with io.StringIO(normalized.decode("utf-8"), newline="") as handle:
        for row in csv.DictReader(handle):
            # Re-check source conditions; do not trust a generated candidate flag.
            if row["vehicle_type"] not in {"CAR", "TWO_WHEELER"} or row["quality_flags"]:
                continue
            if row["source_status"].casefold() not in {"true", "1"}:
                continue
            if row["category"] == "CHARGING_STATION" and (
                row["charging_status"] != "ACTIVE" or row["access_type"] != "Public"
                or row["charging_publish"] != "True"
            ):
                continue
            points.append(CatalogPoint(
                id=row["id"], name=row["name"], address=row["address"], category=row["category"],
                latitude=float(row["latitude"]), longitude=float(row["longitude"]),
                vehicle_type=row["vehicle_type"],
            ))
    return Catalog(metadata=CatalogMetadata(source=provenance["source"], updated_at=None,
                   imported_at=provenance["imported_at"], verification_status="UNVERIFIED", demo=False), points=points)


class SnapshotCatalogAdapter:
    def __init__(self, path: Path = SNAPSHOT_PATH):
        self.path = path

    def load(self) -> Catalog:
        stat = self.path.stat()
        # A metadata change also invalidates the cache.
        metadata_stat = self.path.with_suffix("").with_suffix(".metadata.json").stat()
        return _load_snapshot(str(self.path), stat.st_mtime_ns, metadata_stat.st_mtime_ns, stat.st_size)


def default_catalog_adapter() -> CatalogAdapter:
    mode = os.environ.get("GPS_CATALOG_MODE", "auto").strip().lower()
    if mode == "demo":
        return JsonCatalogAdapter()
    if mode == "snapshot":
        return SnapshotCatalogAdapter()
    if mode in ("auto", "db"):
        if SNAPSHOT_PATH.exists():
            return SnapshotCatalogAdapter()
        return JsonCatalogAdapter()
    raise ValueError("Unsupported GPS catalog mode")


def nearby_service_points(
    lat: float, lng: float, category: str, radius_km: float, limit: int,
    adapter: CatalogAdapter | None = None, vehicle_type: str = "CAR",
) -> dict:
    catalog = (adapter or default_catalog_adapter()).load()
    if not all(math.isfinite(v) for v in (lat, lng, radius_km)) or abs(lat) > 90 or abs(lng) > 180 or radius_km <= 0:
        raise ValueError("Invalid search coordinates")
    if vehicle_type not in {"CAR", "TWO_WHEELER"}:
        raise ValueError("Unsupported vehicle type")
    limit = min(5, max(1, limit))
    metadata = catalog.metadata.model_dump(mode="json")
    matches = []
    for point in catalog.points:
        if point.vehicle_type not in {"ANY", vehicle_type}:
            continue
        if category != "ALL" and point.category != category:
            continue
        dlat, dlng = math.radians(point.latitude - lat), math.radians(point.longitude - lng)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(point.latitude)) * math.sin(dlng / 2) ** 2
        km = 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0, 1 - a)))
        if km <= radius_km:
            matches.append((km, {**point.model_dump(), **metadata, "distance_km": round(km, 3)}))
    matches.sort(key=lambda entry: (entry[0], entry[1]["id"]))
    catalog_source = "demo" if metadata.get("demo") else "snapshot"
    return {"points": [point for _, point in matches[:limit]], **metadata,
            "distance_method": "AIRLINE", "radius_km": radius_km, "limit": limit, "vehicle_type": vehicle_type,
            "meta": {"catalog_source": catalog_source}}
