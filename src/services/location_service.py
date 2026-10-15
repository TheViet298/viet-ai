from __future__ import annotations

import json

from src.agents.guardrails import sanitize_pii
from src.services.session_store import get_store, now


def save_location(location: dict, owner: str) -> dict:
    store = get_store()
    case = store.case(location["case_id"], owner)
    if location["status"] == "CONSENTED" and (location["latitude"] is None or location["longitude"] is None):
        raise ValueError("Consented GPS requires latitude and longitude")
    if location["status"] == "MANUAL" and not location["location_label"].strip():
        raise ValueError("Manual location requires an area label")
    data = dict(location)
    data["location_label"] = sanitize_pii(data["location_label"])[0]
    if data["status"] != "CONSENTED":
        data["latitude"] = data["longitude"] = None
    if data["status"] == "NOT_SHARED":
        data["location_label"] = ""
    with store.connect() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS case_locations(case_id TEXT PRIMARY KEY REFERENCES cases(id), data TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        db.execute("INSERT OR REPLACE INTO case_locations VALUES(?,?,?)", (case["id"], json.dumps(data), now()))
    return data


def suggest_service_points(case_id: str, owner: str) -> list[dict]:
    store = get_store()
    case = store.case(case_id, owner)
    with store.connect() as db:
        if not db.execute("SELECT name FROM sqlite_master WHERE name='case_locations'").fetchone():
            return []
        row = db.execute("SELECT data FROM case_locations WHERE case_id=?", (case_id,)).fetchone()
    if not row or json.loads(row["data"])["status"] == "NOT_SHARED":
        return []
    from src.services.service_point_catalog import nearby_service_points
    location = json.loads(row["data"])
    centers = {"Hà Nội": (21.0285, 105.8542), "TP. Hồ Chí Minh": (10.8231, 106.6297),
               "Đà Nẵng": (16.0544, 108.2022), "Huế": (16.477861, 107.602),
               "Cao tốc Long Thành": (10.7712, 106.945)}
    if location["status"] == "CONSENTED":
        lat, lng = location["latitude"], location["longitude"]
    else:
        center = centers.get(location["location_label"])
        if not center:
            return []
        lat, lng = center
    category = "CHARGING_STATION" if case["intent"] == "Charging/Battery" else "SERVICE_WORKSHOP"
    return nearby_service_points(lat, lng, category, 50, 5)["points"]
