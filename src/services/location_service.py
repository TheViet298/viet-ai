from __future__ import annotations

import json
from pathlib import Path

from src.agents.guardrails import sanitize_pii
from src.config import get_settings
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
    path = Path(get_settings().service_points_file)
    if not path.exists():
        return []
    location = json.loads(row["data"])
    points = json.loads(path.read_text(encoding="utf-8"))
    matched = [
        p
        for p in points
        if p.get("name")
        and p.get("address")
        and case["intent"] in p.get("intents", [])
        and (not location["location_label"] or location["location_label"].casefold() in p.get("area", "").casefold())
    ]
    if location["status"] == "CONSENTED":
        matched = [
            p
            for p in matched
            if isinstance(p.get("latitude"), (int, float)) and isinstance(p.get("longitude"), (int, float))
        ]
        matched.sort(
            key=lambda p: (p["latitude"] - location["latitude"]) ** 2 + (p["longitude"] - location["longitude"]) ** 2
        )
    return matched[:5]
