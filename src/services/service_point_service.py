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
import re
import unicodedata
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

# Tọa độ trung tâm Quận/Huyện/Thị xã phổ biến
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
    "thanh xuân": ("hà nội", (20.9928, 105.8117)),
    "nam từ liêm": ("hà nội", (21.0131, 105.7667)),
    "bắc từ liêm": ("hà nội", (21.0667, 105.7667)),
    "long biên": ("hà nội", (21.0367, 105.8925)),
    "gia lâm": ("hà nội", (21.0142, 105.9400)),
    "đông anh": ("hà nội", (21.1378, 105.8456)),
    "sóc sơn": ("hà nội", (21.2575, 105.8500)),
    "hoài đức": ("hà nội", (21.0189, 105.7078)),
    "hòai đức": ("hà nội", (21.0189, 105.7078)),
    "vinhomes ocean park": ("hà nội", (20.9954, 105.9482)),
    # Đà Nẵng
    "hải châu": ("đà nẵng", (16.0544, 108.2022)),
    "thanh khê": ("đà nẵng", (16.0617, 108.1822)),
    "sơn trà": ("đà nẵng", (16.0820, 108.2430)),
    "liên chiểu": ("đà nẵng", (16.0767, 108.1500)),
    "ngũ hành sơn": ("đà nẵng", (16.0028, 108.2500)),
    # TP. Hồ Chí Minh
    "quận 1": ("hồ chí minh", (10.7769, 106.7009)),
    "quận 3": ("hồ chí minh", (10.7844, 106.6843)),
    "quận 7": ("hồ chí minh", (10.7340, 106.7218)),
    "tân bình": ("hồ chí minh", (10.8015, 106.6534)),
    "tân phú": ("hồ chí minh", (10.7904, 106.6284)),
    "phú nhuận": ("hồ chí minh", (10.7992, 106.6806)),
    "gò vấp": ("hồ chí minh", (10.8388, 106.6653)),
    "bình thạnh": ("hồ chí minh", (10.8106, 106.7091)),
    "bình tân": ("hồ chí minh", (10.7656, 106.6047)),
    "bình chánh": ("hồ chí minh", (10.6874, 106.5925)),
    "hóc môn": ("hồ chí minh", (10.8844, 106.5919)),
    "củ chi": ("hồ chí minh", (11.0067, 106.4950)),
    "nhà bè": ("hồ chí minh", (10.6486, 106.7297)),
    "thủ đức": ("hồ chí minh", (10.8494, 106.7537)),
    "vũng tàu": ("hồ chí minh", (10.3460, 107.0843)),
    # Nghệ An
    "vinh": ("nghệ an", (18.6734, 105.6813)),
    "tp vinh": ("nghệ an", (18.6734, 105.6813)),
    "thành phố vinh": ("nghệ an", (18.6734, 105.6813)),
    # Quảng Ninh
    "hạ long": ("quảng ninh", (20.9505, 107.0734)),
    "cẩm phả": ("quảng ninh", (21.0167, 107.3167)),
    "uông bí": ("quảng ninh", (21.0333, 106.7667)),
    # Đồng Nai
    "biên hòa": ("đồng nai", (10.9574, 106.8427)),
    "long thành": ("đồng nai", (10.7712, 106.9450)),
    # Khánh Hòa
    "nha trang": ("khánh hòa", (12.2388, 109.1967)),
    "cam ranh": ("khánh hòa", (11.9214, 109.1592)),
    # Phú Thọ (Vĩnh Phúc -> Phú Thọ)
    "vĩnh yên": ("phú thọ", (21.3089, 105.6047)),
    # Lâm Đồng
    "đà lạt": ("lâm đồng", (11.9404, 108.4583)),
    "bảo lộc": ("lâm đồng", (11.5475, 107.8083)),
}

# Tọa độ trung tâm Tỉnh/Thành phố (Phủ đủ 34 đơn vị hành chính hiện hành và các bí danh sáp nhập)
PROVINCE_CENTERS: dict[str, tuple[float, float]] = {
    # 34 Đơn vị hành chính cấp tỉnh hiện hành trong dữ liệu
    "bắc ninh": (21.1861, 106.0763),
    "cần thơ": (10.0452, 105.7469),
    "can tho": (10.0452, 105.7469),
    "huế": (16.4637, 107.5909),
    "thừa thiên huế": (16.4637, 107.5909),
    "hue": (16.4637, 107.5909),
    "hà nội": (21.0285, 105.8542),
    "ha noi": (21.0285, 105.8542),
    "hải phòng": (20.8449, 106.6881),
    "hai phong": (20.8449, 106.6881),
    "hồ chí minh": (10.7769, 106.7009),
    "tp. hồ chí minh": (10.7769, 106.7009),
    "tp hồ chí minh": (10.7769, 106.7009),
    "ho chi minh": (10.7769, 106.7009),
    "sài gòn": (10.7769, 106.7009),
    "sai gon": (10.7769, 106.7009),
    "tphcm": (10.7769, 106.7009),
    "quảng ninh": (20.9505, 107.0734),
    "quang ninh": (20.9505, 107.0734),
    "đà nẵng": (16.0544, 108.2022),
    "da nang": (16.0544, 108.2022),
    "đồng nai": (10.9574, 106.8427),
    "dong nai": (10.9574, 106.8427),
    "an giang": (10.3833, 105.4167),
    "cao bằng": (22.6667, 106.2500),
    "cà mau": (9.1768, 105.1524),
    "ca mau": (9.1768, 105.1524),
    "gia lai": (13.9833, 108.0000),
    "hà tĩnh": (18.3333, 105.9000),
    "ha tinh": (18.3333, 105.9000),
    "hưng yên": (20.6500, 106.0500),
    "hung yen": (20.6500, 106.0500),
    "khánh hòa": (12.2388, 109.1967),
    "khanh hoa": (12.2388, 109.1967),
    "lai châu": (22.3833, 103.4500),
    "lào cai": (22.4833, 103.9667),
    "lao cai": (22.4833, 103.9667),
    "lâm đồng": (11.9404, 108.4583),
    "lam dong": (11.9404, 108.4583),
    "lạng sơn": (21.8500, 106.7500),
    "lang son": (21.8500, 106.7500),
    "nghệ an": (18.6734, 105.6813),
    "nghe an": (18.6734, 105.6813),
    "ninh bình": (20.2500, 105.9750),
    "ninh binh": (20.2500, 105.9750),
    "phú thọ": (21.3167, 105.4000),
    "phu tho": (21.3167, 105.4000),
    "quảng ngãi": (15.1167, 108.8000),
    "quang ngai": (15.1167, 108.8000),
    "quảng trị": (16.8167, 107.1000),
    "quang tri": (16.8167, 107.1000),
    "sơn la": (21.3167, 103.9000),
    "son la": (21.3167, 103.9000),
    "thanh hóa": (19.8067, 105.7852),
    "thanh hoa": (19.8067, 105.7852),
    "thái nguyên": (21.5942, 105.8481),
    "thai nguyen": (21.5942, 105.8481),
    "tuyên quang": (21.8167, 105.2167),
    "tuyen quang": (21.8167, 105.2167),
    "tây ninh": (11.3000, 106.1000),
    "tay ninh": (11.3000, 106.1000),
    "vĩnh long": (10.2500, 105.9667),
    "vinh long": (10.2500, 105.9667),
    "điện biên": (21.3833, 103.0167),
    "dien bien": (21.3833, 103.0167),
    "đắk lắk": (12.6667, 108.0500),
    "dak lak": (12.6667, 108.0500),
    "đồng tháp": (10.4500, 105.6333),
    "dong thap": (10.4500, 105.6333),

    # Bí danh các tỉnh/thành đã sáp nhập -> trỏ về tọa độ tỉnh mới (chính xác theo Đề án sắp xếp ĐVHC 2025)
    "bình dương": (10.7769, 106.7009),  # -> TP.HCM
    "binh duong": (10.7769, 106.7009),
    "bà rịa vũng tàu": (10.7769, 106.7009),  # -> TP.HCM
    "ba ria vung tau": (10.7769, 106.7009),
    "bà rịa - vũng tàu": (10.7769, 106.7009),
    "vũng tàu": (10.7769, 106.7009),
    "vung tau": (10.7769, 106.7009),
    "long an": (11.3000, 106.1000),  # -> Tây Ninh
    "kiên giang": (10.3833, 105.4167),  # -> An Giang
    "kien giang": (10.3833, 105.4167),
    "hà giang": (21.8167, 105.2167),  # -> Tuyên Quang
    "ha giang": (21.8167, 105.2167),
    "hà nam": (20.2500, 105.9750),  # -> Ninh Bình
    "ha nam": (20.2500, 105.9750),
    "hải dương": (20.8449, 106.6881),  # -> Hải Phòng
    "hai duong": (20.8449, 106.6881),
    "bắc giang": (21.1861, 106.0763),  # -> Bắc Ninh
    "bac giang": (21.1861, 106.0763),
    "vĩnh phúc": (21.3167, 105.4000),  # -> Phú Thọ
    "vinh phuc": (21.3167, 105.4000),
    "hòa bình": (21.3167, 105.4000),  # -> Phú Thọ
    "hoa binh": (21.3167, 105.4000),
    "nam định": (20.2500, 105.9750),  # -> Ninh Bình
    "nam dinh": (20.2500, 105.9750),
    "thái bình": (20.6500, 106.0500),  # -> Hưng Yên
    "thai binh": (20.6500, 106.0500),
    "quảng bình": (16.8167, 107.1000),  # -> Quảng Trị
    "quang binh": (16.8167, 107.1000),
    "bình định": (13.9833, 108.0000),  # -> Gia Lai
    "binh dinh": (13.9833, 108.0000),
    "quảng nam": (16.0544, 108.2022),  # -> Đà Nẵng
    "quang nam": (16.0544, 108.2022),
    "phú yên": (12.6667, 108.0500),  # -> Đắk Lắk
    "phu yen": (12.6667, 108.0500),
    "ninh thuận": (12.2388, 109.1967),  # -> Khánh Hòa
    "ninh thuan": (12.2388, 109.1967),
    "bình thuận": (11.9404, 108.4583),  # -> Lâm Đồng
    "binh thuan": (11.9404, 108.4583),
    "kon tum": (15.1167, 108.8000),  # -> Quảng Ngãi
    "đắk nông": (11.9404, 108.4583),  # -> Lâm Đồng
    "dak nong": (11.9404, 108.4583),
    "đắc nông": (11.9404, 108.4583),
    "dac nong": (11.9404, 108.4583),
    "bình phước": (10.9574, 106.8427),  # -> Đồng Nai
    "binh phuoc": (10.9574, 106.8427),
    "tiền giang": (10.4500, 105.6333),  # -> Đồng Tháp
    "tien giang": (10.4500, 105.6333),
    "bến tre": (10.2500, 105.9667),  # -> Vĩnh Long
    "ben tre": (10.2500, 105.9667),
    "trà vinh": (10.2500, 105.9667),  # -> Vĩnh Long
    "tra vinh": (10.2500, 105.9667),
    "hậu giang": (10.0452, 105.7469),  # -> Cần Thơ
    "hau giang": (10.0452, 105.7469),
    "sóc trăng": (10.0452, 105.7469),  # -> Cần Thơ
    "soc trang": (10.0452, 105.7469),
    "bạc liêu": (9.1768, 105.1524),  # -> Cà Mau
    "bac lieu": (9.1768, 105.1524),
    "yên bái": (22.4833, 103.9667),  # -> Lào Cai
    "yen bai": (22.4833, 103.9667),
    "bắc kạn": (21.5942, 105.8481),  # -> Thái Nguyên
    "bac kan": (21.5942, 105.8481),
}


TONE_UNIFICATION = {
    "oà": "òa", "oá": "óa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
    "oè": "òe", "oé": "óe", "oẻ": "ỏe", "oẽ": "õe", "oẹ": "ọe",
    "uỳ": "ùy", "uý": "úy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy",
    "ăk": "ắk",
}

def strip_vietnamese_diacritics(text: str) -> str:
    """Loại bỏ dấu tiếng Việt để so sánh dạng không dấu."""
    norm = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in norm if unicodedata.category(ch) != "Mn")
    stripped = stripped.replace("đ", "d").replace("Đ", "d")
    return unicodedata.normalize("NFC", stripped)

def normalize_vietnamese_text(s: str) -> str:
    """Chuẩn hóa Unicode NFC, thường hóa, thống nhất vị trí dấu thanh và tiền tố hành chính."""
    s = unicodedata.normalize("NFC", s.strip().lower())
    for old, new in TONE_UNIFICATION.items():
        s = s.replace(old, new)
    prefixes = [
        "tỉnh ", "tp. ", "tp ", "tp.", "thành phố ", "thị xã ", "tx. ", "quận ", "huyện "
    ]
    changed = True
    while changed:
        changed = False
        for p in prefixes:
            if s.startswith(p):
                s = s[len(p):].strip()
                changed = True
    return s

# Bảng tra cứu canonical 34 tỉnh và bí danh
PROVINCE_CANONICAL_MAP: dict[str, str] = {
    "bắc ninh": "bắc ninh",
    "cần thơ": "cần thơ",
    "huế": "huế",
    "thừa thiên huế": "huế",
    "thừa thiên - huế": "huế",
    "thua thien hue": "huế",
    "hue": "huế",
    "hà nội": "hà nội",
    "ha noi": "hà nội",
    "hanoi": "hà nội",
    "hn": "hà nội",
    "hải phòng": "hải phòng",
    "hai phong": "hải phòng",
    "hồ chí minh": "hồ chí minh",
    "ho chi minh": "hồ chí minh",
    "tp.hcm": "hồ chí minh",
    "tphcm": "hồ chí minh",
    "tp hcm": "hồ chí minh",
    "hcm": "hồ chí minh",
    "sài gòn": "hồ chí minh",
    "sai gon": "hồ chí minh",
    "tp. hồ chí minh": "hồ chí minh",
    "tp hồ chí minh": "hồ chí minh",
    "tp.hồ chí minh": "hồ chí minh",
    "quảng ninh": "quảng ninh",
    "quang ninh": "quảng ninh",
    "đà nẵng": "đà nẵng",
    "da nang": "đà nẵng",
    "đồng nai": "đồng nai",
    "dong nai": "đồng nai",
    "an giang": "an giang",
    "cao bằng": "cao bằng",
    "cao bang": "cao bằng",
    "cà mau": "cà mau",
    "ca mau": "cà mau",
    "gia lai": "gia lai",
    "hà tĩnh": "hà tĩnh",
    "ha tinh": "hà tĩnh",
    "hưng yên": "hưng yên",
    "hung yen": "hưng yên",
    "khánh hòa": "khánh hòa",
    "khanh hoa": "khánh hòa",
    "khánh hoà": "khánh hòa",
    "lai châu": "lai châu",
    "lai chau": "lai châu",
    "lào cai": "lào cai",
    "lao cai": "lào cai",
    "lâm đồng": "lâm đồng",
    "lam dong": "lâm đồng",
    "lạng sơn": "lạng sơn",
    "lang son": "lạng sơn",
    "nghệ an": "nghệ an",
    "nghe an": "nghệ an",
    "ninh bình": "ninh bình",
    "ninh binh": "ninh bình",
    "phú thọ": "phú thọ",
    "phu tho": "phú thọ",
    "quảng ngãi": "quảng ngãi",
    "quang ngai": "quảng ngãi",
    "quảng trị": "quảng trị",
    "quang tri": "quảng trị",
    "sơn la": "sơn la",
    "son la": "sơn la",
    "thanh hóa": "thanh hóa",
    "thanh hoa": "thanh hóa",
    "thanh hoá": "thanh hóa",
    "thái nguyên": "thái nguyên",
    "thai nguyen": "thái nguyên",
    "tuyên quang": "tuyên quang",
    "tuyen quang": "tuyên quang",
    "tây ninh": "tây ninh",
    "tay ninh": "tây ninh",
    "vĩnh long": "vĩnh long",
    "vinh long": "vĩnh long",
    "điện biên": "điện biên",
    "dien bien": "điện biên",
    "đắk lắk": "đắk lắk",
    "dak lak": "đắk lắk",
    "đăk lăk": "đắk lắk",
    "đắc lắc": "đắk lắk",
    "daklak": "đắk lắk",
    "đồng tháp": "đồng tháp",
    "dong thap": "đồng tháp",

    # Sáp nhập theo Nghị quyết:
    "bình dương": "hồ chí minh",
    "binh duong": "hồ chí minh",
    "bà rịa vũng tàu": "hồ chí minh",
    "ba ria vung tau": "hồ chí minh",
    "bà rịa - vũng tàu": "hồ chí minh",
    "vũng tàu": "hồ chí minh",
    "vung tau": "hồ chí minh",
    "long an": "tây ninh",
    "kiên giang": "an giang",
    "kien giang": "an giang",
    "hà giang": "tuyên quang",
    "ha giang": "tuyên quang",
    "hà nam": "ninh bình",
    "ha nam": "ninh bình",
    "hải dương": "hải phòng",
    "hai duong": "hải phòng",
    "bắc giang": "bắc ninh",
    "bac giang": "bắc ninh",
    "vĩnh phúc": "phú thọ",
    "vinh phuc": "phú thọ",
    "hòa bình": "phú thọ",
    "hoa binh": "phú thọ",
    "hoà bình": "phú thọ",
    "nam định": "ninh bình",
    "nam dinh": "ninh bình",
    "thái bình": "hưng yên",
    "thai binh": "hưng yên",
    "quảng bình": "quảng trị",
    "quang binh": "quảng trị",
    "bình định": "gia lai",
    "binh dinh": "gia lai",
    "quảng nam": "đà nẵng",
    "quang nam": "đà nẵng",
    "phú yên": "đắk lắk",
    "phu yen": "đắk lắk",
    "ninh thuận": "khánh hòa",
    "ninh thuan": "khánh hòa",
    "bình thuận": "lâm đồng",
    "binh thuan": "lâm đồng",
    "kon tum": "quảng ngãi",
    "đắk nông": "lâm đồng",
    "dak nong": "lâm đồng",
    "đắc nông": "lâm đồng",
    "dac nong": "lâm đồng",
    "đăk nông": "lâm đồng",
    "bình phước": "đồng nai",
    "binh phuoc": "đồng nai",
    "tiền giang": "đồng tháp",
    "tien giang": "đồng tháp",
    "bến tre": "vĩnh long",
    "ben tre": "vĩnh long",
    "trà vinh": "vĩnh long",
    "tra vinh": "vĩnh long",
    "hậu giang": "cần thơ",
    "hau giang": "cần thơ",
    "sóc trăng": "cần thơ",
    "soc trang": "cần thơ",
    "bạc liêu": "cà mau",
    "bac lieu": "cà mau",
    "yên bái": "lào cai",
    "yen bai": "lào cai",
    "bắc kạn": "thái nguyên",
    "bac kan": "thái nguyên",
    "bắc cạn": "thái nguyên",
}

LOOKUP_PROVINCE_MAP: dict[str, str] = {}
for _k, _v in PROVINCE_CANONICAL_MAP.items():
    _k_norm = normalize_vietnamese_text(_k)
    LOOKUP_PROVINCE_MAP[_k_norm] = _v
    _k_no_acc = strip_vietnamese_diacritics(_k_norm)
    if _k_no_acc not in LOOKUP_PROVINCE_MAP:
        LOOKUP_PROVINCE_MAP[_k_no_acc] = _v

DISTRICT_TOWN_TO_PROVINCE: dict[str, str] = {
    # TP.HCM
    "quận 1": "hồ chí minh",
    "quận 3": "hồ chí minh",
    "quận 7": "hồ chí minh",
    "quận 10": "hồ chí minh",
    "quận 12": "hồ chí minh",
    "thủ đức": "hồ chí minh",
    "bình tân": "hồ chí minh",
    "bình chánh": "hồ chí minh",
    "củ chi": "hồ chí minh",
    "hóc môn": "hồ chí minh",
    "nhà bè": "hồ chí minh",
    "gò vấp": "hồ chí minh",
    "tân bình": "hồ chí minh",
    "tân phú": "hồ chí minh",
    "phú nhuận": "hồ chí minh",
    "bình thạnh": "hồ chí minh",
    "vũng tàu": "hồ chí minh",
    # Hà Nội
    "ba đình": "hà nội",
    "tây hồ": "hà nội",
    "sóc sơn": "hà nội",
    "hoài đức": "hà nội",
    "hòai đức": "hà nội",
    "đông anh": "hà nội",
    "gia lâm": "hà nội",
    "long biên": "hà nội",
    "cầu giấy": "hà nội",
    "đống đa": "hà nội",
    "hoàn kiếm": "hà nội",
    "hà đông": "hà nội",
    "thanh xuân": "hà nội",
    "nam từ liêm": "hà nội",
    "bắc từ liêm": "hà nội",
    "vinhomes ocean park": "hà nội",
    # Nghệ An (chỉ khi đứng một mình hoặc kèm "TP Vinh")
    "vinh": "nghệ an",
    "tp vinh": "nghệ an",
    "thành phố vinh": "nghệ an",
    # Quảng Ninh
    "hạ long": "quảng ninh",
    "cẩm phả": "quảng ninh",
    "uông bí": "quảng ninh",
    # Đồng Nai
    "biên hòa": "đồng nai",
    "long thành": "đồng nai",
    # Khánh Hòa
    "nha trang": "khánh hòa",
    "cam ranh": "khánh hòa",
    # Phú Thọ (Vĩnh Phúc -> Phú Thọ)
    "vĩnh yên": "phú thọ",
    # Đà Nẵng
    "thanh khê": "đà nẵng",
    "hải châu": "đà nẵng",
    "sơn trà": "đà nẵng",
    "liên chiểu": "đà nẵng",
    "ngũ hành sơn": "đà nẵng",
    # Cần Thơ
    "ninh kiều": "cần thơ",
    "bình thủy": "cần thơ",
    "cái răng": "cần thơ",
    # Lâm Đồng
    "đà lạt": "lâm đồng",
    "bảo lộc": "lâm đồng",
}

LOOKUP_DISTRICT_MAP: dict[str, str] = {}
for _dk, _dv in DISTRICT_TOWN_TO_PROVINCE.items():
    _dk_norm = normalize_vietnamese_text(_dk)
    LOOKUP_DISTRICT_MAP[_dk_norm] = _dv
    _dk_no_acc = strip_vietnamese_diacritics(_dk_norm)
    if _dk_no_acc not in LOOKUP_DISTRICT_MAP:
        LOOKUP_DISTRICT_MAP[_dk_no_acc] = _dv


def match_province_segment(raw_segment: str) -> str | None:
    norm = normalize_vietnamese_text(raw_segment)
    if norm in LOOKUP_PROVINCE_MAP:
        return LOOKUP_PROVINCE_MAP[norm]
    norm_no_acc = strip_vietnamese_diacritics(norm)
    if norm_no_acc in LOOKUP_PROVINCE_MAP:
        return LOOKUP_PROVINCE_MAP[norm_no_acc]

    # Kiểm tra bảng quận/huyện/thị xã phổ biến
    if norm == "vinh" or norm_no_acc == "vinh":
        return "nghệ an"
    if norm in LOOKUP_DISTRICT_MAP:
        return LOOKUP_DISTRICT_MAP[norm]
    if norm_no_acc in LOOKUP_DISTRICT_MAP:
        return LOOKUP_DISTRICT_MAP[norm_no_acc]

    # Bóc tách tiền tố quận/huyện/thị xã/thành phố nếu có
    for prefix in ("quận ", "huyện ", "thị xã ", "tx ", "thành phố ", "tp "):
        if norm.startswith(prefix):
            sub = norm[len(prefix):].strip()
            if sub in LOOKUP_DISTRICT_MAP:
                return LOOKUP_DISTRICT_MAP[sub]
            if sub in LOOKUP_PROVINCE_MAP:
                return LOOKUP_PROVINCE_MAP[sub]
        p_no_acc = strip_vietnamese_diacritics(prefix)
        if norm_no_acc.startswith(p_no_acc):
            sub_no_acc = norm_no_acc[len(p_no_acc):].strip()
            if sub_no_acc in LOOKUP_DISTRICT_MAP:
                return LOOKUP_DISTRICT_MAP[sub_no_acc]
            if sub_no_acc in LOOKUP_PROVINCE_MAP:
                return LOOKUP_PROVINCE_MAP[sub_no_acc]

    return None


def detect_province_from_address(addr: str | None) -> str | None:
    """Nhận diện tên tỉnh canonical từ chuỗi address bằng cách duyệt các đoạn từ cuối lên."""
    if not addr or not addr.strip():
        return None
    parts = [p.strip() for p in addr.split(",") if p.strip()]
    if not parts:
        return None
    for part in reversed(parts):
        norm_p = normalize_vietnamese_text(part)
        norm_no_acc = strip_vietnamese_diacritics(norm_p)
        if norm_no_acc in ["viet nam", "vietnam", "vn"]:
            continue
        prov = match_province_segment(part)
        if prov:
            return prov
        for k in sorted(LOOKUP_PROVINCE_MAP.keys(), key=len, reverse=True):
            if re.search(r"\b" + re.escape(k) + r"\b", norm_p):
                return LOOKUP_PROVINCE_MAP[k]
            if re.search(r"\b" + re.escape(k) + r"\b", norm_no_acc):
                return LOOKUP_PROVINCE_MAP[k]
        for k in sorted(LOOKUP_DISTRICT_MAP.keys(), key=len, reverse=True):
            if k == "vinh":
                if re.search(r"\b(?:tp\.?\s*)?vinh\b", norm_p) and "vinhomes" not in norm_p and "trà vinh" not in norm_p:
                    return "nghệ an"
                if re.search(r"\b(?:tp\.?\s*)?vinh\b", norm_no_acc) and "vinhomes" not in norm_no_acc and "tra vinh" not in norm_no_acc:
                    return "nghệ an"
                continue
            if re.search(r"\b" + re.escape(k) + r"\b", norm_p):
                return LOOKUP_DISTRICT_MAP[k]
            if re.search(r"\b" + re.escape(k) + r"\b", norm_no_acc):
                return LOOKUP_DISTRICT_MAP[k]
    return None


def extract_province_from_address(addr: str | None) -> str | None:
    """Trích xuất tên tỉnh/thành phố hiển thị từ cột address."""
    if not addr or not addr.strip():
        return None
    parts = [p.strip() for p in addr.split(",") if p.strip()]
    if not parts:
        return None
    for part in reversed(parts):
        norm_p = normalize_vietnamese_text(part)
        norm_no_acc = strip_vietnamese_diacritics(norm_p)
        if norm_no_acc in ["viet nam", "vietnam", "vn"]:
            continue
        return part
    return parts[-1]


def detect_province_from_label(label: str | None) -> str | None:
    """Nhận diện tên tỉnh/thành phố từ nhãn người dùng nhập (chuẩn hóa về tên chung)."""
    if not label or not label.strip():
        return None
    norm = normalize_vietnamese_text(label)
    if re.search(r"\b(?:tp\.?\s*)?vinh\b", norm) and "vinhomes" not in norm and "trà vinh" not in norm:
        return "nghệ an"
    for district_alias, (prov, _) in DISTRICT_CENTERS.items():
        if district_alias in ("vinh", "tp vinh", "thành phố vinh"):
            continue
        if district_alias in norm:
            return prov
    return detect_province_from_address(label)


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


def infer_coordinates_and_area_reference(
    label: str | None,
) -> tuple[float, float, dict[str, str], str | None] | None:
    """Khớp khu vực từ chuỗi nhãn theo thứ tự ưu tiên:
    1. Quét tìm Quận/Huyện có trong DISTRICT_CENTERS -> trả về (lat, lng, area_reference, prov).
    2. Nếu không khớp tâm quận: Quét tìm Tỉnh/Thành phố trong PROVINCE_CENTERS -> fallback về tâm tỉnh.
    3. Không khớp khu vực -> trả về None.
    """
    if not label or not label.strip():
        return None
    norm = normalize_vietnamese_text(label)

    # 1. Tìm Quận/Huyện
    for district_alias, (prov, coords) in DISTRICT_CENTERS.items():
        if district_alias in norm:
            dist_title = district_alias.title()
            if not any(dist_title.lower().startswith(p) for p in ["quận", "huyện", "thị xã", "tp"]):
                dist_title = f"Quận {dist_title}"
            return coords[0], coords[1], {"label": f"trung tâm {dist_title}", "level": "district"}, prov

    # 2. Fallback về tâm Tỉnh/Thành phố
    prov_canonical = detect_province_from_address(label)
    if prov_canonical and prov_canonical in PROVINCE_CENTERS:
        coords = PROVINCE_CENTERS[prov_canonical]
        prov_title = prov_canonical.title()
        return coords[0], coords[1], {"label": f"trung tâm {prov_title}", "level": "province"}, prov_canonical

    return None


def infer_coordinates_from_label(label: str | None) -> tuple[float, float] | None:
    """Wrapper tương thích ngược trả về (lat, lng) từ nhãn."""
    res = infer_coordinates_and_area_reference(label)
    if res:
        return res[0], res[1]
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

        if matched and (len(matched) >= limit or current_radius == search_radii[-1]):
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
    distance_from_area_km: float | None = None,
    power_info: str | None = None,
    note: str | None = None,
    mask_phone: bool = False,
    is_out_of_area: bool = False,
) -> ServicePointItem:
    # Không bao giờ để distance_from_area_km xuất hiện cùng lúc với distance_km khác null trên cùng một điểm
    if distance_km is not None and distance_from_area_km is not None:
        raise ValueError("distance_km and distance_from_area_km cannot both be non-null on the same point")

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
        province=extract_province_from_address(sp.address),
        distance_km=round(distance_km, 2) if distance_km is not None else None,
        distance_from_area_km=round(distance_from_area_km, 1) if distance_from_area_km is not None else None,
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
        is_out_of_area=is_out_of_area,
    )


def build_case_service_points_response(
    db: Session,
    case: Case,
    mask_phone_in_response: bool = False,
) -> ServicePointsData:
    """Tạo response đề xuất điểm dịch vụ cho một Case theo chuẩn BƯỚC 3 & 4."""
    loc: CaseLocation | None = case.location

    # Kiểm tra điều kiện tính km
    can_calculate_km = False
    ref_lat: float | None = None
    ref_lng: float | None = None
    area_ref: dict[str, str] | None = None
    target_prov: str | None = None

    if (
        loc is not None
        and loc.status != "NOT_SHARED"
        and loc.source in ("BROWSER_GPS", "MAP_PICKER")
        and is_valid_vietnam_coord(loc.latitude, loc.longitude)
    ):
        can_calculate_km = True
        ref_lat = loc.latitude
        ref_lng = loc.longitude
        area_ref = None
    elif loc is not None and loc.location_label:
        inferred = infer_coordinates_and_area_reference(loc.location_label)
        if inferred:
            ref_lat, ref_lng, area_ref, target_prov = inferred
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
    is_out_of_area = False
    message = None

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

        # Xử lý ưu tiên cùng tỉnh khi không có GPS
        if not can_calculate_km and loc and loc.location_label:
            if not target_prov:
                target_prov = detect_province_from_label(loc.location_label)
            if target_prov:
                same_prov = []
                diff_prov = []
                for sp_item in nearby_raw:
                    sp_obj = sp_item[0]
                    sp_p = detect_province_from_address(sp_obj.address)
                    if sp_p and (sp_p == target_prov):
                        same_prov.append(sp_item)
                    else:
                        diff_prov.append(sp_item)

                if same_prov:
                    nearby_raw = same_prov + diff_prov
                else:
                    # Không có điểm nào cùng tỉnh -> Lấy 5 điểm gần nhất theo khoảng cách haversine từ tâm
                    is_out_of_area = True
                    if target_category == "workshop":
                        all_ws = list(db.scalars(
                            select(ServicePoint).where(
                                ServicePoint.category == "workshop",
                                ServicePoint.is_visible.is_(True),
                                ServicePoint.is_car_compatible.is_(True),
                            )
                        ).all())
                        scored_ws = [
                            (sp, haversine_km(ref_lat, ref_lng, sp.latitude, sp.longitude))
                            for sp in all_ws
                            if sp.latitude is not None and sp.longitude is not None
                        ]
                        car_partner = [m for m in scored_ws if (m[0].category_slug or "") in ("service_car", "service_car_partner")]
                        car_partner.sort(key=lambda m: (m[1], m[0].id))
                        gsm = [m for m in scored_ws if (m[0].category_slug or "") == "service_gsm"]
                        gsm.sort(key=lambda m: (m[1], m[0].id))
                        others = [m for m in scored_ws if (m[0].category_slug or "") not in ("service_car", "service_car_partner", "service_gsm")]
                        others.sort(key=lambda m: (m[1], m[0].id))
                        res_ws = car_partner[:5]
                        if len(res_ws) < 5:
                            res_ws.extend(others[: 5 - len(res_ws)])
                        if len(res_ws) < 5:
                            res_ws.extend(gsm[: 5 - len(res_ws)])
                        nearby_raw = res_ws

                    cat_name = "xưởng" if target_category == "workshop" else "trạm sạc" if target_category == "charging_station" else "showroom"
                    if nearby_raw:
                        nearest_sp = nearby_raw[0][0]
                        nearest_dist = haversine_km(ref_lat, ref_lng, nearest_sp.latitude, nearest_sp.longitude)
                        nearest_p = extract_province_from_address(nearest_sp.address) or "tỉnh khác"
                        if area_ref:
                            if nearest_dist < 5:
                                ref_area_text = f", dưới 5 km từ {area_ref['label']}"
                            else:
                                rounded_km = round(nearest_dist)
                                ref_area_text = f", khoảng {rounded_km} km từ {area_ref['label']}"
                        else:
                            ref_area_text = ""
                        message = f"Chưa có {cat_name} trong khu vực bạn nhập; điểm gần nhất ở {nearest_p}{ref_area_text}"
                    else:
                        message = f"Chưa có {cat_name} trong khu vực bạn nhập; không tìm thấy điểm dịch vụ lân cận"

        # Khi không có GPS, sắp xếp danh sách theo khoảng cách từ tâm khu vực (ưu tiên car/partner trước gsm)
        if not can_calculate_km:
            scored_points = [
                (sp_item[0], haversine_km(ref_lat, ref_lng, sp_item[0].latitude, sp_item[0].longitude))
                for sp_item in nearby_raw
            ]
            car_part = [p for p in scored_points if (p[0].category_slug or "") in ("service_car", "service_car_partner")]
            car_part.sort(key=lambda m: (m[1], m[0].id))
            gsm_pts = [p for p in scored_points if (p[0].category_slug or "") == "service_gsm"]
            gsm_pts.sort(key=lambda m: (m[1], m[0].id))
            oth = [p for p in scored_points if (p[0].category_slug or "") not in ("service_car", "service_car_partner", "service_gsm")]
            oth.sort(key=lambda m: (m[1], m[0].id))
            nearby_raw = car_part + oth + gsm_pts

        is_collision = is_collision_or_bodywork_case(case)

        for sp, dist in nearby_raw:
            if sp.crawled_at:
                if max_crawled_at is None or sp.crawled_at > max_crawled_at:
                    max_crawled_at = sp.crawled_at

            item_dist = dist if can_calculate_km else None
            dist_from_area = round(dist, 1) if not can_calculate_km else None

            power_info = "Chưa công bố công suất" if target_category == "charging_station" else None
            note = None
            if is_out_of_area:
                item_prov = extract_province_from_address(sp.address) or "ngoại tỉnh"
                note = f"Điểm ngoại tỉnh ({item_prov})"
            elif target_category == "workshop" and is_collision and sp.dong_son:
                note = "Có làm đồng sơn"

            item = format_service_point_item(
                sp=sp,
                distance_km=item_dist,
                distance_from_area_km=dist_from_area,
                power_info=power_info,
                note=note,
                mask_phone=mask_phone_in_response,
                is_out_of_area=is_out_of_area,
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
        is_out_of_area=is_out_of_area,
        message=message,
        last_updated_label=last_updated_label,
        rescue_hotline=rescue_hotline,
        area_reference=area_ref if not can_calculate_km else None,
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
    import logging
    import os
    logger = logging.getLogger(__name__)

    mode = os.environ.get("GPS_CATALOG_MODE", "auto").strip().lower()
    from src.services.service_point_catalog import SnapshotCatalogAdapter, default_catalog_adapter, nearby_service_points
    if mode in ("demo", "snapshot") or getattr(SnapshotCatalogAdapter.load, "__name__", "") != "load":
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
        from sqlalchemy import func
        count_pts = db.scalar(select(func.count()).select_from(ServicePoint)) or 0
        if count_pts == 0:
            logger.warning("Bảng service_points rỗng, fallback sang catalog snapshot/demo")
            from src.services.service_point_catalog import default_catalog_adapter, nearby_service_points
            return nearby_service_points(lat, lng, category, radius_km, limit, default_catalog_adapter(), vehicle_type)

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
                "province": extract_province_from_address(sp.address),
                "category": cat_out,
                "vehicle_type": vehicle_type,
                "latitude": sp.latitude,
                "longitude": sp.longitude,
                "distance_km": round(dist, 3),
                "source": "VinFast (dữ liệu thu thập)",
                "updated_at": sp.crawled_at.strftime("%Y-%m-%d") if sp.crawled_at else "2026-10-15",
                "verification_status": "SNAPSHOT",
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
            "source": "VinFast (dữ liệu thu thập)",
            "updated_at": "2026-10-15",
            "verification_status": "SNAPSHOT",
            "demo": False,
            "distance_method": "AIRLINE",
            "radius_km": radius_km,
            "limit": limit,
            "vehicle_type": vehicle_type,
        }
    finally:
        if should_close_db:
            db.close()
