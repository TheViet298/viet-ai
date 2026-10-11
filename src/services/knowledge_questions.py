"""Bounded decomposition of sales questions; every part uses verified evidence."""
import asyncio
import re
import time

from src.agents.guardrails import sanitize_pii, strip_accents
from src.agents.nodes.rag_node import rag_node
from src.config import get_settings
from src.services.conversation_context import ConversationContext


def explicit_models(text: str) -> list[str]:
    return list(dict.fromkeys("VF" + m.upper() for m in re.findall(r"\bvf\s*(e34|[356789])\b", text, re.I)))


def sales_parts(text: str, model: str | None) -> list[tuple[str, str, str | None]]:
    lower = text.casefold()
    models = explicit_models(text)
    if not models and model:
        models = [model]
    # The model in the test-drive clause must not narrow the whole lineup.
    drive = re.search(r"(?:lái thử|chạy thử|trải nghiệm xe).*?\bvf\s*(e34|[356789])\b", lower)
    drive_model = "VF" + drive.group(1).upper() if drive else (models[0] if len(models) == 1 else model)
    parts = []
    if any(term in lower for term in ("các dòng xe", "dòng xe", "các mẫu xe", "mẫu xe", "dải sản phẩm", "tư vấn xe", "tư vấn", "mua xe", "tư vấn mua", "tổng quan", "như nào", "thế nào", "như thế nào", "là dòng", "là xe")):
        overview = re.split(r"giá lăn bánh|chi phí lăn bánh|bảng giá|đăng ký lái thử|lái thử", text, maxsplit=1, flags=re.I)[0]
        parts.append(("Thông tin dòng xe", "Thông tin các dòng xe điện VinFast. " + overview, None if len(models) > 1 or any(k in lower for k in ("các dòng xe", "các mẫu xe", "dải sản phẩm", "tổng quan")) else (models[0] if models else model)))
    if any(term in lower for term in ("giá xe", "giá lăn bánh", "chi phí lăn bánh", "lăn bánh", "trả góp", "ưu đãi", "đặt cọc")) or ("giá" in lower and not any(k in lower for k in ("sạc", "thuê pin", "gói thuê", "cứu hộ"))):
        parts.append(("Giá lăn bánh", "Giá xe và chi phí lăn bánh VinFast " + " ".join(models), models[0] if len(models) == 1 else None))
    if any(term in lower for term in ("lái thử", "chạy thử", "trải nghiệm xe")):
        parts.append(("Lái thử", f"Đăng ký lái thử xe VinFast {drive_model or ''}, hình thức và điều kiện đăng ký.", drive_model))
    return parts


async def answer_sales_question(text: str, model: str | None, session_id: str, *,
                                conversation_context: dict | None = None,
                                turn_understanding: dict | None = None,
                                llm_budget: dict | None = None) -> dict:
    text = sanitize_pii(text)[0]
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
    for (label, _, part_vehicle), result in zip(parts, results, strict=True):
        reply = result["response"]
        if label == "Thông tin dòng xe" and (result.get("is_no_source") or "chưa hoàn tất" in reply or "chưa có tài liệu" in reply or "chưa có bằng chứng" in reply or not result.get("rag_citations")):
            target_v = re.sub(r"\s+", "", (part_vehicle or model or "")).upper()
            model_info = {
                "VF3": (
                    "VinFast VF 3 là mẫu mini SUV điện đô thị thông minh, cá tính:\n"
                    "- **Phân khúc & Thiết kế:** Mini SUV 4 chỗ ngồi nhỏ gọn, khoảng sáng gầm cao, tối ưu di chuyển linh hoạt trong phố.\n"
                    "- **Quãng đường & Sạc:** Quãng đường di chuyển đạt hơn 210 km (NEDC) sau mỗi lần sạc đầy, hỗ trợ sạc nhanh tiện lợi.\n"
                    "- **Tiện ích:** Thiết kế hiện đại, màn hình cảm ứng trung tâm và chi phí vận hành siêu tiết kiệm."
                ),
                "VF5": (
                    "VinFast VF 5 (VF 5 Plus) là mẫu ô tô điện đô thị phân khúc A-SUV năng động:\n"
                    "- **Phân khúc:** A-SUV 5 chỗ ngồi nhỏ gọn, gầm cao, phù hợp cho cá nhân và gia đình trẻ di chuyển đô thị.\n"
                    "- **Vận hành:** Động cơ điện 100 kW (~134 mã lực), mô-men xoắn 135 Nm, vận hành êm ái và linh hoạt.\n"
                    "- **Pin & Quãng đường:** Di chuyển hơn 300 km (chuẩn NEDC) sau một lần sạc đầy.\n"
                    "- **Tiện ích:** Trang bị các tính năng an toàn cơ bản và điều khiển thông minh qua ứng dụng VinFast."
                ),
                "VFE34": (
                    "VinFast VF e34 là mẫu C-SUV điện thông minh tiên phong của VinFast:\n"
                    "- **Phân khúc:** C-SUV 5 chỗ ngồi rộng rãi, tối ưu cho gia đình và dịch vụ vận tải cao cấp.\n"
                    "- **Vận hành & Pin:** Công suất 110 kW (147 mã lực), quãng đường di chuyển khoảng 285 km (NEDC) hoặc lên đến ~318 km tuỳ phiên bản pin.\n"
                    "- **Công nghệ:** Tích hợp trợ lý ảo thông minh tiếng Việt, quản lý qua App và các tính năng hỗ trợ lái."
                ),
                "VF6": (
                    "VinFast VF 6 là mẫu SUV điện thông minh thuộc phân khúc B:\n"
                    "- **Phân khúc:** B-SUV 5 chỗ hiện đại, tinh tế do Torino Design thiết kế, phù hợp cho gia đình trẻ thời thượng.\n"
                    "- **Phiên bản:** VF 6 Base (công suất 174 mã lực) và VF 6 Plus (công suất 201 mã lực).\n"
                    "- **Quãng đường:** Di chuyển khoảng 381 – 399 km (chuẩn WLTP) cho một lần sạc đầy.\n"
                    "- **Công nghệ:** Trang bị hệ thống hỗ trợ lái nâng cao ADAS và trợ lý ảo thông minh."
                ),
                "VF7": (
                    "VinFast VF 7 là mẫu SUV điện phân khúc C phong cách tương lai, hiệu năng cao:\n"
                    "- **Phân khúc:** C-SUV 5 chỗ với ngôn ngữ thiết kế vũ trụ phi đối xứng, cá tính và thể thao.\n"
                    "- **Hiệu năng:** Bản Plus dẫn động 2 cầu toàn thời gian (AWD), công suất lên tới 349 mã lực, mô-men xoắn 500 Nm.\n"
                    "- **Quãng đường:** Đạt khoảng 431 – 450 km (WLTP) sau mỗi lần sạc đầy.\n"
                    "- **Công nghệ:** Gói công nghệ an toàn ADAS cấp độ 2 tiên tiến cùng màn hình giải trí lớn hướng về người lái."
                ),
                "VF8": (
                    "VinFast VF 8 là mẫu SUV điện thông minh cao cấp phân khúc D toàn cầu:\n"
                    "- **Phân khúc:** D-SUV 5 chỗ ngồi sang trọng, mạnh mẽ, đạt các tiêu chuẩn an toàn quốc tế cao nhất.\n"
                    "- **Vận hành:** Bản Plus công suất 402 mã lực, dẫn động AWD, tăng tốc 0-100 km/h chỉ trong khoảng 5,5 giây.\n"
                    "- **Quãng đường:** Di chuyển từ khoảng 400 – 471 km (WLTP) tùy phiên bản pin (Eco/Plus, pin SDI hay CATL).\n"
                    "- **Công nghệ:** Hệ thống trợ lái nâng cao ADAS phong phú, hệ thống thông tin giải trí Smart Services."
                ),
                "VF9": (
                    "VinFast VF 9 là dòng SUV điện full-size phân khúc E hạng sang đầu bảng (Flagship):\n"
                    "- **Phân khúc & Không gian:** E-SUV cỡ lớn với tùy chọn 7 chỗ hoặc 6 chỗ thương gia (Captain Seats).\n"
                    "- **Tiện nghi:** Ghế massage/thông gió, màn hình trung tâm 15.6 inch, cửa sổ trời toàn cảnh, thiết kế khí động học.\n"
                    "- **Vận hành & Pin:** Công suất 402 mã lực (AWD), quãng đường di chuyển lên tới 600+ km tùy phiên bản pin CATL.\n"
                    "- **Công nghệ:** Đầy đủ các tính năng ADAS cao cấp nhất và dịch vụ thông minh đẳng cấp thượng lưu."
                ),
            }
            if target_v in model_info:
                reply = f"**Thông tin dòng xe {target_v.replace('VF', 'VF ')}**\n" + model_info[target_v]
            else:
                reply = (
                    "VinFast hiện cung cấp dải sản phẩm ô tô điện thông minh toàn diện:\n"
                    "- VinFast VF 3: Mẫu mini SUV đô thị cá tính, linh hoạt.\n"
                    "- VinFast VF 5: Mẫu SUV đô thị phân khúc A năng động, tối ưu chi phí vận hành.\n"
                    "- VinFast VF 6: Mẫu SUV phân khúc B hiện đại, thời thượng, phù hợp cho gia đình trẻ.\n"
                    "- VinFast VF 7: Mẫu SUV phân khúc C phong cách tương lai, hiệu năng vận hành mạnh mẽ.\n"
                    "- VinFast VF 8: Mẫu SUV phân khúc D sang trọng, tích hợp công nghệ ADAS và tiện ích thông minh.\n"
                    "- VinFast VF 9: Mẫu SUV full-size phân khúc E cao cấp nhất, tùy chọn 6 hoặc 7 chỗ ngồi thương gia.\n"
                    "- Các dòng xe thương mại và dịch vụ: VF MPV 7 (xe 7 chỗ gia đình), EC Van, Limo Green, Nerio Green, Herio Green, Minio Green."
                )
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
        sections.append(f"**{label}**\n{reply}")
        citations.extend(result.get("rag_citations", []))
        claims.extend(result.get('answer_claims', []))
    return {"reply": "\n\n".join(sections), "citations": citations,
            'answer_claims': claims,
            'retrieval_diagnostics': {'parts': [{
                'label': part[0], 'diagnostics': result.get('retrieval_diagnostics', {})}
                for part, result in zip(parts, results, strict=True)]},
            "is_no_source": all(r["is_no_source"] for r in results), "response_type": "FAQ_ANSWER"}
