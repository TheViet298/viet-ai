"""CLI tool for one-off importing VinFast service points (charging stations, showrooms, 2S workshops).

Usage:
    python -m src.cli.import_service_points --path data/crawl
"""
import argparse
import ast
from datetime import UTC, datetime
import hashlib
import os
from pathlib import Path
import re
import sys
from typing import Any
import unicodedata

if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.config import get_settings
from src.models.db_models import ServicePoint, utcnow


def generate_point_id(source_file: str, source_id: str | None, name: str, lat: float, lng: float) -> str:
    if source_id and str(source_id).strip() and str(source_id).strip() != "nan":
        return f"{source_file}:{str(source_id).strip()}"
    raw = f"{name.strip().lower()}_{round(lat, 6)}_{round(lng, 6)}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"{source_file}:{digest}"


def normalize_name(s: Any) -> str:
    if not isinstance(s, str):
        return ""
    norm = unicodedata.normalize("NFC", s).strip().lower()
    return re.sub(r"\s+", " ", norm)


def normalize_phone(raw: Any) -> str | None:
    if not raw or pd.isna(raw):
        return None
    val = str(raw).strip()
    if val in ["nan", "None", "", "[]"]:
        return None

    digits = re.sub(r"\D", "", val)
    if not digits:
        return None

    if digits.startswith(("1900", "1800")):
        return digits

    if len(digits) == 9 and digits[0] in "35789":
        return "0" + digits

    if len(digits) in (10, 11):
        return digits

    return digits


def normalize_time_str(val: Any) -> str | None:
    if not val or pd.isna(val):
        return None
    s = str(val).strip().lower()
    if s in ["nan", "none", "", "[]"]:
        return None
    m = re.match(r"^(\d{1,2})[h:](\d{2})$", s)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    m2 = re.match(r"^(\d{1,2})h$", s)
    if m2:
        return f"{int(m2.group(1)):02d}:00"
    m3 = re.match(r"^(\d{1,2}):(\d{2}):\d{2}$", s)
    if m3:
        return f"{int(m3.group(1)):02d}:{m3.group(2)}"
    return s


def format_operating_hours(open_val: Any, close_val: Any) -> str | None:
    op = normalize_time_str(open_val)
    cl = normalize_time_str(close_val)
    if op and cl:
        return f"{op} - {cl}"
    if op:
        return f"{op} -"
    if cl:
        return f"- {cl}"
    return None


def extract_booking_url(val: Any) -> str | None:
    if not val or pd.isna(val) or str(val).strip() in ["[]", ""]:
        return None
    raw = str(val).strip()
    try:
        data = ast.literal_eval(raw)
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            return data[0].get("href")
    except Exception:
        pass
    m = re.search(r"['\"]href['\"]\s*:\s*['\"]([^'\"]+)['\"]", raw)
    if m:
        return m.group(1)
    return None


def mask_phone_for_log(phone: str | None) -> str | None:
    if not phone:
        return None
    if len(phone) > 4:
        return phone[:-4] + "****"
    return "****"


def parse_service_points(
    crawl_dir: Path,
    cli_crawled_at: datetime | None = None,
    suspect_hide: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stats = {}

    # 1. Charging Stations
    ts_file = crawl_dir / "vinfast_tramsac.csv"
    if not ts_file.exists():
        ts_file = crawl_dir / "vinfast_charging_stations.csv"
    if not ts_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file trạm sạc trong {crawl_dir}")

    ts_mtime = cli_crawled_at or datetime.fromtimestamp(os.path.getmtime(ts_file), tz=UTC)
    df_ts = pd.read_csv(ts_file, dtype=str, low_memory=False)
    total_ts_raw = len(df_ts)
    df_ts_car = df_ts[df_ts["category_slug"] == "car_charging_station"].copy()
    ts_car_count = len(df_ts_car)
    ts_skipped = total_ts_raw - ts_car_count
    stats["charging_stations"] = {"raw": total_ts_raw, "loaded": ts_car_count, "skipped": ts_skipped}

    # 2. Showrooms
    sr_file = crawl_dir / "vinfast_showrooms.csv"
    if not sr_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file showroom trong {crawl_dir}")

    sr_mtime = cli_crawled_at or datetime.fromtimestamp(os.path.getmtime(sr_file), tz=UTC)
    df_sr = pd.read_csv(sr_file, dtype=str, low_memory=False)
    total_sr_raw = len(df_sr)
    df_sr_car = df_sr[df_sr["category_slug"] == "showroom_car"].copy()
    sr_car_count = len(df_sr_car)
    sr_skipped = total_sr_raw - sr_car_count
    stats["showrooms"] = {"raw": total_sr_raw, "loaded": sr_car_count, "skipped": sr_skipped}

    # 3. 2S Workshops
    s2_file = crawl_dir / "vinfast_xuong_dich_vu_2s.csv"
    if not s2_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file xưởng 2S trong {crawl_dir}")

    s2_mtime = cli_crawled_at or datetime.fromtimestamp(os.path.getmtime(s2_file), tz=UTC)
    df_2s = pd.read_csv(s2_file, dtype=str, low_memory=False)
    total_2s_raw = len(df_2s)
    df_2s_car = df_2s[df_2s["category_slug"].isin(["service_car", "service_car_partner", "service_gsm"])].copy()

    df_2s_car["norm_name"] = df_2s_car["name"].apply(normalize_name)
    df_2s_car["lat_r"] = df_2s_car["lat"].astype(float).round(6)
    df_2s_car["lng_r"] = df_2s_car["lng"].astype(float).round(6)
    df_2s_car["entity_id_int"] = df_2s_car["entity_id"].astype(int)
    df_2s_car = df_2s_car.sort_values("entity_id_int", ascending=True)
    df_2s_dedup = df_2s_car.drop_duplicates(subset=["norm_name", "lat_r", "lng_r"], keep="first")
    s2_car_count = len(df_2s_dedup)
    s2_skipped = total_2s_raw - s2_car_count
    stats["service_2s"] = {"raw": total_2s_raw, "loaded": s2_car_count, "skipped": s2_skipped}

    records: list[dict[str, Any]] = []

    # Process Charging Stations
    for _, row in df_ts_car.iterrows():
        ent_id = str(row["entity_id"]).strip() if pd.notna(row.get("entity_id")) else None
        lat = float(row["lat"])
        lng = float(row["lng"])
        pt_id = generate_point_id("charging_stations", ent_id, str(row["name"]), lat, lng)

        status_val = str(row["charging_status"]).strip() if pd.notna(row.get("charging_status")) else "ACTIVE"
        access_val = str(row["access_type"]).strip() if pd.notna(row.get("access_type")) else "Public"
        if access_val == "nan" or not access_val:
            access_val = "Public"

        is_vis = (status_val in ["ACTIVE", "BUSY"]) and (access_val != "Restricted")
        hours = format_operating_hours(row.get("open_time_service"), row.get("close_time_service"))
        phone = normalize_phone(row.get("hotline"))

        records.append({
            "id": pt_id,
            "source_file": "charging_stations",
            "source_id": ent_id,
            "category": "charging_station",
            "category_name": str(row.get("category_name", "Trạm sạc ô tô")),
            "category_slug": str(row.get("category_slug", "car_charging_station")),
            "name": str(row["name"]).strip(),
            "address": str(row["address"]).strip(),
            "latitude": lat,
            "longitude": lng,
            "phone": phone,
            "hotline_service": None,
            "booking_url": None,
            "dong_son": False,
            "operating_hours": hours,
            "services_offered": ["charging"],
            "status": status_val,
            "access_type": access_val,
            "is_car_compatible": True,
            "is_visible": is_vis,
            "extra_metadata": {
                "store_id": str(row.get("store_id", "")),
                "code": str(row.get("code", "")),
                "parking_fee": str(row.get("parking_fee", "")) if pd.notna(row.get("parking_fee")) else None,
            },
            "crawled_at": ts_mtime,
        })

    # Process Showrooms
    for _, row in df_sr_car.iterrows():
        ent_id = str(row["entity_id"]).strip() if pd.notna(row.get("entity_id")) else None
        lat = float(row["lat"])
        lng = float(row["lng"])
        pt_id = generate_point_id("showrooms", ent_id, str(row["name"]), lat, lng)

        hours = format_operating_hours(row.get("open_time_sales"), row.get("close_time_sales"))
        phone = normalize_phone(row.get("hotline"))

        records.append({
            "id": pt_id,
            "source_file": "showrooms",
            "source_id": ent_id,
            "category": "showroom",
            "category_name": str(row.get("category_name", "Showroom ô tô")),
            "category_slug": str(row.get("category_slug", "showroom_car")),
            "name": str(row["name"]).strip(),
            "address": str(row["address"]).strip(),
            "latitude": lat,
            "longitude": lng,
            "phone": phone,
            "hotline_service": None,
            "booking_url": None,
            "dong_son": False,
            "operating_hours": hours,
            "services_offered": ["sales"],
            "status": "ACTIVE",
            "access_type": "Public",
            "is_car_compatible": True,
            "is_visible": True,
            "extra_metadata": {
                "store_id": str(row.get("store_id", "")),
                "code": str(row.get("code", "")),
            },
            "crawled_at": sr_mtime,
        })

    # Process 2S Workshops (Category: workshop)
    for _, row in df_2s_dedup.iterrows():
        ent_id = str(row["entity_id"]).strip() if pd.notna(row.get("entity_id")) else None
        lat = float(row["lat"])
        lng = float(row["lng"])
        pt_id = generate_point_id("service_2s", ent_id, str(row["name"]), lat, lng)

        hours = format_operating_hours(row.get("open_time_service"), row.get("close_time_service"))
        phone = normalize_phone(row.get("hotline"))
        hotline_xdv = normalize_phone(row.get("hotline_xdv"))

        b_url = extract_booking_url(row.get("button_action"))
        is_dong_son = str(row.get("dong_son", "")).strip().lower() == "true"

        services = ["maintenance", "repair"]
        if is_dong_son:
            services.append("dong_son")
        if b_url:
            services.append("booking")

        records.append({
            "id": pt_id,
            "source_file": "service_2s",
            "source_id": ent_id,
            "category": "workshop",
            "category_name": str(row.get("category_name", "Xưởng dịch vụ 2S")),
            "category_slug": str(row.get("category_slug", "service_car")),
            "name": str(row["name"]).strip(),
            "address": str(row["address"]).strip(),
            "latitude": lat,
            "longitude": lng,
            "phone": phone,
            "hotline_service": hotline_xdv,
            "booking_url": b_url,
            "dong_son": is_dong_son,
            "operating_hours": hours,
            "services_offered": services,
            "status": "ACTIVE",
            "access_type": "Public",
            "is_car_compatible": True,
            "is_visible": True,
            "extra_metadata": {
                "store_id": str(row.get("store_id", "")),
                "code": str(row.get("code", "")),
            },
            "crawled_at": s2_mtime,
        })

    if suspect_hide:
        suspect_info = apply_suspect_coordinate_rule(records, suspect_hide=True)
        stats["suspect_info"] = suspect_info

    return records, stats


def apply_suspect_coordinate_rule(
    records: list[dict[str, Any]],
    suspect_hide: bool = True,
    max_threshold: int = 300,
) -> dict[str, Any]:
    """Áp quy tắc phát hiện và xử lý tọa độ đáng ngờ:
    - KNN-5: 5 láng giềng đồng thuận cùng 1 tỉnh khác tỉnh trong address.
    - Khoảng cách tới trạm gần nhất cùng tỉnh theo address > 50 km.
    - Gắn extra_metadata['coordinate_suspect'] = True.
    - Nếu tổng số trạm đáng ngờ <= max_threshold (300) và suspect_hide=True:
      gán is_visible = False.
    - Nếu tổng số trạm đáng ngờ > max_threshold: tắt tự động ẩn, chỉ gắn cờ/báo cáo.
    """
    from collections import Counter
    from scipy.spatial import KDTree
    from src.services.service_point_service import detect_province_from_address, haversine_km

    charging_stations = [r for r in records if r.get("category_slug") == "car_charging_station"]

    valid_stations = []
    coords = []
    stations_by_prov: dict[str, list[tuple[str, float, float]]] = {}

    for r in charging_stations:
        lat = r.get("latitude")
        lng = r.get("longitude")
        if lat is None or lng is None:
            continue
        prov = detect_province_from_address(r.get("address", ""))
        if not prov:
            continue
        valid_stations.append({
            "record": r,
            "lat": lat,
            "lng": lng,
            "prov": prov,
        })
        coords.append([lat, lng])
        stations_by_prov.setdefault(prov, []).append((r["id"], lat, lng))

    if len(coords) < 6:
        return {"total_suspects": 0, "newly_hidden": 0, "new_visible": sum(1 for r in charging_stations if r["is_visible"]), "breakdown": {}}

    tree = KDTree(coords)
    distances, indices = tree.query(coords, k=6)

    suspect_candidates = []
    for idx, st in enumerate(valid_stations):
        neighbor_indices = indices[idx][1:6]
        neighbor_provinces = [valid_stations[n_idx]["prov"] for n_idx in neighbor_indices]
        if len(neighbor_provinces) == 5 and len(set(neighbor_provinces)) == 1:
            dom_prov = neighbor_provinces[0]
            if dom_prov != st["prov"]:
                same_prov_list = stations_by_prov.get(st["prov"], [])
                min_dist = float("inf")
                for other_id, other_lat, other_lng in same_prov_list:
                    if other_id == st["record"]["id"]:
                        continue
                    d = haversine_km(st["lat"], st["lng"], other_lat, other_lng)
                    if d < min_dist:
                        min_dist = d
                if min_dist > 50.0:
                    suspect_candidates.append((st["record"], st["prov"], dom_prov, min_dist))

    total_suspects = len(suspect_candidates)
    should_hide = suspect_hide
    if total_suspects > max_threshold:
        print(f"[CẢNH BÁO] Số trạm nghi ngờ ({total_suspects}) vượt ngưỡng ({max_threshold}). Tắt cờ tự động ẩn.")
        should_hide = False

    newly_hidden = 0
    major_cities = ["hà nội", "hồ chí minh", "đà nẵng", "cần thơ", "huế", "hải phòng"]
    city_counter = Counter()

    for rec, prov, dom_prov, dist in suspect_candidates:
        if "extra_metadata" not in rec or rec["extra_metadata"] is None:
            rec["extra_metadata"] = {}
        rec["extra_metadata"]["coordinate_suspect"] = True
        rec["extra_metadata"]["suspect_reason"] = "knn5_consensus_mismatch_and_dist_gt_50km"
        rec["extra_metadata"]["neighbor_province"] = dom_prov
        rec["extra_metadata"]["dist_to_same_province_station_km"] = round(dist, 1)

        if should_hide:
            if rec.get("is_visible"):
                newly_hidden += 1
                rec["is_visible"] = False
                if prov in major_cities:
                    city_counter[prov] += 1
        else:
            if prov in major_cities:
                city_counter[prov] += 1

    new_visible_charging = sum(1 for r in charging_stations if r["is_visible"])
    return {
        "total_suspects": total_suspects,
        "should_hide": should_hide,
        "newly_hidden": newly_hidden,
        "new_visible_charging_stations": new_visible_charging,
        "city_breakdown": dict(city_counter),
    }


from urllib.parse import urlparse


def is_local_db(url_str: str) -> bool:
    if not url_str or url_str.startswith("sqlite"):
        return True
    try:
        parsed = urlparse(url_str)
        host = (parsed.hostname or "").lower()
        return host in ["localhost", "127.0.0.1", "::1"]
    except Exception:
        return False


def mask_db_url(url_str: str) -> str:
    if not url_str:
        return ""
    try:
        from sqlalchemy.engine import make_url
        return make_url(url_str).render_as_string(hide_password=True)
    except Exception:
        if "@" in url_str:
            return re.sub(r":([^@/]+)@", r":****@", url_str)
        return url_str


def get_target_db_url(cli_db_url: str | None, allow_remote: bool = False) -> str:
    if cli_db_url:
        target_url = cli_db_url
    else:
        # Nếu không truyền --db-url thì KHÔNG tự đọc DATABASE_URL production
        settings = get_settings()
        default_url = settings.database_url
        if is_local_db(default_url):
            target_url = default_url
        else:
            raise ValueError(
                "DATABASE_URL trong cấu hình trỏ tới host từ xa (production). "
                "Để đảm bảo an toàn, CLI không tự động dùng database này khi không có --db-url. "
                "Vui lòng truyền tường minh --db-url kèm --allow-remote nếu thực sự muốn chạy."
            )

    if not is_local_db(target_url) and not allow_remote:
        raise ValueError(
            f"Thao tác bị chặn: Database '{mask_db_url(target_url)}' là host từ xa. "
            "Cần truyền cờ tường minh --allow-remote để xác nhận thực thi."
        )

    if not is_local_db(target_url) and allow_remote:
        print(f"[CẢNH BÁO] Đang kết nối tới Database từ xa: {mask_db_url(target_url)}")

    return target_url


def import_records(
    records: list[dict[str, Any]],
    db_url: str | None = None,
    allow_remote: bool = False,
    dry_run: bool = False,
) -> tuple[int, int]:
    target_url = get_target_db_url(db_url, allow_remote=allow_remote)
    engine = create_engine(target_url)

    total_loaded = len(records)
    total_visible = sum(1 for r in records if r["is_visible"])

    # Validate exact counts
    if total_loaded != 25228:
        raise ValueError(f"LỆCH TỔNG SỐ NẠP: Kỳ vọng 25228, thực tế {total_loaded}. DỪNG.")
    if total_visible < 17000 or total_visible > 18189:
        raise ValueError(f"LỆCH TỔNG SỐ HIỂN THỊ: Kỳ vọng 17000..18189, thực tế {total_visible}. DỪNG.")

    if dry_run:
        print(f"[DRY-RUN] Xác nhận hợp lệ: {total_loaded} bản ghi ({total_visible} hiển thị). Không ghi vào DB.")
        engine.dispose()
        return total_loaded, total_visible

    with Session(engine) as session:
        session.query(ServicePoint).delete()
        now = utcnow()
        objects = [
            ServicePoint(
                id=r["id"],
                source_file=r["source_file"],
                source_id=r["source_id"],
                category=r["category"],
                category_name=r["category_name"],
                category_slug=r["category_slug"],
                name=r["name"],
                address=r["address"],
                latitude=r["latitude"],
                longitude=r["longitude"],
                phone=r["phone"],
                hotline_service=r["hotline_service"],
                booking_url=r["booking_url"],
                dong_son=r["dong_son"],
                operating_hours=r["operating_hours"],
                services_offered=r["services_offered"],
                status=r["status"],
                access_type=r["access_type"],
                is_car_compatible=r["is_car_compatible"],
                is_visible=r["is_visible"],
                extra_metadata=r["extra_metadata"],
                crawled_at=r["crawled_at"],
                created_at=now,
                updated_at=now,
            )
            for r in records
        ]
        session.bulk_save_objects(objects)
        session.commit()

    engine.dispose()
    return total_loaded, total_visible


def print_cross_tabulation(records: list[dict[str, Any]], stats: dict[str, Any]):
    df = pd.DataFrame(records)
    print("\n" + "=" * 70)
    print("=== BÁO CÁO NHẬP DỮ LIỆU ĐIỂM DỊCH VỤ VINFAST ===")
    print("=" * 70)

    print("\n1. THỐNG KÊ THEO FILE NGUỒN (NẠP / BỎ QUA):")
    print("-" * 70)
    for src, st in stats.items():
        if src == "suspect_info":
            continue
        print(f" - {src:20s}: Tổng {st['raw']:>6} dòng | Nạp: {st['loaded']:>6} | Bỏ qua: {st['skipped']:>6}")

    total_loaded = len(df)
    total_visible = df["is_visible"].sum()
    print("-" * 70)
    print(f" => TỔNG CỘNG NẠP      : {total_loaded} (Kỳ vọng: 25228 -> {'KHỚP' if total_loaded == 25228 else 'LỆCH'})")
    print(f" => TỔNG CỘNG HIỂN THỊ: {total_visible}")

    if "suspect_info" in stats:
        s_info = stats["suspect_info"]
        print("\n4. THỐNG KÊ TỌA ĐỘ ĐÁNG NGỜ (KNN-5 & DIST > 50KM):")
        print("-" * 70)
        print(f" - Tổng số trạm đáng ngờ phát hiện: {s_info['total_suspects']}")
        print(f" - Số trạm bị ẩn (chuyển is_visible=False): {s_info['newly_hidden']}")
        print(f" - Số trạm sạc hiển thị mới: {s_info['new_visible_charging_stations']} (kỳ vọng 17.656 - {s_info['newly_hidden']})")
        print(f" - Phân bố số bị ẩn tại các TP lớn: {s_info['city_breakdown']}")

    print("\n2. BẢNG CHÉO (CATEGORY x STATUS x ACCESS_TYPE):")
    print("-" * 70)
    ct = pd.crosstab([df["category"], df["status"]], df["access_type"], margins=True, margins_name="Total")
    print(ct.to_string())

    print("\n3. PHÂN BỐ THEO ĐIỀU KIỆN HIỂN THỊ (IS_VISIBLE):")
    print("-" * 70)
    vis_table = pd.crosstab(df["category"], df["is_visible"], margins=True, margins_name="Total")
    vis_table.columns = ["False (Ẩn/Không khả dụng)", "True (Hiển thị)", "Total"]
    print(vis_table.to_string())
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Import service points from crawl CSVs.")
    parser.add_argument("--path", default="data/crawl", help="Directory containing crawl CSV files.")
    parser.add_argument("--db-url", default=None, help="Database URL (default from local settings).")
    parser.add_argument("--crawled-at", default=None, help="ISO timestamp for crawled_at.")
    parser.add_argument("--allow-remote", action="store_true", help="Allow running against remote databases.")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing to database.")
    parser.add_argument("--suspect-hide", action=argparse.BooleanOptionalAction, default=True, help="Hide suspect stations based on KNN-5 consensus and distance > 50km.")
    args = parser.parse_args()

    crawl_dir = Path(args.path)
    if not crawl_dir.exists():
        print(f"Error: Path {crawl_dir} does not exist.", file=sys.stderr)
        sys.exit(1)

    crawled_at_dt = None
    if args.crawled_at:
        try:
            crawled_at_dt = datetime.fromisoformat(args.crawled_at)
        except Exception as e:
            print(f"Invalid --crawled-at timestamp format: {e}", file=sys.stderr)
            sys.exit(1)

    print(f"Đang đọc dữ liệu từ: {crawl_dir}...")
    records, stats = parse_service_points(crawl_dir, crawled_at_dt, suspect_hide=args.suspect_hide)

    print("Đang kiểm tra / nạp vào cơ sở dữ liệu...")
    total_loaded, total_visible = import_records(
        records,
        db_url=args.db_url,
        allow_remote=args.allow_remote,
        dry_run=args.dry_run,
    )

    print_cross_tabulation(records, stats)


if __name__ == "__main__":
    main()
