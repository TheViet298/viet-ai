"""Generate publication-quality Use Case diagram for VinFast ServiceFlow AI.

Run: python3 docs/architecture/serviceflow-usecase.py
Outputs: docs/architecture/serviceflow-usecase.svg
"""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent / "serviceflow-usecase.svg"

parts = []


def text(x, y, value, size=14, weight=400, color="#263747", anchor="start", style="normal"):
    font_style = f' font-style="{style}"' if style != "normal" else ""
    parts.append(
        f'<text x="{x}" y="{y}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}" '
        f'text-anchor="{anchor}"{font_style}>{escape(value)}</text>'
    )


def multiline_text(cx, cy, lines, size=13, weight=400, color="#263747", line_height=18, style="normal"):
    start_y = cy - ((len(lines) - 1) * line_height) / 2 + (size * 0.35)
    for i, line in enumerate(lines):
        text(cx, start_y + i * line_height, line, size=size, weight=weight, color=color, anchor="middle", style=style)


def usecase(cx, cy, rx, ry, label_lines, fill="#edf1f5", stroke="#8e9fad", text_color="#263747", bold=False, style="normal", size=13):
    parts.append(
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.3"/>'
    )
    multiline_text(cx, cy, label_lines, size=size, weight=600 if bold else 400, color=text_color, style=style)


def actor_human(cx, cy, name, role, en_name, color="#5b7a9c", bg="#eaf2fb"):
    # Head
    parts.append(f'<circle cx="{cx}" cy="{cy-32}" r="14" fill="{bg}" stroke="{color}" stroke-width="1.8"/>')
    # Torso
    parts.append(f'<line x1="{cx}" y1="{cy-18}" x2="{cx}" y2="{cy+16}" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>')
    # Arms
    parts.append(f'<line x1="{cx-22}" y1="{cy-6}" x2="{cx+22}" y2="{cy-6}" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>')
    # Legs
    parts.append(f'<line x1="{cx}" y1="{cy+16}" x2="{cx-16}" y2="{cy+42}" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>')
    parts.append(f'<line x1="{cx}" y1="{cy+16}" x2="{cx+16}" y2="{cy+42}" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>')
    # Labels
    text(cx, cy + 62, f"«{role}»", size=11, color="#607080", anchor="middle")
    text(cx, cy + 78, name, size=14, weight=600, color="#263747", anchor="middle")
    text(cx, cy + 95, f"({en_name})", size=12, color="#486581", anchor="middle")


def actor_system(cx, cy, name, role, en_name, color="#7d6ba8", bg="#f0edf8"):
    w, h = 64, 52
    parts.append(f'<rect x="{cx-w/2}" y="{cy-h/2}" width="{w}" height="{h}" rx="6" fill="{bg}" stroke="{color}" stroke-width="1.8"/>')
    # Inner rack bars
    parts.append(f'<line x1="{cx-20}" y1="{cy-12}" x2="{cx+20}" y2="{cy-12}" stroke="{color}" stroke-width="1.4"/>')
    parts.append(f'<line x1="{cx-20}" y1="{cy}" x2="{cx+20}" y2="{cy}" stroke="{color}" stroke-width="1.4"/>')
    parts.append(f'<line x1="{cx-20}" y1="{cy+12}" x2="{cx+20}" y2="{cy+12}" stroke="{color}" stroke-width="1.4"/>')
    parts.append(f'<circle cx="{cx+14}" cy="{cy-12}" r="2" fill="{color}"/>')
    parts.append(f'<circle cx="{cx+14}" cy="{cy}" r="2" fill="{color}"/>')
    parts.append(f'<circle cx="{cx+14}" cy="{cy+12}" r="2" fill="{color}"/>')
    # Labels
    text(cx, cy + 42, f"«{role}»", size=11, color="#607080", anchor="middle")
    text(cx, cy + 58, name, size=14, weight=600, color="#263747", anchor="middle")
    text(cx, cy + 75, f"({en_name})", size=12, color="#486581", anchor="middle")


def line_assoc(points, stroke="#506273"):
    pts = " ".join(f"{p[0]},{p[1]}" for p in points)
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{stroke}" stroke-width="1.3"/>')


def line_include_extend(points, lx, ly, is_include=True, note=None):
    pts = " ".join(f"{p[0]},{p[1]}" for p in points)
    tag = "«include»" if is_include else "«extend»"
    parts.append(
        f'<polyline points="{pts}" fill="none" stroke="#506273" stroke-width="1.2" '
        f'stroke-dasharray="5 4" marker-end="url(#arrow)"/>'
    )
    text(lx, ly, tag, size=11, color="#2b4366", weight=600, style="italic", anchor="middle")
    if note:
        text(lx, ly + 13, note, size=9.5, color="#556980", anchor="middle")


def line_generalize(points):
    pts = " ".join(f"{p[0]},{p[1]}" for p in points)
    parts.append(
        f'<polyline points="{pts}" fill="none" stroke="#506273" stroke-width="1.2" '
        f'marker-end="url(#triangle)"/>'
    )


def build_svg():
    parts.clear()
    width, height = 1600, 1180
    parts.extend([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="320mm" height="236mm" xml:lang="vi" role="img" aria-labelledby="title desc">',
        '<title id="title">ServiceFlow — Sơ đồ Use Case toàn hệ thống</title>',
        '<desc id="desc">Sơ đồ Use Case thể hiện ranh giới hệ thống VinFast ServiceFlow AI, các tác nhân Guest, Customer, Staff, Google Gemini cùng các quan hệ include, extend và generalization.</desc>',
        '<defs>',
        '  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">',
        '    <path d="M 0 1 L 9 5 L 0 9" fill="none" stroke="#506273" stroke-width="1.4"/>',
        '  </marker>',
        '  <marker id="triangle" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="9" markerHeight="9" orient="auto">',
        '    <path d="M 1 1 L 11 6 L 1 11 Z" fill="white" stroke="#506273" stroke-width="1.3"/>',
        '  </marker>',
        '</defs>',
        f'<rect width="{width}" height="{height}" fill="white"/>',
    ])

    # Header
    text(45, 48, "ServiceFlow · Sơ đồ Use Case toàn hệ thống", size=26, weight=600, color="#102a43")
    text(45, 78, "Hệ thống VinFast ServiceFlow AI · Tác nhân, ranh giới hệ thống, ca sử dụng nghiệp vụ và quan hệ chuẩn UML 2.5", size=15, color="#486581")

    # System Boundary Box
    parts.append('<rect x="190" y="105" width="1220" height="990" rx="10" fill="#ffffff" stroke="#7b8e9f" stroke-width="1.5"/>')
    text(215, 134, "HỆ THỐNG VINFAST SERVICEFLOW AI", size=15, weight=600, color="#102a43")
    text(1390, 134, "Ranh giới ứng dụng chính (FastAPI, SQLite, ChromaDB & Agent Engine)", size=13, color="#627d98", anchor="end")

    # --------------------------------------------------------------------------
    # Subsystem Packages
    # --------------------------------------------------------------------------
    # Package 1: Public & Auth
    parts.append('<rect x="210" y="145" width="1180" height="140" rx="6" fill="#f8fafc" stroke="#bcccdc" stroke-width="1" stroke-dasharray="4 3"/>')
    text(225, 168, "PHÂN HỆ XÁC THỰC & TRI THỨC CÔNG KHAI", size=12, weight=600, color="#334e68")

    # Package 2: Customer Service
    parts.append('<rect x="210" y="300" width="740" height="780" rx="6" fill="#f8fafc" stroke="#bcccdc" stroke-width="1" stroke-dasharray="4 3"/>')
    text(225, 322, "PHÂN HỆ TIẾP NHẬN & XỬ LÝ SỰ CỐ KHÁCH HÀNG", size=12, weight=600, color="#334e68")

    # Package 3: Staff HITL
    parts.append('<rect x="970" y="300" width="420" height="780" rx="6" fill="#f8fafc" stroke="#bcccdc" stroke-width="1" stroke-dasharray="4 3"/>')
    text(985, 322, "BÀN ĐIỀU PHỐI & ĐÁNH GIÁ (STAFF HITL)", size=12, weight=600, color="#334e68")

    # --------------------------------------------------------------------------
    # Actors
    # --------------------------------------------------------------------------
    actor_human(90, 205, "Khách vãng lai", "primary actor", "Guest")
    actor_human(90, 560, "Khách hàng", "primary actor", "Customer")
    actor_human(1505, 460, "Nhân viên dịch vụ", "primary actor", "Staff / Reviewer")
    actor_system(1505, 840, "Google Gemini", "external system", "LLM Service")

    # --------------------------------------------------------------------------
    # Use Cases - Package 1 (Public & Auth)
    # --------------------------------------------------------------------------
    usecase(340, 215, 95, 30, ["Xem tài liệu &", "FAQ công khai"])
    usecase(580, 215, 95, 30, ["Đăng ký tài khoản", "khách hàng"])
    usecase(830, 215, 100, 30, ["Đăng nhập hệ thống", "(Cấp JWT Token)"])
    usecase(1100, 215, 95, 30, ["Xem thông tin", "hồ sơ cá nhân"])

    # --------------------------------------------------------------------------
    # Use Cases - Package 2 (Customer)
    # --------------------------------------------------------------------------
    # Column 1 (Left): Attachments, Emergency, Tracking, History, Reopen, Feedback
    usecase(335, 365, 95, 30, ["Tải ảnh táp-lô", "& trụ sạc"], fill="#edf5ee", stroke="#7eaa89")
    usecase(335, 465, 100, 30, ["Cung cấp Hotline", "& cứu hộ khẩn cấp"], fill="#fbebeb", stroke="#c4787e")
    usecase(335, 640, 95, 30, ["Theo dõi trạng thái", "tiến độ hồ sơ"])
    usecase(335, 730, 95, 30, ["Xem danh sách", "hồ sơ cá nhân"])
    usecase(335, 820, 95, 30, ["Mở lại hồ sơ", "đã giải quyết"])
    usecase(335, 910, 95, 30, ["Đánh giá chất lượng", "xử lý sự cố (CSAT)"])

    # Column 2 (Center): Core Chat & Case Creation
    usecase(580, 465, 110, 36, ["Trò chuyện hỗ trợ", "& tiếp nhận sự cố"], fill="#eaf2fb", stroke="#627d98", bold=True)
    usecase(580, 640, 110, 35, ["Tạo hồ sơ hỗ trợ", "& tóm tắt sự cố"], fill="#edf5ee", stroke="#7eaa89")

    # Column 3 (Right): Triage, Clarify, RAG, Synthesize Brief
    usecase(825, 375, 95, 30, ["Kiểm tra an toàn", "& triage Intent"], fill="#fbebeb", stroke="#c4787e", style="italic")
    usecase(825, 465, 95, 30, ["Hỏi làm rõ", "thông tin kỹ thuật"])
    usecase(825, 550, 95, 30, ["Tra cứu cẩm nang", "& trích dẫn RAG"], fill="#f0edf8", stroke="#9b8ec4")
    usecase(825, 640, 95, 35, ["Tổng hợp Case Brief", "chuẩn hóa JSON"], fill="#f0edf8", stroke="#9b8ec4", style="italic")

    # --------------------------------------------------------------------------
    # Use Cases - Package 3 (Staff HITL)
    # --------------------------------------------------------------------------
    usecase(1180, 365, 110, 30, ["Xem hàng đợi ticket", "theo bộ lọc"])
    usecase(1180, 455, 110, 30, ["Kiểm tra chi tiết hồ sơ", "& lịch sử hội thoại"])

    # Core Action
    usecase(1180, 565, 120, 36, ["Xử lý & điều phối", "hồ sơ (HITL Action)"], fill="#eaf2fb", stroke="#627d98", bold=True)

    # Sub-actions (Generalization)
    usecase(1075, 675, 75, 25, ["Duyệt & phân công", "điều phối"], size=11)
    usecase(1285, 675, 75, 25, ["Chỉnh sửa tóm tắt", "Case Brief"], size=11)
    usecase(1075, 745, 75, 25, ["Chuyển tuyến", "xử lý sự cố"], size=11)
    usecase(1285, 745, 75, 25, ["Yêu cầu bổ sung", "thông tin"], size=11)
    usecase(1180, 815, 85, 25, ["Giải quyết &", "đóng hồ sơ"], size=11)

    # Audit log (Included)
    usecase(1180, 910, 110, 32, ["Ghi nhận nhật ký", "kiểm toán (Audit Log)"], fill="#edf5ee", stroke="#7eaa89", style="italic")

    # --------------------------------------------------------------------------
    # Associations: Guest
    # --------------------------------------------------------------------------
    line_assoc([(135, 205), (245, 215)])  # to UC_ARTICLES
    line_assoc([(135, 195), (220, 180), (470, 180), (495, 205)])  # to UC_REGISTER
    line_assoc([(130, 185), (220, 160), (720, 160), (745, 205)])  # to UC_LOGIN

    # --------------------------------------------------------------------------
    # Associations: Customer
    # --------------------------------------------------------------------------
    # Customer to Login (via vertical channel x=160, then horizontal corridor y=265)
    line_assoc([(140, 520), (160, 265), (810, 265), (830, 245)])
    # Customer to Profile (via top outer margin y=125)
    line_assoc([(140, 510), (150, 125), (1075, 125), (1100, 185)])
    # Customer to Attachments
    line_assoc([(140, 535), (180, 385), (240, 370)])
    # Customer to Main Chat
    line_assoc([(140, 555), (220, 500), (470, 475)])
    # Customer to Track Status
    line_assoc([(140, 575), (180, 630), (240, 640)])
    # Customer to List Cases
    line_assoc([(140, 590), (180, 720), (240, 730)])
    # Customer to Reopen
    line_assoc([(140, 605), (180, 810), (240, 820)])
    # Customer to Feedback
    line_assoc([(135, 620), (180, 900), (240, 910)])

    # --------------------------------------------------------------------------
    # Associations: Staff
    # --------------------------------------------------------------------------
    # Staff to Login (via right channel x=1430, then corridor y=265)
    line_assoc([(1455, 420), (1430, 265), (870, 265), (850, 245)])
    # Staff to Queue
    line_assoc([(1455, 440), (1370, 380), (1290, 370)])
    # Staff to Detail
    line_assoc([(1455, 455), (1290, 455)])
    # Staff to Staff Action
    line_assoc([(1455, 475), (1375, 545), (1300, 560)])

    # --------------------------------------------------------------------------
    # Associations: Google Gemini (External System)
    # --------------------------------------------------------------------------
    # Gemini to UC_BRIEF and UC_RAG (via open corridor y=1000)
    line_assoc([(1455, 835), (1420, 835), (1420, 1000), (940, 1000), (940, 650), (920, 645)])
    line_assoc([(940, 650), (940, 555), (920, 550)])

    # --------------------------------------------------------------------------
    # Use Case Relationships: Include & Extend in Customer Package
    # --------------------------------------------------------------------------
    # Chat -> Triage (include)
    line_include_extend([(680, 435), (740, 400)], lx=715, ly=405, is_include=True)

    # Emergency -> Chat (extend)
    line_include_extend([(435, 465), (470, 465)], lx=452, ly=452, is_include=False, note="nguy cơ khẩn cấp")

    # Clarify -> Chat (extend)
    line_include_extend([(730, 465), (690, 465)], lx=710, ly=452, is_include=False, note="thiếu dữ kiện, ≤2 lượt")

    # RAG -> Chat (extend)
    line_include_extend([(740, 525), (675, 490)], lx=715, ly=495, is_include=False, note="hỏi FAQ cẩm nang")

    # Chat -> Create Case (include)
    line_include_extend([(580, 501), (580, 605)], lx=608, ly=555, is_include=True, note="khi đủ dữ kiện")

    # Create Case -> Synthesize Brief (include)
    line_include_extend([(690, 640), (730, 640)], lx=710, ly=628, is_include=True)

    # --------------------------------------------------------------------------
    # Use Case Relationships: Staff Package (Generalization & Include)
    # --------------------------------------------------------------------------
    # Sub-actions generalize to Staff Action
    line_generalize([(1075, 650), (1130, 600)])  # Approve
    line_generalize([(1285, 650), (1230, 600)])  # Edit Brief
    line_generalize([(1090, 720), (1145, 601)])  # Reroute
    line_generalize([(1270, 720), (1215, 601)])  # Request Info
    line_generalize([(1180, 790), (1180, 601)])  # Resolve & Close

    # Staff Action -> Audit Log (include) - routed around right margin of subactions
    line_include_extend([(1295, 580), (1370, 580), (1370, 910), (1290, 910)], lx=1345, ly=750, is_include=True)

    # --------------------------------------------------------------------------
    # Legend & Notes Box
    # --------------------------------------------------------------------------
    parts.append('<rect x="190" y="1105" width="1220" height="55" rx="6" fill="#f8fafc" stroke="#bcccdc" stroke-width="1"/>')

    # Legend items
    # Standard UC
    parts.append('<ellipse cx="240" cy="1132" rx="20" ry="10" fill="#edf1f5" stroke="#8e9fad" stroke-width="1.2"/>')
    text(270, 1136, "Ca sử dụng nghiệp vụ", size=11, color="#334e68")

    # AI / RAG UC
    parts.append('<ellipse cx="430" cy="1132" rx="20" ry="10" fill="#f0edf8" stroke="#9b8ec4" stroke-width="1.2"/>')
    text(460, 1136, "AI / RAG tự động", size=11, color="#334e68")

    # Safety UC
    parts.append('<ellipse cx="590" cy="1132" rx="20" ry="10" fill="#fbebeb" stroke="#c4787e" stroke-width="1.2"/>')
    text(620, 1136, "An toàn & Khẩn cấp", size=11, color="#334e68")

    # Storage UC
    parts.append('<ellipse cx="770" cy="1132" rx="20" ry="10" fill="#edf5ee" stroke="#7eaa89" stroke-width="1.2"/>')
    text(800, 1136, "Lưu trữ / Hồ sơ", size=11, color="#334e68")

    # Include line
    parts.append('<line x1="915" y1="1132" x2="945" y2="1132" stroke="#506273" stroke-width="1.2" stroke-dasharray="4 3" marker-end="url(#arrow)"/>')
    text(955, 1136, "«include» (bắt buộc)", size=11, color="#334e68")

    # Extend line
    parts.append('<line x1="1085" y1="1132" x2="1115" y2="1132" stroke="#506273" stroke-width="1.2" stroke-dasharray="4 3" marker-end="url(#arrow)"/>')
    text(1125, 1136, "«extend» (có điều kiện)", size=11, color="#334e68")

    # Generalization line
    parts.append('<line x1="1275" y1="1132" x2="1305" y2="1132" stroke="#506273" stroke-width="1.2" marker-end="url(#triangle)"/>')
    text(1315, 1136, "Kế thừa / chuyên biệt hóa", size=11, color="#334e68")

    parts.append('</svg>')

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Generated {OUT} ({len(parts)} tags)")


if __name__ == "__main__":
    build_svg()
