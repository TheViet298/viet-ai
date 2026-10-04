#!/usr/bin/env python3
"""
Kiểm thử tính toàn vẹn và hợp lệ của Bộ dữ liệu nhận diện ảnh táp-lô VinFast
(dataset/img_warning_taplo)
"""

import csv
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN", "INFO"}
REQUIRED_TPMS_SYMPTOMS = {
    "rapid_leak",
    "low_pressure",
    "over_pressure",
    "high_temperature",
    "sensor_fault",
    "sensor_battery_low",
    "tpms_system_error",
}
SELECTED_MODELS = {"VinFast VF e34", "VinFast VF 8", "VinFast VF 5 Plus"}


def verify_tpms_dataset(base_dir: Path) -> dict:
    tpms_file = base_dir / "tpms_dataset.json"
    if not tpms_file.exists():
        raise FileNotFoundError(f"Missing {tpms_file}")

    with open(tpms_file, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("tpms_dataset.json must be a non-empty JSON array")

    ids = set()
    symptoms_by_model = {model: set() for model in SELECTED_MODELS}
    severity_counts = {}

    required_fields = [
        "id",
        "vehicle_model",
        "warning_group",
        "symptom_key",
        "warning_name_vi",
        "severity",
        "immediate_actions",
        "chatbot_response_template",
        "source_reference",
    ]

    for item in data:
        for field in required_fields:
            if field not in item:
                raise KeyError(f"Item {item.get('id')} missing required field: {field}")

        item_id = item["id"]
        if item_id in ids:
            raise ValueError(f"Duplicate id in tpms_dataset.json: {item_id}")
        ids.add(item_id)

        model = item["vehicle_model"]
        if model not in SELECTED_MODELS:
            raise ValueError(f"Unknown vehicle_model: {model}")

        symptom = item["symptom_key"]
        symptoms_by_model[model].add(symptom)

        sev = item["severity"]
        if sev not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{sev}' in item {item_id}")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Check completeness of the 7 TPMS symptoms for each selected model
    for model, symptoms in symptoms_by_model.items():
        missing = REQUIRED_TPMS_SYMPTOMS - symptoms
        if missing:
            raise ValueError(f"Model {model} is missing TPMS symptoms: {missing}")

    return {
        "total_records": len(data),
        "unique_ids": len(ids),
        "severity_distribution": severity_counts,
        "models_covered": list(symptoms_by_model.keys()),
    }


def verify_dashboard_full_dataset(base_dir: Path) -> dict:
    full_file = base_dir / "dashboard_warnings_full.json"
    if not full_file.exists():
        raise FileNotFoundError(f"Missing {full_file}")

    with open(full_file, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("dashboard_warnings_full.json must be a non-empty JSON array")

    ids = set()
    required_fields = [
        "id",
        "vehicle_model",
        "warning_category",
        "symptom_key",
        "warning_name_vi",
        "indicator_color",
        "severity",
        "display_text",
        "action_summary",
        "source_url",
    ]

    severity_counts = {}
    category_counts = {}

    for item in data:
        for field in required_fields:
            if field not in item:
                raise KeyError(f"Item {item.get('id')} missing required field: {field}")

        item_id = item["id"]
        if item_id in ids:
            raise ValueError(f"Duplicate id in dashboard_warnings_full.json: {item_id}")
        ids.add(item_id)

        sev = item["severity"]
        if sev not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{sev}' in item {item_id}")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

        cat = item["warning_category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "total_records": len(data),
        "unique_ids": len(ids),
        "severity_distribution": severity_counts,
        "category_distribution": category_counts,
    }


def verify_csv_labels(base_dir: Path, expected_count: int) -> None:
    csv_file = base_dir / "dataset_labels.csv"
    if not csv_file.exists():
        raise FileNotFoundError(f"Missing {csv_file}")

    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if len(rows) != expected_count:
        raise ValueError(
            f"CSV row count ({len(rows)}) does not match full json count ({expected_count})"
        )


def verify_image_catalog(base_dir: Path) -> dict:
    catalog_file = base_dir / "images" / "image_catalog.json"
    if not catalog_file.exists():
        raise FileNotFoundError(f"Missing {catalog_file}")

    with open(catalog_file, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("image_catalog.json must be a non-empty list")

    for img in data:
        assert "image_id" in img
        assert "source_url" in img
        assert "visual_elements" in img

    return {"cataloged_images": len(data)}


def main():
    base_dir = Path(__file__).resolve().parent
    print("============================================================")
    print(f"  KIỂM THỬ DATASET TÁP-LÔ VINFAST: {base_dir}")
    print("============================================================")

    try:
        tpms_res = verify_tpms_dataset(base_dir)
        print("✅ 1. TPMS Dataset: HỢP LỆ")
        print(f"   - Tổng số bản ghi TPMS: {tpms_res['total_records']}")
        print(f"   - Mẫu xe bảo đảm độ phủ: {tpms_res['models_covered']}")
        print(f"   - Phân bố Severity TPMS: {tpms_res['severity_distribution']}")

        full_res = verify_dashboard_full_dataset(base_dir)
        print("\n✅ 2. Dashboard Warnings Full Dataset: HỢP LỆ")
        print(f"   - Tổng số bản ghi toàn diện: {full_res['total_records']}")
        print(f"   - Phân bố Severity: {full_res['severity_distribution']}")
        print(f"   - Phân bố Phân nhóm: {full_res['category_distribution']}")

        verify_csv_labels(base_dir, full_res["total_records"])
        print(f"\n✅ 3. CSV Dataset Labels: HỢP LỆ ({full_res['total_records']} dòng)")

        img_res = verify_image_catalog(base_dir)
        print(f"\n✅ 4. Image Catalog: HỢP LỆ ({img_res['cataloged_images']} ảnh tham chiếu)")

        print("\n============================================================")
        print("🎉 TẤT CẢ KIỂM THỬ THÀNH CÔNG! Dataset sẵn sàng cho PR.")
        print("============================================================")
    except Exception as e:
        print(f"\n❌ LỖI KIỂM THỬ: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
