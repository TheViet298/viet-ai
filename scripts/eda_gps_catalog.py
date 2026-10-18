"""Profile supplied GPS exports and prepare a staging dataset; no runtime changes."""

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def profile(input_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {"generated_at": datetime.now(UTC).isoformat(),
               "source_export_date": None, "verification_status": "UNVERIFIED",
               "files": {}, "notes": [
                   "Vietnam bounding box is a screening heuristic, not a national boundary.",
                   "Source status is a snapshot, not live availability.",
                   "No hotline, CRM identifiers, URLs or nested source objects are copied.",
                   "Normalized rows are staging data, not the active application catalog."]}
    normalized, issues = [], []
    for filename in ("vinfast_showrooms.csv", "vinfast_tramsac.csv"):
        source = input_dir / filename
        with source.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames
            rows = list(reader)
        info = {"rows": len(rows), "columns": len(columns),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "missing": {c: sum(not (r.get(c) or "").strip() for r in rows) for c in columns},
                "distinct_nonempty": {c: len({r[c].strip() for r in rows if r.get(c, "").strip()}) for c in columns},
                "distributions": {c: dict(Counter(r[c] or "<missing>" for r in rows)) for c in
                                  ("bundle", "category_slug", "category_name", "status", "charging_status",
                                   "charging_publish", "access_type", "parking_fee", "province_id", "store_type")},
                "duplicates": {c: sum(n - 1 for n in Counter(r[c].strip() for r in rows if r[c].strip()).values())
                               for c in ("entity_id", "code", "store_id", "name", "address")},
                "exact_duplicate_rows": len(rows) - len({tuple(r.get(c) for c in columns) for r in rows}),
                "malformed_rows": sum(None in r or any(r.get(c) is None for c in columns) for r in rows)}
        valid_coords, flags_count = [], Counter()
        for line, row in enumerate(rows, 2):
            flags = []
            lat = lng = None
            try:
                lat, lng = float(row["lat"]), float(row["lng"])
                if not (math.isfinite(lat) and math.isfinite(lng) and abs(lat) <= 90 and abs(lng) <= 180):
                    raise ValueError("Invalid coordinates")
                valid_coords.append((lat, lng))
                if not (8 <= lat <= 24 and 102 <= lng <= 110):
                    flags.append("outside_vietnam_screen")
            except (ValueError, TypeError):
                lat = lng = None
                flags.append("invalid_coordinates")
            slug = row["category_slug"]
            category = "SHOWROOM" if slug.startswith("showroom_") else "BATTERY_SWAP" if slug == "battery_swap_station" else "CHARGING_STATION"
            vehicle = ("CAR" if slug in ("car_charging_station", "showroom_car")
                       else "UNKNOWN" if slug == "battery_swap_station" else "TWO_WHEELER")
            if row["status"].casefold() not in ("1", "true"):
                flags.append("source_disabled")
            if row["charging_publish"] == "False":
                flags.append("not_published")
            if row["access_type"] == "Restricted":
                flags.append("restricted_access")
            if category == "CHARGING_STATION" and row["charging_status"] != "ACTIVE":
                flags.append("charging_not_active")
            if category == "BATTERY_SWAP":
                flags.append("availability_unknown")
            if not row["name"].strip() or not row["address"].strip():
                flags.append("missing_identity")
            flags_count.update(flags)
            point_id = f"{row['bundle']}:{row['entity_id']}"
            normalized.append({"id": point_id, "name": row["name"].strip(), "address": row["address"].strip(),
                               "latitude": lat, "longitude": lng, "category": category, "vehicle_type": vehicle,
                               "source_category": slug, "province_id": row["province_id"],
                               "source_status": row["status"], "charging_status": row["charging_status"],
                               "access_type": row["access_type"], "charging_publish": row["charging_publish"],
                               "parking_fee": row["parking_fee"], "service_capability_codes": row["multiple_type"],
                               "open_time_service": row["open_time_service"], "close_time_service": row["close_time_service"],
                               "open_time_sales": row["open_time_sales"], "close_time_sales": row["close_time_sales"],
                               "verification_status": "UNVERIFIED", "source_file": filename, "source_row": line,
                               "quality_flags": "|".join(flags),
                               "candidate_car_default": vehicle == "CAR" and not flags})
            for flag in flags:
                issues.append({"source_file": filename, "source_row": line, "id": point_id, "issue": flag})
        info["quality_flags"] = dict(flags_count)
        info["coordinate_bounds"] = {"latitude": [min(p[0] for p in valid_coords), max(p[0] for p in valid_coords)],
                                     "longitude": [min(p[1] for p in valid_coords), max(p[1] for p in valid_coords)]}
        summary["files"][filename] = info
    coords = Counter((p["latitude"], p["longitude"]) for p in normalized if p["latitude"] is not None)
    summary["combined"] = {"rows": len(normalized),
                           "duplicate_normalized_ids": len(normalized) - len({p["id"] for p in normalized}),
                           "shared_coordinate_groups": sum(n > 1 for n in coords.values()),
                           "shared_coordinate_excess_rows": sum(n - 1 for n in coords.values()),
                           "candidate_car_default": dict(Counter(p["source_category"] for p in normalized if p["candidate_car_default"])),
                           "quarantined_coordinate_rows": sum("coordinates" in p["quality_flags"] or "outside_vietnam" in p["quality_flags"] for p in normalized)}
    for name, records in (("service_points.normalized.csv", normalized), ("quality_issues.csv", issues)):
        with (output_dir / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    (output_dir / "eda-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/gps"))
    parser.add_argument("--runtime-dir", type=Path)
    args = parser.parse_args()
    result = profile(args.input_dir, args.output_dir)
    if args.runtime_dir:
        import gzip
        args.runtime_dir.mkdir(parents=True, exist_ok=True)
        normalized = (args.output_dir / "service_points.normalized.csv").read_bytes()
        (args.runtime_dir / "service_points.snapshot.csv.gz").write_bytes(gzip.compress(normalized, mtime=0))
        metadata = {"source": "User-supplied VinFast location CSV snapshot; export date unknown",
                    "imported_at": result["generated_at"][:10], "updated_at": None,
                    "verification_status": "UNVERIFIED", "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
                    "input_files": {k: {"sha256": v["sha256"], "rows": v["rows"]} for k, v in result["files"].items()},
                    "rows": result["combined"]["rows"]}
        (args.runtime_dir / "service_points.snapshot.metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files": {k: {"rows": v["rows"], "quality_flags": v["quality_flags"]} for k, v in result["files"].items()},
                      "combined": result["combined"]}, ensure_ascii=False, indent=2))
