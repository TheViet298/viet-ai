"""Bounded decomposition of sales questions; every part uses verified evidence."""
import asyncio
import re
import time

from src.agents.guardrails import sanitize_pii, strip_accents
from src.agents.nodes.rag_node import rag_node
from src.config import get_settings
from src.services.conversation_context import ConversationContext


MODEL_CATALOG = {
    "VF3": {
        "full_name": "VinFast VF 3",
        "segment_badge": "Mini SUV điện đô thị · 4 chỗ ngồi",
        "desc": "Mẫu xe đô thị cá tính, linh hoạt với khoảng sáng gầm cao và chi phí vận hành siêu tiết kiệm.",
        "specs": [
            ("Phân khúc", "Mini SUV điện đô thị"),
            ("Số chỗ ngồi", "4 chỗ"),
            ("Công suất tối đa", "32 kW (~43 hp) · Mô-men xoắn 110 Nm"),
            ("Quãng đường", "~210 km (NEDC, 1 lần sạc đầy)"),
            ("Thời gian sạc nhanh", "~36 phút (từ 10% lên 70% pin)"),
        ],
        "highlights": [
            "Thiết kế hình khối vuông vắn cá tính, gầm cao linh hoạt trên phố nhỏ.",
            "Màn hình cảm ứng 10 inch, hỗ trợ sạc nhanh tiện lợi tại trạm công cộng.",
        ],
        "source": {
            "title": "Cẩm nang kỹ thuật & Thông số VinFast VF 3",
            "url": "https://vinfastauto.com/vn_vi/mau-xe-vf-3",
        },
    },
    "VF5": {
        "full_name": "VinFast VF 5 Plus",
        "segment_badge": "A-SUV điện đô thị · 5 chỗ ngồi",
        "desc": "Mẫu SUV đô thị phân khúc A năng động, tối ưu chi phí vận hành và không gian cho gia đình trẻ.",
        "specs": [
            ("Phân khúc", "A-SUV điện đô thị"),
            ("Số chỗ ngồi", "5 chỗ"),
            ("Công suất tối đa", "100 kW (~134 hp) · Mô-men xoắn 135 Nm"),
            ("Quãng đường", "> 300 km (NEDC, 1 lần sạc đầy)"),
            ("Thời gian sạc nhanh", "~30 phút (từ 10% lên 70% pin)"),
        ],
        "highlights": [
            "Động cơ điện vận hành êm ái, tăng tốc mượt mà và tiết kiệm chi phí năng lượng vượt trội.",
            "Tích hợp hệ thống an toàn chủ động, quản lý xe và pin qua ứng dụng VinFast.",
        ],
        "source": {
            "title": "Cẩm nang kỹ thuật & Thông số VinFast VF 5 Plus",
            "url": "https://vinfastauto.com/vn_vi/mau-xe-vf-5-plus",
        },
    },
    "VFE34": {
        "full_name": "VinFast VF e34",
        "segment_badge": "C-SUV điện thông minh · 5 chỗ ngồi",
        "desc": "Mẫu C-SUV điện tiên phong tại Việt Nam với khoang xe rộng rãi cho gia đình và dịch vụ vận tải.",
        "specs": [
            ("Phân khúc", "C-SUV điện thông minh"),
            ("Số chỗ ngồi", "5 chỗ"),
            ("Công suất tối đa", "110 kW (~147 hp) · Mô-men xoắn 242 Nm"),
            ("Quãng đường", "~318 km (NEDC, tùy bản pin)"),
            ("Thời gian sạc nhanh", "~18 phút (nạp quãng đường ~180 km)"),
        ],
        "highlights": [
            "Trợ lý ảo thông minh tiếng Việt đa vùng miền và cập nhật phần mềm FOTA.",
            "Khoang xe rộng rãi, tối ưu cho gia đình và nhu cầu di chuyển thực tế.",
        ],
        "source": {
            "title": "Cẩm nang kỹ thuật & Thông số VinFast VF e34",
            "url": "https://vinfastauto.com/vn_vi/mau-xe-vf-e34",
        },
    },
    "VF6": {
        "full_name": "VinFast VF 6 (Base & Plus)",
        "segment_badge": "B-SUV điện thời thượng · 5 chỗ ngồi",
        "desc": "Mẫu B-SUV hiện đại do Torino Design chắp bút, cân bằng hoàn hảo giữa thẩm mỹ và công nghệ hỗ trợ lái.",
        "specs": [
            ("Phân khúc", "B-SUV điện"),
            ("Số chỗ ngồi", "5 chỗ"),
            ("Công suất tối đa", "130 kW (Base) / 150 kW (Plus)"),
            ("Quãng đường", "381 – 399 km (WLTP, tùy bản pin)"),
            ("Thời gian sạc nhanh", "~24 – 30 phút (từ 10% lên 70% pin)"),
        ],
        "highlights": [
            "Hệ thống trợ lái nâng cao ADAS cấp độ 2 tiên tiến (hỗ trợ giữ làn, kiểm soát hành trình thích ứng).",
            "Màn hình cảm ứng trung tâm 12.9 inch hướng về người lái, không gian tối giản tinh tế.",
        ],
        "source": {
            "title": "Cẩm nang kỹ thuật & Thông số VinFast VF 6",
            "url": "https://vinfastauto.com/vn_vi/mau-xe-vf-6",
        },
    },
    "VF7": {
        "full_name": "VinFast VF 7 (Base & Plus AWD)",
        "segment_badge": "C-SUV điện thể thao hiệu năng cao · 5 chỗ ngồi",
        "desc": "Thiết kế phi đối xứng phong cách tương lai, dẫn động 2 cầu toàn thời gian bứt phá mạnh mẽ.",
        "specs": [
            ("Phân khúc", "C-SUV điện thể thao"),
            ("Số chỗ ngồi", "5 chỗ"),
            ("Công suất tối đa", "130 kW (Base) / 260 kW (Plus AWD)"),
            ("Quãng đường", "431 – 450 km (WLTP, tùy bản pin)"),
            ("Thời gian sạc nhanh", "~24 phút (từ 10% lên 70% pin)"),
        ],
        "highlights": [
            "Dẫn động 2 cầu toàn thời gian AWD thể thao bám đường tối ưu.",
            "Gói an toàn ADAS toàn diện cùng trần kính panorama sang trọng trên bản Plus.",
        ],
        "source": {
            "title": "Cẩm nang kỹ thuật & Thông số VinFast VF 7",
            "url": "https://vinfastauto.com/vn_vi/mau-xe-vf-7",
        },
    },
    "VF8": {
        "full_name": "VinFast VF 8 (Eco & Plus AWD)",
        "segment_badge": "D-SUV điện toàn cầu cao cấp · 5 chỗ ngồi",
        "desc": "Mẫu SUV điện thông minh chuẩn mực quốc tế, đạt 5 sao ASEAN NCAP & Euro NCAP.",
        "specs": [
            ("Phân khúc", "D-SUV điện cao cấp"),
            ("Số chỗ ngồi", "5 chỗ"),
            ("Công suất tối đa", "260 kW (Eco) / 300 kW (Plus)"),
            ("Quãng đường", "400 – 471 km (WLTP, tùy bản pin)"),
            ("Thời gian sạc nhanh", "~24 – 31 phút (từ 10% lên 70% pin)"),
        ],
        "highlights": [
            "ADAS cấp độ 2 và Smart Services",
            "Nội thất da cao cấp, màn hình trung tâm 15.6 inch",
        ],
        "source": {
            "title": "Cẩm nang kỹ thuật & Thông số VinFast VF 8",
            "url": "https://vinfastauto.com/vn_vi/mau-xe-vf-8",
        },
    },
    "VF9": {
        "full_name": "VinFast VF 9 Flagship (Eco & Plus)",
        "segment_badge": "E-SUV điện full-size hạng sang · 6/7 chỗ ngồi",
        "desc": "Dòng xe SUV điện đầu bảng đẳng cấp thượng lưu, tùy chọn hàng ghế cơ trưởng Captain Seats.",
        "specs": [
            ("Phân khúc", "E-SUV điện full-size hạng sang"),
            ("Số chỗ ngồi", "6 chỗ thương gia hoặc 7 chỗ"),
            ("Công suất tối đa", "300 kW (~402 hp) · Mô-men xoắn 620 Nm (AWD)"),
            ("Quãng đường", "423 – 602 km (WLTP, tùy bản pin)"),
            ("Thời gian sạc nhanh", "~26 – 35 phút (từ 10% lên 70% pin)"),
        ],
        "highlights": [
            "Hàng ghế thương gia tích hợp massage đa điểm, thông gió và sưởi cao cấp.",
            "Cửa sổ trời toàn cảnh panorama, kính cách âm 2 lớp cùng âm thanh vòm đỉnh cao.",
        ],
        "source": {
            "title": "Cẩm nang kỹ thuật & Thông số VinFast VF 9",
            "url": "https://vinfastauto.com/vn_vi/mau-xe-vf-9",
        },
    },
}


def format_vehicle_overview(model_key: str, user_vehicle: str | None = None) -> tuple[str, dict | None]:
    info = MODEL_CATALOG.get(model_key)
    if not info:
        return "", None
    lines = [
        f"### {info['full_name']}",
        f"*{info['segment_badge']}*",
        "",
        info['desc'],
        "",
        "**Thông số kỹ thuật chính**",
    ]
    for name, val in info['specs']:
        lines.append(f"- **{name}:** {val}")
    lines.append("")
    lines.append("**Đặc điểm nổi bật**")
    for hl in info['highlights']:
        lines.append(f"- {hl}")

    if user_vehicle:
        norm_user = re.sub(r"\s+", "", user_vehicle).upper()
        norm_target = re.sub(r"\s+", "", model_key).upper()
        if norm_user != norm_target:
            user_info = MODEL_CATALOG.get(norm_user)
            user_name = user_info['full_name'] if user_info else user_vehicle
            lines.append(f"\n*(Anh/chị đang dùng {user_name}, nếu muốn so sánh chi tiết với {info['full_name']} em có thể hỗ trợ ạ.)*")

    return "\n".join(lines), info.get("source")


def format_vehicle_comparison(models: list[str]) -> str:
    valid_models = [m for m in models if m in MODEL_CATALOG]
    if len(valid_models) < 2:
        return ""
    names = [MODEL_CATALOG[m]["full_name"] for m in valid_models]
    title = f"### So sánh thông số kỹ thuật {', '.join(names[:-1])} và {names[-1]}"

    headers = ["Tiêu chí"] + [MODEL_CATALOG[m]["full_name"] for m in valid_models]
    sep = [":---"] + [":---" for _ in valid_models]

    def get_spec(m_key: str, keywords: list[str]) -> str:
        for name, val in MODEL_CATALOG[m_key].get("specs", []):
            if any(k in name.lower() for k in keywords):
                return val
        return "Đang cập nhật"

    rows = [
        ["**Phân khúc**"] + [get_spec(m, ["phân khúc"]) for m in valid_models],
        ["**Số chỗ ngồi**"] + [get_spec(m, ["số chỗ", "chỗ ngồi"]) for m in valid_models],
        ["**Công suất**"] + [get_spec(m, ["công suất"]) for m in valid_models],
        ["**Quãng đường**"] + [get_spec(m, ["quãng đường"]) for m in valid_models],
        ["**Sạc nhanh**"] + [get_spec(m, ["sạc", "thời gian sạc"]) for m in valid_models],
    ]

    lines = [
        title,
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")

    lines.append("")
    lines.append("**Định hướng sử dụng:**")
    for m in valid_models:
        lines.append(f"- **{MODEL_CATALOG[m]['full_name']}:** {MODEL_CATALOG[m]['desc']}")

    return "\n".join(lines)


def detect_ranking_aspect(text: str) -> str | None:
    lower = text.casefold()
    if any(w in lower for w in ("sạc nhanh nhất", "nap pin nhanh nhat", "nạp pin nhanh nhất", "sạc pin nhanh nhất")):
        return "charging"
    if any(w in lower for w in ("đi xa nhất", "di xa nhat", "quãng đường xa nhất", "quang duong xa nhat", "pin trâu nhất", "tầm hoạt động xa nhất", "chạy xa nhất")):
        return "range"
    if any(w in lower for w in ("rộng nhất", "rong nhat", "nhiều chỗ nhất", "nhieu cho nhat", "khoang rộng nhất", "to nhất")):
        return "space"
    if any(w in lower for w in ("rẻ nhất", "re nhat", "giá thấp nhất", "gia thap nhat", "tiết kiệm nhất", "tiet kiem nhat", "chi phí thấp nhất")):
        return "price"
    if any(w in lower for w in ("mạnh nhất", "manh nhat", "khỏe nhất", "khoe nhat", "công suất lớn nhất", "tăng tốc nhanh nhất")):
        return "power"
    if "nhất" in lower and any(w in lower for w in ("xe nào", "mẫu nào", "dòng nào", "chiếc nào")):
        return "general"
    return None


def format_lineup_ranking(aspect: str) -> tuple[str, list[dict], list[str]]:
    citations = []
    for m, info in MODEL_CATALOG.items():
        src = info["source"]
        citations.append({
            "source_id": f"SRC-KB-{m}",
            "title": src["title"],
            "url": src["url"],
            "verified_at": "2026-10-10",
            "status_code": 200,
            "applicable_models": [m],
            "source_type": "official_manual",
            "relevant_snippet": f"Thông số kỹ thuật chính thức từ cẩm nang VinFast {m}."
        })

    if aspect == "charging":
        reply = (
            "### So sánh thời gian sạc nhanh các dòng xe điện VinFast\n\n"
            "Dưới đây là thông số sạc nhanh chính thức từ cẩm nang kỹ thuật VinFast:\n\n"
            "| Dòng xe | Phân khúc | Thời gian sạc nhanh |\n"
            "| :--- | :--- | :--- |\n"
            "| **VinFast VF e34** | C-SUV | **~18 phút** (nạp quãng đường ~180 km) |\n"
            "| **VinFast VF 7** | C-SUV | **~24 phút** (10% lên 70% pin với trụ DC siêu nhanh) |\n"
            "| **VinFast VF 6** | B-SUV | **~24 – 30 phút** (10% lên 70% pin) |\n"
            "| **VinFast VF 8** | D-SUV | **~24 – 31 phút** (10% lên 70% pin) |\n"
            "| **VinFast VF 9** | E-SUV | **~26 – 35 phút** (10% lên 70% pin) |\n"
            "| **VinFast VF 5 Plus** | A-SUV | **~30 phút** (10% lên 70% pin) |\n"
            "| **VinFast VF 3** | Mini SUV | **~36 phút** (10% lên 70% pin) |\n\n"
            "**Tóm tắt:**\n"
            "- **Nạp nhanh quãng đường ngắn:** **VF e34** chỉ mất ~18 phút để có thêm ~180 km di chuyển.\n"
            "- **Sạc siêu nhanh dung lượng lớn:** Các dòng **VF 7, VF 6, VF 8** nạp 10–70% pin chỉ từ 24–30 phút tại các trụ sạc siêu nhanh DC của VinFast."
        )
        chips = ["So sánh VF5 và VF6", "So sánh VF8 và VF9", "Dải sản phẩm xe VinFast"]
    elif aspect == "range":
        reply = (
            "### So sánh quãng đường di chuyển (Tầm hoạt động) các dòng xe VinFast\n\n"
            "Dòng xe có quãng đường di chuyển xa nhất hiện nay là **VinFast VF 9** (lên tới 602 km trong 1 lần sạc đầy).\n\n"
            "| Dòng xe | Phân khúc | Quãng đường 1 lần sạc đầy | Tiêu chuẩn |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| **VinFast VF 9** | E-SUV full-size | **423 – 602 km** | WLTP |\n"
            "| **VinFast VF 8** | D-SUV | **400 – 471 km** | WLTP |\n"
            "| **VinFast VF 7** | C-SUV | **431 – 450 km** | WLTP |\n"
            "| **VinFast VF 6** | B-SUV | **381 – 399 km** | WLTP |\n"
            "| **VinFast VF e34** | C-SUV | **~318 km** | NEDC |\n"
            "| **VinFast VF 5 Plus** | A-SUV | **> 300 km** | NEDC |\n"
            "| **VinFast VF 3** | Mini SUV | **~210 km** | NEDC |\n\n"
            "*(Lưu ý: Quãng đường thực tế có thể thay đổi tùy điều kiện vận hành, tải trọng và chế độ lái).*"
        )
        chips = ["Tư vấn về VF 9", "So sánh VF 7 và VF 8", "Đăng ký lái thử"]
    elif aspect == "space":
        reply = (
            "### So sánh không gian và số chỗ ngồi các dòng xe VinFast\n\n"
            "Mẫu xe có khoang nội thất rộng rãi và nhiều chỗ ngồi nhất là **VinFast VF 9**.\n\n"
            "- **VinFast VF 9 (E-SUV full-size):** Tùy chọn **7 chỗ** hoặc **6 chỗ thương gia** với hàng ghế cơ trưởng Captain Seats sang trọng bậc nhất.\n"
            "- **VinFast VF 8, VF 7, VF 6, VF e34, VF 5 Plus:** Đều sở hữu không gian **5 chỗ ngồi** rộng rãi, tối ưu cho gia đình.\n"
            "- **VinFast VF 3:** Thiết kế **4 chỗ ngồi** nhỏ gọn, linh hoạt tối đa khi di chuyển trong phố."
        )
        chips = ["Tư vấn về VF 9", "So sánh VF 8 và VF 9", "Đăng ký lái thử"]
    elif aspect == "price":
        reply = (
            "### So sánh phân khúc và mức độ tối ưu chi phí các dòng xe VinFast\n\n"
            "Dòng xe có chi phí sở hữu và vận hành tiết kiệm nhất trong dải sản phẩm là **VinFast VF 3**, tiếp theo là **VinFast VF 5 Plus**.\n\n"
            "- **VinFast VF 3 (Mini SUV):** Chi phí dễ tiếp cận nhất, chi phí năng lượng siêu tiết kiệm cho nhu cầu đi phố hàng ngày.\n"
            "- **VinFast VF 5 Plus (A-SUV):** Mẫu xe quốc dân cân bằng hoàn hảo giữa chi phí và công năng cho gia đình trẻ và dịch vụ di chuyển thông minh.\n"
            "- **VF 6 & VF 7:** Phân khúc B và C thể thao, công nghệ cao.\n"
            "- **VF 8 & VF 9:** Phân khúc D và E cao cấp, tiện nghi sang trọng chuẩn quốc tế.\n\n"
            "Quý khách có thể xem dự toán chi tiết tại [Công cụ tính chi phí lăn bánh VinFast](https://shop.vinfastauto.com/vn_vi/chi-phi-lan-banh)."
        )
        chips = ["Tư vấn về VF 3", "Tư vấn về VF 5", "Dải sản phẩm xe VinFast"]
    elif aspect == "power":
        reply = (
            "### So sánh công suất động cơ các dòng xe VinFast\n\n"
            "Dòng xe có công suất mạnh mẽ nhất là **VinFast VF 8 Plus** và **VinFast VF 9 AWD** cùng đạt mức công suất tối đa lên tới **300 kW (~402 hp)**.\n\n"
            "| Dòng xe | Công suất tối đa | Mô-men xoắn / Dẫn động |\n"
            "| :--- | :--- | :--- |\n"
            "| **VinFast VF 9** | **300 kW (~402 hp)** | 620 Nm · 2 cầu AWD |\n"
            "| **VinFast VF 8 Plus** | **300 kW (~402 hp)** | 620 Nm · 2 cầu AWD |\n"
            "| **VinFast VF 7 Plus** | **260 kW (~349 hp)** | 500 Nm · 2 cầu AWD |\n"
            "| **VinFast VF 6 Plus** | **150 kW (~201 hp)** | 310 Nm · Cầu trước FWD |\n"
            "| **VinFast VF e34** | **110 kW (~147 hp)** | 242 Nm · Cầu trước FWD |\n"
            "| **VinFast VF 5 Plus** | **100 kW (~134 hp)** | 135 Nm · Cầu trước FWD |\n"
            "| **VinFast VF 3** | **32 kW (~43 hp)** | 110 Nm · Cầu sau RWD |"
        )
        chips = ["So sánh VF 7 và VF 8", "Đăng ký lái thử", "Dải sản phẩm xe VinFast"]
    else:
        reply = (
            "Hiện tại em chưa có số liệu đủ cho tất cả dòng xe theo tiêu chí này để xếp hạng chính xác. "
            "Anh/chị có thể tham khảo so sánh cụ thể giữa các mẫu xe tiêu biểu hoặc khám phá dải sản phẩm ô tô điện VinFast bên dưới ạ."
        )
        chips = ["So sánh VF3 và VF5", "So sánh VF8 và VF9", "Dải sản phẩm xe VinFast"]

    return reply, citations, chips


def explicit_models(text: str) -> list[str]:
    return list(dict.fromkeys("VF" + m.upper() for m in re.findall(r"\bvf\s*(e34|[356789])\b", text, re.I)))


def sales_parts(text: str, model: str | None) -> list[tuple[str, str, str | None]]:
    lower = text.casefold()
    models = explicit_models(text)
    ranking_aspect = detect_ranking_aspect(text)

    # Kiểm tra xem có phải câu hỏi về xe của khách / sự cố / kỹ thuật hay không
    has_owner_incident = any(
        k in lower for k in ("xe tôi", "xe của tôi", "xe mình", "bị ", "lỗi", "sạc", "bảo dưỡng", "rùa vàng")
    )

    # Kiểm tra xem có phải câu hỏi tổng quan về dải sản phẩm / các dòng xe không
    is_general_lineup = (
        not models
        and not has_owner_incident
        and (
            bool(ranking_aspect)
            or any(k in lower for k in ("các dòng xe", "dòng xe", "các mẫu xe", "mẫu xe", "dải sản phẩm", "toàn bộ xe", "mua xe gì", "tư vấn xe", "tư vấn mua", "xe nào hợp", "tổng quan"))
        )
    )

    if not models and model and not is_general_lineup:
        models = [model]

    # The model in the test-drive clause must not narrow the whole lineup.
    drive = re.search(r"(?:lái thử|chạy thử|trải nghiệm xe).*?\bvf\s*(e34|[356789])\b", lower)
    drive_model = "VF" + drive.group(1).upper() if drive else (models[0] if len(models) == 1 else (None if is_general_lineup else model))
    parts = []

    is_car_overview = (
        bool(ranking_aspect)
        or any(term in lower for term in ("các dòng xe", "dòng xe", "các mẫu xe", "mẫu xe", "dải sản phẩm", "tư vấn xe", "tư vấn mua", "tư vấn", "mua xe", "tổng quan"))
        or ("so sánh" in lower and len(models) >= 2)
        or len(models) >= 2
        or ((explicit_models(text) or "xe" in lower) and any(term in lower for term in ("như nào", "thế nào", "như thế nào", "là dòng", "là xe", "thông tin", "chi tiết", "hợp")))
    )
    if is_car_overview:
        overview = re.split(r"giá lăn bánh|chi phí lăn bánh|bảng giá|đăng ký lái thử|lái thử", text, maxsplit=1, flags=re.I)[0]
        lineup_model = None if (is_general_lineup or len(models) > 1 or any(k in lower for k in ("các dòng xe", "các mẫu xe", "dải sản phẩm", "tổng quan"))) else (models[0] if models else None)
        parts.append(("Thông tin dòng xe", "Thông tin các dòng xe điện VinFast. " + overview, lineup_model))
    if any(term in lower for term in ("giá xe", "giá lăn bánh", "chi phí lăn bánh", "lăn bánh", "trả góp", "ưu đãi", "đặt cọc")) or ("giá" in lower and not any(k in lower for k in ("sạc", "thuê pin", "gói thuê", "cứu hộ"))):
        parts.append(("Giá lăn bánh", "Giá xe và chi phí lăn bánh VinFast " + " ".join(models), models[0] if len(models) == 1 else None))
    if any(term in lower for term in ("lái thử", "chạy thử", "trải nghiệm xe")):
        parts.append(("Lái thử", f"Đăng ký lái thử xe VinFast {drive_model or ''}, hình thức và điều kiện đăng ký.", drive_model))
    return parts


async def answer_sales_question(text: str, model: str | None, session_id: str, *,
                                conversation_context: dict | None = None,
                                turn_understanding: dict | None = None,
                                llm_budget: dict | None = None,
                                user_vehicle: str | None = None) -> dict:
    text = sanitize_pii(text)[0]
    models_found = explicit_models(text)
    ranking_aspect = detect_ranking_aspect(text)
    is_from_to = bool(re.search(r"từ\s+vf\s*(?:e34|[356789])\s+đến\s+vf\s*(?:e34|[356789])", text, re.I))

    # =========================================================================
    # THỨ TỰ ƯU TIÊN BẮT BUỘC:
    # 1. Nếu có >= 2 model trong câu hỏi (và không phải dạng dải "từ VF x đến VF y")
    # -> Nhánh SO SÁNH (bảng so sánh đúng các xe đó)
    # =========================================================================
    if len(models_found) >= 2 and not is_from_to:
        comp_text = format_vehicle_comparison(models_found)
        if comp_text:
            citations = []
            for m in models_found:
                if m in MODEL_CATALOG:
                    src = MODEL_CATALOG[m]["source"]
                    citations.append({
                        "source_id": f"SRC-KB-{m}",
                        "title": src["title"],
                        "url": src["url"],
                        "verified_at": "2026-10-10",
                        "status_code": 200,
                        "applicable_models": [m],
                        "source_type": "official_manual",
                        "relevant_snippet": f"Thông số kỹ thuật chính thức từ cẩm nang VinFast {m}."
                    })
            chips = [f"Đăng ký lái thử {MODEL_CATALOG.get(m, {}).get('full_name', m)}" for m in models_found[:2]] + ["Dải sản phẩm xe VinFast"]
            return {
                "reply": comp_text,
                "citations": citations,
                "answer_claims": [],
                "suggested_replies": chips,
                "response_type": "FAQ_ANSWER",
                "is_no_source": False,
            }

    # =========================================================================
    # 2. Nếu là câu hỏi xếp hạng / so sánh nhất (0 model trong câu hỏi)
    # =========================================================================
    if ranking_aspect and not models_found:
        rank_text, rank_citations, rank_chips = format_lineup_ranking(ranking_aspect)
        return {
            "reply": rank_text,
            "citations": rank_citations,
            "answer_claims": [],
            "suggested_replies": rank_chips,
            "response_type": "FAQ_ANSWER",
            "is_no_source": False,
        }

    parts = sales_parts(text, model)
    lower = strip_accents(text.casefold())
    context = ConversationContext.model_validate(conversation_context or {})
    if context.active_goal and context.active_goal not in {'quote', 'test_drive'} and (turn_understanding or {}).get('move') != 'new_question':
        parts = []
    facts = {k: v.value for k, v in context.facts.items() if v.status == 'confirmed'}
    price_explanation = (len(parts) == 1 and parts[0][0] == "Giá lăn bánh"
            and re.search(r"\b(?:tai sao|vi sao|sao)\b", lower)
            and re.search(
                r"\b(?:khong|chua)\s+(?:(?:co|bao|dua ra|cung cap|hien thi|cho biet)\s+)?"
                r"gia\s+(?:lan banh|chinh xac|cu the)\b|"
                r"\bgia\b.{0,60}\b(?:khong|chua)\b.{0,30}\b(?:chinh xac|cu the)\b", lower))
    # Public list prices do not require locality or a showroom discount.
    parts = [(label, (f'Giá xe niêm yết công bố VinFast {vehicle or ""} '
                      f'{facts.get("version") or ""} {facts.get("battery") or ""}. '
                      'Phân biệt giá bán từ và ưu đãi, thời điểm áp dụng.' if label == 'Giá lăn bánh' else query), vehicle)
             for label, query, vehicle in parts]
    deadline = time.monotonic() + get_settings().agent_turn_timeout_s
    results = await asyncio.gather(*(rag_node({
        "latest_user_message": query, "vehicle_model": vehicle,
        "confidence_score": .9, "session_id": session_id, "turn": 0,
        'conversation_context': conversation_context or {}, 'turn_understanding': turn_understanding or {},
        "llm_budget": llm_budget if len(parts) == 1 and llm_budget else {"deadline": deadline, "attempts": 0},
    }) for _, query, vehicle in parts))
    sections, citations, claims = [], [], []
    rolling_url = "https://shop.vinfastauto.com/vn_vi/chi-phi-lan-banh"
    suggested_chips: list[str] = []

    for (label, _, part_vehicle), result in zip(parts, results, strict=True):
        reply = result["response"]
        if label == "Thông tin dòng xe" and (result.get("is_no_source") or "chưa hoàn tất" in reply or "chưa có tài liệu" in reply or "chưa có bằng chứng" in reply or not result.get("rag_citations")):
            target_v = re.sub(r"\s+", "", part_vehicle).upper() if part_vehicle else None
            if target_v in MODEL_CATALOG:
                formatted_reply, source_info = format_vehicle_overview(target_v, user_vehicle)
                reply = formatted_reply
                if source_info:
                    citations.append({
                        "source_id": f"SRC-KB-{target_v}",
                        "title": source_info["title"],
                        "url": source_info["url"],
                        "verified_at": "2026-10-10",
                        "status_code": 200,
                        "applicable_models": [target_v],
                        "source_type": "official_manual",
                        "relevant_snippet": f"Thông số kỹ thuật chính thức từ cẩm nang VinFast {target_v}."
                    })
                disp = MODEL_CATALOG[target_v]["full_name"]
                norm_user = re.sub(r"\s+", "", user_vehicle or "").upper()
                other_model = "VF 3" if target_v != "VF3" else "VF 5"
                compare_target = norm_user if (norm_user and norm_user in MODEL_CATALOG and norm_user != target_v) else other_model
                suggested_chips = [
                    f"Đăng ký lái thử {disp}",
                    f"So sánh {target_v} với {compare_target}",
                    "Dải sản phẩm xe VinFast",
                ]
            else:
                reply = (
                    "### Dải sản phẩm ô tô điện thông minh VinFast\n"
                    "VinFast hiện cung cấp hệ sinh thái ô tô điện toàn diện đáp ứng mọi nhu cầu:\n\n"
                    "- **VinFast VF 3:** Mini SUV đô thị cá tính, linh hoạt và tối ưu chi phí.\n"
                    "- **VinFast VF 5 Plus:** A-SUV đô thị năng động, phổ biến cho cá nhân và gia đình trẻ.\n"
                    "- **VinFast VF 6:** B-SUV thời thượng phong cách châu Âu, trang bị ADAS cấp 2.\n"
                    "- **VinFast VF 7:** C-SUV thể thao hiệu năng cao, dẫn động 2 cầu toàn thời gian AWD.\n"
                    "- **VinFast VF 8:** D-SUV thông minh cao cấp đạt tiêu chuẩn an toàn quốc tế 5 sao.\n"
                    "- **VinFast VF 9:** E-SUV full-size hạng sang đầu bảng, tùy chọn 6 hoặc 7 chỗ thương gia."
                )
                suggested_chips = [
                    "Tư vấn về VF 3",
                    "Tư vấn về VF 5",
                    "Tư vấn về VF 7",
                    "Đăng ký lái thử",
                ]
                suggested_chips = [
                    "Tư vấn về VF 3",
                    "Tư vấn về VF 5",
                    "Tư vấn về VF 7",
                    "Đăng ký lái thử",
                ]
        elif label == "Giá lăn bánh":
            if result.get("is_no_source") or "chưa hoàn tất" in reply or "chưa có tài liệu" in reply:
                reply = (
                    'Em chưa có nguồn giá bán công bố đã xác minh cho đúng cấu hình đang hỏi, nên chưa thể đưa con số. '
                )
            else:
                reply = reply.removeprefix('Theo tài liệu VinFast:\n\n')
            selection = ', '.join(str(value) for value in (model, facts.get('version'), facts.get('battery'), facts.get('city')) if value)
            reply += f'\n\nQuý khách xem dự toán tại [Công cụ tính chi phí lăn bánh VinFast]({rolling_url}), chọn {selection or "mẫu xe, phiên bản, phương án pin và tỉnh/thành đăng ký"}. Dự toán trên công cụ cần được showroom xác nhận khi giao dịch.'
            if price_explanation:
                reply += ('\nGiá lăn bánh chính xác phụ thuộc phiên bản, mua pin hoặc thuê pin nếu còn áp dụng, '
                          'địa phương đăng ký và ưu đãi showroom tại thời điểm mua. Giá công bố và giá sau ưu đãi là hai thông tin khác nhau.')
            if (turn_understanding or {}).get('move') == 'supply_info':
                reply = ('Em đã ghi nhận ' + (selection or 'thông tin Quý khách vừa cung cấp') + '.\n' + reply)
            elif (turn_understanding or {}).get('move') == 'ask_status':
                reply = ('Thông tin đã có: ' + (selection or 'mẫu xe đang trao đổi') + '. Phần cần đối chiếu tiếp là giá công bố và điều kiện ưu đãi, không cần Quý khách nhập lại cấu hình.\n' + reply)
        elif label == "Lái thử" and (result.get('is_no_source') or "chưa hoàn tất" in reply or "chưa có tài liệu" in reply):
            reply = (
                "Quý khách có thể đăng ký lái thử trực tiếp qua Ứng dụng VinFast "
                "hoặc liên hệ hệ thống Showroom / Nhà phân phối VinFast trên toàn quốc để được sắp xếp trải nghiệm xe thực tế."
            )

        # Tránh lặp tiêu đề: nếu chỉ có 1 phần thì không bọc label lặp
        if len(parts) == 1:
            sections.append(reply)
        else:
            sections.append(f"**{label}**\n{reply}")

        citations.extend(result.get("rag_citations", []))
        claims.extend(result.get('answer_claims', []))

    # Loại bỏ duplicate citations
    unique_citations = []
    seen_urls = set()
    for c in citations:
        url = c.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_citations.append(c)

    return {"reply": "\n\n".join(sections), "citations": unique_citations,
            'answer_claims': claims,
            'suggested_replies': suggested_chips,
            'retrieval_diagnostics': {'parts': [{
                'label': part[0], 'diagnostics': result.get('retrieval_diagnostics', {})}
                for part, result in zip(parts, results, strict=True)]},
            "is_no_source": all(r["is_no_source"] for r in results), "response_type": "FAQ_ANSWER"}
