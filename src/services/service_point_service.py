"""Service layer for VinFast Service Points spatial query and intent-based recommendation.

Features:
- Bounding-box pre-filtering with cos(lat) adjustment
- Stepwise radius expansion (50km -> 100km -> 150km max) for sparse areas
- Haversine distance computation
- Filter is_visible=True, is_car_compatible=True
- Ranking rules:
    - Workshop: service_car and service_car_partner ALWAYS rank before service_gsm.
    - service_gsm only appears if car/partner workshops are fewer than limit.
    - When service_gsm appears, it carries note "Xưởng phục vụ xe taxi GSM, vui lòng gọi xác nhận trước khi đến".
- Intent routing & Triage:
    - Charging/Battery -> charging_station (ACTIVE/BUSY, "Chưa công bố công suất")
    - Service/Incident:
        - Heavy incident / Need rescue / Insufficient data:
            VINFAST_HOTLINE (1900-232389 from guardrails) at top,
            nearest workshop + hotline_service.
            "Có làm đồng sơn" if dong_son=True and collision detected.
        - Periodic maintenance (explicit LOW/MEDIUM priority without hazard):
            workshop with operating_hours, booking_url (fallback hotline_service), no rescue hotline.
    - Sales/General Info -> showroom
- Distance calculation rules:
    - Only calculate km when coordinates valid in Vietnam (lat 8..24, lng 102..110)
      AND source in ("BROWSER_GPS", "MAP_PICKER") AND status != "NOT_SHARED".
    - source="USER_TEXT" or missing coordinates -> needs_location=True, distance_km=None.
- Customer coordinates are NEVER returned in response.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from src.agents.guardrails import VINFAST_HOTLINE
from src.models.db_models import Case, CaseBrief, CaseLocation, ServicePoint
from src.models.schemas import ServicePointItem, ServicePointsData


# Bounding box Việt Nam
VN_LAT_MIN, VN_LAT_MAX = 8.0, 24.0
VN_LNG_MIN, VN_LNG_MAX = 102.0, 110.0

# Bán kính mặc định theo loại điểm (km)
DEFAULT_SEARCH_RADIUS: dict[str, float] = {
    "charging_station": 50.0,
    "workshop": 50.0,
    "showroom": 50.0,
}

# Tọa độ trung tâm Quận/Huyện (22 mục tham chiếu cấp quận)
DISTRICT_CENTERS: dict[str, tuple[str, tuple[float, float]]] = {
    # Cần Thơ
    "ninh kiều": ("cần thơ", (10.0342, 105.7885)),
    "bình thủy": ("cần thơ", (10.0718, 105.7282)),
    "cái răng": ("cần thơ", (9.9880, 105.7483)),
    # Hà Nội
    "ba đình": ("hà nội", (21.0341, 105.8244)),
    "hoàn kiếm": ("hà nội", (21.0285, 105.8542)),
    "cầu giấy": ("hà nội", (21.0362, 105.7906)),
    "đống đa": ("hà nội", (21.0181, 105.8299)),
    "hai bà trưng": ("hà nội", (21.0080, 105.8500)),
    "hà đông": ("hà nội", (20.9720, 105.7740)),
    # Đà Nẵng
    "hải châu": ("đà nẵng", (16.0544, 108.2022)),
    "thanh khê": ("đà nẵng", (16.0617, 108.1822)),
    "sơn trà": ("đà nẵng", (16.0820, 108.2430)),
    # TP. Hồ Chí Minh
    "quận 1": ("hồ chí minh", (10.7769, 106.7009)),
    "quận 3": ("hồ chí minh", (10.7844, 106.6843)),
    "quận 7": ("hồ chí minh", (10.7340, 106.7218)),
    "tân bình": ("hồ chí minh", (10.8015, 106.6534)),
    "bình thạnh": ("hồ chí minh", (10.8106, 106.7091)),
    "thủ đức": ("hồ chí minh", (10.8494, 106.7537)),
    # Đồng Nai
    "long thành": ("đồng nai", (10.7712, 106.9450)),
    # Lâm Đồng
    "đà lạt": ("lâm đồng", (11.9404, 108.4583)),
    # Khánh Hòa
    "nha trang": ("khánh hòa", (12.2388, 109.1967)),
    # Bà Rịa - Vũng Tàu
    "vũng tàu": ("bà rịa vũng tàu", (10.3460, 107.0843)),
}

# Tọa độ trung tâm Tỉnh/Thành phố (20 tỉnh/thành phố lớn)
PROVINCE_CENTERS: dict[str, tuple[float, float]] = {
    "cần thơ": (10.0452, 105.7469),
    "can tho": (10.0452, 105.7469),
    "hà nội": (21.0285, 105.8542),
    "ha noi": (21.0285, 105.8542),
    "tp. hồ chí minh": (10.8231, 106.6297),
    "hồ chí minh": (10.8231, 106.6297),
    "ho chi minh": (10.8231, 106.6297),
    "sài gòn": (10.8231, 106.6297),
    "sai gon": (10.8231, 106.6297),
    "tphcm": (10.8231, 106.6297),
    "đà nẵng": (16.0544, 108.2022),
    "da nang": (16.0544, 108.2022),
    "hải phòng": (20.8449, 106.6881),
    "hai phong": (20.8449, 106.6881),
    "huế": (16.4637, 107.5909),
    "thừa thiên huế": (16.4637, 107.5909),
    "hue": (16.4637, 107.5909),
    "lâm đồng": (11.9404, 108.4583),
    "lam dong": (11.9404, 108.4583),
    "hà giang": (22.8233, 104.9839),
    "cà mau": (9.1768, 105.1524),
    "đồng nai": (10.9574, 106.8427),
    "bình dương": (11.1603, 106.6576),
    "quảng ninh": (20.9505, 107.0734),
    "khánh hòa": (12.2388, 109.1967),
    "bà rịa vũng tàu": (10.3460, 107.0843),
    "thanh hóa": (19.8067, 105.7852),
    "nghệ an": (18.6734, 105.6813),
}


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Tính khoảng cách Haversine giữa 2 tọa độ (km). Bán kính Trái Đất = 6371.0 km."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return r * c


def is_valid_vietnam_coord(lat: float | None, lng: float | None) -> bool:
    if lat is None or lng is None:
        return False
    if not (math.isfinite(lat) and math.isfinite(lng)):
        return False
    return VN_LAT_MIN <= lat <= VN_LAT_MAX and VN_LNG_MIN <= lng <= VN_LNG_MAX


def infer_coordinates_from_label(label: str | None) -> tuple[float, float] | None:
    """Khớp khu vực từ chuỗi nhãn theo thứ tự ưu tiên:
    1. Quét tìm Quận/Huyện có trong DISTRICT_CENTERS. Nếu khớp -> trả về tọa độ tâm quận.
    2. Nếu không khớp tâm quận (hoặc quận không có trong bảng): Quét tìm Tỉnh/Thành phố trong PROVINCE_CENTERS -> fallback về tâm tỉnh.
    3. Nếu nhãn chỉ có phường (không khớp quận và không có tỉnh), hoặc tỉnh không nhận diện được -> trả về None.
    """
    if not label or not label.strip():
        return None
    norm = label.strip().lower()

    # 1. Tìm Quận/Huyện
    for district_alias, (_prov, coords) in DISTRICT_CENTERS.items():
        if district_alias in norm:
            return coords

    # 2. Fallback về tâm Tỉnh/Thành phố
    for prov_alias, coords in PROVINCE_CENTERS.items():
        if prov_alias in norm:
            return coords

    # 3. Phường đơn lẻ hoặc địa danh lạ không có tỉnh -> None
    return None


def mask_phone_last_4(phone: str | None) -> str | None:
    if not phone:
        return None
    val = phone.strip()
    if len(val) > 4:
        return val[:-4] + "****"
    return "****"


def find_nearby_service_points(
    db: Session,
    lat: float,
    lng: float,
    category: str | None = None,
    radius_km: float = 50.0,
    limit: int = 5,
    is_car_compatible: bool = True,
) -> list[tuple[ServicePoint, float]]:
    """Truy vấn các điểm dịch vụ gần nhất sử dụng Bounding Box + cos(lat) và Haversine.

    - Bán kính mở rộng theo bậc nếu vùng thưa: radius_km (50) -> 100 -> 150 km tối đa.
    - Sắp xếp:
        + Trạm sạc / Showroom: Khoảng cách tăng dần.
        + Xưởng dịch vụ: service_car và service_car_partner LUÔN xếp trước service_gsm bất kể khoảng cách.
          service_gsm chỉ bổ sung vào danh sách khi không đủ xưởng car/partner trong bán kính.
    """
    if not (math.isfinite(lat) and math.isfinite(lng) and math.isfinite(radius_km)):
        raise ValueError("Tọa độ hoặc bán kính không hợp lệ")

    # Mở rộng bán kính theo bậc tối đa 150 km
    search_radii = [radius_km]
    if radius_km < 100.0:
        search_radii.append(100.0)
    if radius_km < 150.0:
        search_radii.append(150.0)

    for current_radius in search_radii:
        lat_deg = current_radius / 111.0
        cos_lat = max(0.1, math.cos(math.radians(lat)))
        lng_deg = current_radius / (111.0 * cos_lat)

        lat_min, lat_max = lat - lat_deg, lat + lat_deg
        lng_min, lng_max = lng - lng_deg, lng + lng_deg

        filters = [
            ServicePoint.latitude.between(lat_min, lat_max),
            ServicePoint.longitude.between(lng_min, lng_max),
            ServicePoint.is_visible.is_(True),
        ]
        if is_car_compatible:
            filters.append(ServicePoint.is_car_compatible.is_(True))

        if category:
            filters.append(ServicePoint.category == category)
            if category == "charging_station":
                filters.append(ServicePoint.status.in_(["ACTIVE", "BUSY"]))
                filters.append(ServicePoint.access_type != "Restricted")

        dist_approx = (
            (ServicePoint.latitude - lat) * (ServicePoint.latitude - lat)
            + (ServicePoint.longitude - lng) * (ServicePoint.longitude - lng) * (cos_lat * cos_lat)
        )
        stmt = select(ServicePoint).where(and_(*filters)).order_by(dist_approx.asc()).limit(max(60, limit * 6))
        candidates = list(db.scalars(stmt).all())

        matched: list[tuple[ServicePoint, float]] = []
        for sp in candidates:
            dist = haversine_km(lat, lng, sp.latitude, sp.longitude)
            if dist <= current_radius:
                matched.append((sp, dist))

        if matched:
            if category == "workshop":
                # Quy tắc GSM: car & car_partner xếp TRƯỚC service_gsm bất kể khoảng cách
                car_partner = [m for m in matched if (m[0].category_slug or "") in ("service_car", "service_car_partner")]
                car_partner.sort(key=lambda m: (m[1], m[0].id))

                gsm = [m for m in matched if (m[0].category_slug or "") == "service_gsm"]
                gsm.sort(key=lambda m: (m[1], m[0].id))

                others = [m for m in matched if (m[0].category_slug or "") not in ("service_car", "service_car_partner", "service_gsm")]
                others.sort(key=lambda m: (m[1], m[0].id))

                result = car_partner[:limit]
                if len(result) < limit:
                    result.extend(others[: limit - len(result)])
                if len(result) < limit:
                    result.extend(gsm[: limit - len(result)])
                return result
            else:
                matched.sort(key=lambda m: (m[1], m[0].id))
                return matched[:limit]

    # Nếu sau 150 km vẫn không có điểm nào
    return []


def is_heavy_incident_or_needs_rescue(case: Case) -> bool:
    """Xác định sự cố nặng hoặc xe cần cứu hộ để hiển thị Hotline Cứu hộ VinFast (VINFAST_HOTLINE).

    Các trường triage:
    1. Case.priority: 'CRITICAL', 'HIGH'
    2. Case.safety_status: 'danger'
    3. CaseBrief.captured_fields:
       - operational_status: 'không di chuyển được', 'dừng xe', 'hỏng máy', 'cần cứu hộ'...
       - warning_symbol: 'rùa vàng', 'báo rùa'...
    4. Từ khóa trong CaseBrief.summary hoặc Case.messages:
       - 'không di chuyển được', 'không đi được', 'không chạy được', 'chết máy', 'sập nguồn',
         'rùa vàng', 'con rùa', 'mất phanh', 'tai nạn', 'lật xe', 'bốc khói', 'cháy', 'cứu hộ', 'cần cứu hộ'
    5. Ưu tiên an toàn: Nếu intent là Service/Incident nhưng thiếu dữ liệu phân loại -> ƯU TIÊN hiện rescue_hotline.
    6. CHỈ TẮT rescue_hotline khi:
       - Case được phân loại rõ ràng là bảo dưỡng thông thường (priority LOW/MEDIUM, summary/messages
         chỉ chứa 'bảo dưỡng', 'thay dầu', 'kiểm tra định kỳ' và KHÔNG có bất kỳ dấu hiệu nguy hiểm/bất động nào).
    """
    intent = (case.intent or "").strip()
    if intent not in ("Service/Incident", "SERVICE_INCIDENT", "Tire/Brake"):
        return False

    # Thu thập văn bản ngữ cảnh
    texts = []
    if case.brief and case.brief.summary:
        texts.append(case.brief.summary.lower())
    if case.brief and case.brief.captured_fields:
        for val in case.brief.captured_fields.values():
            if isinstance(val, str):
                texts.append(val.lower())
    if case.messages:
        for m in case.messages[-5:]:
            if m.content:
                texts.append(m.content.lower())
    combined = " ".join(texts)

    # Dấu hiệu cứu hộ / nguy hiểm
    danger_signals = [
        "không di chuyển được", "khong di chuyen duoc", "không đi được", "khong di duoc",
        "không chạy được", "khong chay duoc", "chết máy", "chet may", "sập nguồn", "sap nguon",
        "rùa vàng", "rua vang", "con rùa", "con rua", "báo rùa", "mất phanh", "mat phanh",
        "tai nạn", "tai nan", "va chạm", "lật xe", "bốc khói", "cháy", "cứu hộ", "cuu ho", "cần cứu hộ"
    ]
    has_danger_signal = any(sig in combined for sig in danger_signals)

    # 1. Có dấu hiệu nguy hiểm / bất động rõ ràng
    if has_danger_signal:
        return True

    # 2. Priority cao hoặc safety_status nguy hiểm
    if case.priority in ("CRITICAL", "HIGH") or getattr(case, "safety_status", None) == "danger":
        return True

    # 3. Phân biệt bảo dưỡng định kỳ lành tính
    is_routine_maintenance = (
        case.priority in ("LOW", "MEDIUM")
        and getattr(case, "safety_status", None) != "danger"
        and any(kw in combined for kw in ["bảo dưỡng", "bao duong", "thay dầu", "kiểm tra định kỳ", "bảo dưỡng định kỳ"])
        and not has_danger_signal
    )
    if is_routine_maintenance:
        return False

    # 4. Khi intent là Service/Incident nhưng thiếu dữ liệu phân loại -> ƯU TIÊN hiện hotline cứu hộ
    return True


def is_collision_or_bodywork_case(case: Case) -> bool:
    """Xác định sự cố có liên quan đến va chạm, tai nạn, thân vỏ để kích hoạt ghi chú đồng sơn."""
    collision_keywords = [
        "va chạm", "tai nạn", "đâm", "móp", "thân vỏ", "trầy", "xước",
        "bẹp", "đồng sơn", "vỡ cản", "hỏng vỏ", "cọ quẹt", "móp méo"
    ]
    texts = []
    if case.brief and case.brief.summary:
        texts.append(case.brief.summary.lower())
    if case.messages:
        for m in case.messages[-5:]:
            if m.content:
                texts.append(m.content.lower())
    combined = " ".join(texts)
    return any(kw in combined for kw in collision_keywords)


def format_service_point_item(
    sp: ServicePoint,
    distance_km: float | None = None,
    power_info: str | None = None,
    note: str | None = None,
    mask_phone: bool = False,
) -> ServicePointItem:
    phone = mask_phone_last_4(sp.phone) if mask_phone else sp.phone
    hotline_service = mask_phone_last_4(sp.hotline_service) if mask_phone else sp.hotline_service

    # Note bổ sung cho service_gsm
    final_note = note
    if sp.category_slug == "service_gsm":
        gsm_note = "Xưởng phục vụ xe taxi GSM, vui lòng gọi xác nhận trước khi đến"
        final_note = f"{note}; {gsm_note}" if note else gsm_note

    return ServicePointItem(
        id=sp.id,
        name=sp.name,
        category=sp.category,
        category_slug=sp.category_slug,
        address=sp.address,
        distance_km=round(distance_km, 2) if distance_km is not None else None,
        latitude=sp.latitude,
        longitude=sp.longitude,
        phone=phone,
        hotline=phone,
        hotline_service=hotline_service,
        booking_url=sp.booking_url,
        dong_son=bool(sp.dong_son),
        operating_hours=sp.operating_hours,
        hours=sp.operating_hours,
        services_offered=sp.services_offered,
        power_info=power_info,
        status=sp.status,
        note=final_note,
        crawled_at=sp.crawled_at.isoformat() if sp.crawled_at else None,
    )


def build_case_service_points_response(
    db: Session,
    case: Case,
    mask_phone_in_response: bool = False,
) -> ServicePointsData:
    """Tạo response đề xuất điểm dịch vụ cho một Case theo chuẩn BƯỚC 3."""
    loc: CaseLocation | None = case.location

    # Kiểm tra điều kiện tính km
    can_calculate_km = False
    ref_lat: float | None = None
    ref_lng: float | None = None

    if (
        loc is not None
        and loc.status != "NOT_SHARED"
        and loc.source in ("BROWSER_GPS", "MAP_PICKER")
        and is_valid_vietnam_coord(loc.latitude, loc.longitude)
    ):
        can_calculate_km = True
        ref_lat = loc.latitude
        ref_lng = loc.longitude
    elif loc is not None and loc.location_label:
        inferred = infer_coordinates_from_label(loc.location_label)
        if inferred:
            ref_lat, ref_lng = inferred
            can_calculate_km = False

    intent = (case.intent or "").strip()
    is_rescue_needed = is_heavy_incident_or_needs_rescue(case)

    target_category: str
    if intent in ("Charging/Battery", "CHARGING_BATTERY"):
        target_category = "charging_station"
    elif intent in ("Service/Incident", "SERVICE_INCIDENT", "Tire/Brake"):
        target_category = "workshop"
    elif intent in ("Sales/General Info", "SALES_INFO"):
        target_category = "showroom"
    else:
        target_category = "workshop"

    recommended_points: list[ServicePointItem] = []
    max_crawled_at: datetime | None = None
    rescue_hotline: str | None = None

    if ref_lat is not None and ref_lng is not None:
        radius_default = DEFAULT_SEARCH_RADIUS.get(target_category, 50.0)
        nearby_raw = find_nearby_service_points(
            db=db,
            lat=ref_lat,
            lng=ref_lng,
            category=target_category,
            radius_km=radius_default,
            limit=5,
        )

        is_collision = is_collision_or_bodywork_case(case)

        for sp, dist in nearby_raw:
            if sp.crawled_at:
                if max_crawled_at is None or sp.crawled_at > max_crawled_at:
                    max_crawled_at = sp.crawled_at

            item_dist = dist if can_calculate_km else None

            power_info = "Chưa công bố công suất" if target_category == "charging_station" else None
            note = None
            if target_category == "workshop" and is_collision and sp.dong_son:
                note = "Có làm đồng sơn"

            item = format_service_point_item(
                sp=sp,
                distance_km=item_dist,
                power_info=power_info,
                note=note,
                mask_phone=mask_phone_in_response,
            )
            recommended_points.append(item)

    if is_rescue_needed:
        rescue_hotline = VINFAST_HOTLINE

    if max_crawled_at:
        last_updated_label = f"Dữ liệu thu thập tháng {max_crawled_at.month}/{max_crawled_at.year}"
    else:
        last_updated_label = "Dữ liệu thu thập tháng 10/2026"

    # Xử lý cờ vùng thưa và nhu cầu định vị
    no_points_nearby = False
    message = None
    if can_calculate_km and len(recommended_points) == 0:
        no_points_nearby = True
        message = "Chưa có điểm dịch vụ trong 150 km quanh vị trí của bạn; vui lòng gọi hotline"
        needs_location = False
    else:
        needs_location = not can_calculate_km

    return ServicePointsData(
        case_id=case.id,
        needs_location=needs_location,
        no_points_nearby=no_points_nearby,
        message=message,
        last_updated_label=last_updated_label,
        rescue_hotline=rescue_hotline,
        recommended_points=recommended_points,
    )


def search_service_points_catalog(
    lat: float,
    lng: float,
    category: str = "ALL",
    radius_km: float = 50.0,
    limit: int = 5,
    vehicle_type: str = "CAR",
    db: Session | None = None,
) -> dict:
    """Tra cứu điểm dịch vụ cho tool vinfast_nearby_search và endpoint /customer/service-points/nearby.

    - Nếu chạy ở chế độ demo (GPS_CATALOG_MODE=demo): dùng catalog demo từ file JSON để giữ tính toàn vẹn cho test fixture.
    - Chế độ chuẩn (production / database): truy vấn trực tiếp bảng `service_points` qua SQLAlchemy,
      áp dụng bộ lọc is_visible=True, is_car_compatible=True (nếu vehicle_type='CAR'),
      xếp xưởng service_car/service_car_partner trước service_gsm.
    """
    import os
    if os.environ.get("GPS_CATALOG_MODE") == "demo":
        from src.services.service_point_catalog import default_catalog_adapter, nearby_service_points
        return nearby_service_points(lat, lng, category, radius_km, limit, default_catalog_adapter(), vehicle_type)

    if not all(math.isfinite(v) for v in (lat, lng, radius_km)) or abs(lat) > 90 or abs(lng) > 180 or radius_km <= 0:
        raise ValueError("Invalid search coordinates")
    if vehicle_type not in {"CAR", "TWO_WHEELER"}:
        raise ValueError("Unsupported vehicle type")

    limit = min(100, max(1, limit))

    # Ánh xạ category
    cat_map = {
        "CHARGING_STATION": "charging_station",
        "SHOWROOM": "showroom",
        "SERVICE_WORKSHOP": "workshop",
    }
    db_cat = cat_map.get(category)

    should_close_db = False
    if db is None:
        from src.db import SessionLocal
        db = SessionLocal()
        should_close_db = True

    try:
        is_car = (vehicle_type == "CAR")
        nearby_raw = find_nearby_service_points(
            db=db,
            lat=lat,
            lng=lng,
            category=db_cat,
            radius_km=radius_km,
            limit=limit,
            is_car_compatible=is_car,
        )

        points = []
        for sp, dist in nearby_raw:
            cat_out = "SHOWROOM"
            if sp.category == "charging_station":
                cat_out = "CHARGING_STATION"
            elif sp.category == "workshop":
                cat_out = "SERVICE_WORKSHOP"

            points.append({
                "id": sp.id,
                "name": sp.name,
                "address": sp.address,
                "category": cat_out,
                "vehicle_type": vehicle_type,
                "latitude": sp.latitude,
                "longitude": sp.longitude,
                "distance_km": round(dist, 3),
                "source": "VinFast Database",
                "updated_at": sp.crawled_at.strftime("%Y-%m-%d") if sp.crawled_at else "2026-10-15",
                "verification_status": "VERIFIED",
                "demo": False,
                "phone": sp.phone,
                "hotline_service": sp.hotline_service,
                "booking_url": sp.booking_url,
                "operating_hours": sp.operating_hours,
                "hours": sp.operating_hours,
                "dong_son": bool(sp.dong_son),
                "services_offered": sp.services_offered,
            })

        return {
            "points": points,
            "source": "VinFast Database",
            "updated_at": "2026-10-15",
            "verification_status": "VERIFIED",
            "demo": False,
            "distance_method": "AIRLINE",
            "radius_km": radius_km,
            "limit": limit,
            "vehicle_type": vehicle_type,
        }
    finally:
        if should_close_db:
            db.close()
