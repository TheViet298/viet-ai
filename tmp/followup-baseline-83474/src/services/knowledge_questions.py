"""Bounded decomposition of sales questions; every part uses verified evidence."""
import asyncio
import re
import time

from src.agents.guardrails import sanitize_pii, strip_accents
from src.agents.nodes.rag_node import rag_node
from src.config import get_settings
from src.services.conversation_context import ConversationContext


from src.services.vehicle_catalog import catalog_cards, catalog_citations, vehicle_overview_reply, vehicle_comparison_reply

# Compatibility metadata contains names/links only. Facts come from the scoped registry.
GENERAL_VEHICLE_ADVICE = ('VinFast có các dòng xe điện VF3, VF5, VF6, VF7, VF8 và VF9 để anh/chị tham khảo. '
    'Em có thể giới thiệu từng dòng xe, các phiên bản, giá niêm yết và hỗ trợ tìm hiểu việc lái thử. '
    'Anh/chị muốn được tư vấn cụ thể mẫu xe nào?')
GENERAL_VEHICLE_CHIPS = ['Tư vấn xe VF3', 'Tư vấn xe VF8']

MODEL_CATALOG = {c.model: {'full_name': 'VinFast ' + c.model, 'source': {'title': c.name, 'url': c.source_url}}
                 for c in catalog_cards()}


def format_vehicle_overview(model_key: str, user_vehicle: str | None = None) -> tuple[str, dict | None]:
    cards = catalog_cards([model_key])
    if not cards:
        return '', None
    return vehicle_overview_reply(cards), MODEL_CATALOG[model_key]['source']


def comparison_cards(models: list[str], text: str = '') -> list:
    from src.services.vehicle_catalog import requested_variants
    cards = []
    for model in models:
        available = catalog_cards([model])
        selected = requested_variants(strip_accents(text.casefold()), model, len(models) == 1)
        if selected:
            scoped = [c for v in selected for c in available if c.variant == v]
            if len(scoped) != len(selected):
                return []
            cards.extend(scoped)
        else:
            cards.extend(available[:1])
    return cards


def format_vehicle_comparison(models: list[str], text: str = '') -> str:
    cards = comparison_cards(models, text)
    if len(cards) > 2:
        return vehicle_overview_reply(cards)
    return vehicle_comparison_reply(cards) if len(cards) == 2 else ''


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
    cards = catalog_cards()
    labels = {'range': 'Quãng đường', 'power': 'Công suất tối đa', 'space': 'Số chỗ ngồi', 'charging': 'Thời gian sạc'}
    label = labels.get(aspect)
    heading = {'range': 'Quãng đường công bố theo phiên bản và chuẩn đo', 'charging': 'Thời gian sạc nhanh 10%–70% theo phiên bản', 'power': 'Công suất tối đa theo phiên bản', 'space': 'Số chỗ ngồi theo phiên bản', 'price': 'Giá niêm yết theo phiên bản'}.get(aspect, 'Thông tin các cấu hình đã đối chiếu nguồn')
    lines = [heading + '. Chưa đủ căn cứ xếp hạng toàn bộ thị trường.']
    for card in cards:
        value = card.price_label if aspect == 'price' else next((s.value for s in card.specs if s.label.startswith(label or '___')), 'Chưa có dữ liệu xác minh')
        lines.append(f'- **{card.name}**: {value}.')
    lines.append('Các chuẩn NEDC/WLTP và điều kiện sạc khác nhau không được so trực tiếp. Giá niêm yết chưa phải chi phí sở hữu hoặc giá lăn bánh.')
    return '\n\n'.join(lines), catalog_citations(cards), ['So sánh VF7 và VF8', 'Đăng ký lái thử']


def explicit_models(text: str) -> list[str]:
    return list(dict.fromkeys("VF" + m.upper() for m in re.findall(r"\bvf\s*(e34|[356789])\b", text, re.I)))


def sales_parts(text: str, model: str | None, *, turn_understanding: dict | None = None) -> list[tuple[str, str, str | None]]:
    if turn_understanding:
        goal = turn_understanding.get('goal')
        cost = turn_understanding.get('cost_subject')
        if goal in {'incident', 'complaint', 'out_of_scope', 'warranty', 'maintenance', 'application', 'charging_network', 'concept', 'appearance'} or cost not in {None, 'vehicle_purchase'}:
            return []
        if goal == 'overview':
            return [('Thông tin dòng xe', text, model)]
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
    from src.services.vehicle_catalog import is_generic_vehicle_comparison, select_vehicle_cards, vehicle_overview_reply
    from src.services.vehicle_card_intent import is_generic_vehicle_overview, is_general_vehicle_advice
    raw_text = (turn_understanding or {}).get('original_text') or text
    if is_general_vehicle_advice(raw_text):
        return {'reply': GENERAL_VEHICLE_ADVICE, 'citations': [], 'answer_claims': [],
                'suggested_replies': GENERAL_VEHICLE_CHIPS.copy(), 'response_type': 'FAQ_ANSWER',
                'is_no_source': False, 'answer_path': 'general_lineup'}
    overview_followup = ((turn_understanding or {}).get('goal') == 'overview'
                         and (turn_understanding or {}).get('move') == 'elaborate')
    if is_generic_vehicle_overview(raw_text) or overview_followup:
        from src.services.conversation_context import TurnUnderstanding
        understanding = TurnUnderstanding.model_validate({'original_text': raw_text, 'resolved_query': text,
                                                          **turn_understanding}) if turn_understanding else None
        cards = select_vehicle_cards(text if overview_followup else raw_text, understanding=understanding)
        if cards:
            reply = vehicle_overview_reply(cards)
            if user_vehicle and model and re.sub(r'\s+', '', user_vehicle).upper() != model.upper():
                reply += f'\n\nQuý khách có muốn so sánh {model} với xe {user_vehicle} đang sử dụng không?'
            return {'reply': reply, 'citations': catalog_citations(cards), 'answer_claims': [], 'suggested_replies': [],
                    'response_type': 'FAQ_ANSWER', 'is_no_source': False, 'answer_path': 'snapshot'}
    from src.services.conversation_context import normalized
    specific_aspect = bool(re.search(r'bao hanh|bao duong|sua chua|ung dung|adas|\babs\b|mau (?:gi|nao|sac)', normalized(text)))
    if len(models_found) >= 2 and not is_from_to and not specific_aspect:
        comp_text = format_vehicle_comparison(models_found, raw_text)
        if comp_text:
            citations = catalog_citations(comparison_cards(models_found, raw_text))
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

    parts = sales_parts(text, model, turn_understanding=turn_understanding)
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
    from src.services.agent_llm import new_turn_budget
    shared_budget = llm_budget if llm_budget is not None else new_turn_budget(time.monotonic() + get_settings().agent_turn_timeout_s)
    results = await asyncio.gather(*(rag_node({
        "latest_user_message": query, "vehicle_model": vehicle,
        "confidence_score": .9, "session_id": session_id, "turn": 0,
        'conversation_context': conversation_context or {}, 'turn_understanding': turn_understanding or {},
        "llm_budget": shared_budget,
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
                citations.extend(catalog_citations(catalog_cards([target_v])))
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
                reply = vehicle_overview_reply(catalog_cards())
                citations.extend(catalog_citations(catalog_cards()))
                suggested_chips = ['Tư vấn VF3', 'Tư vấn VF7', 'Đăng ký lái thử']
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

    # Shared product URLs contain multiple configurations. Deduplicate identical
    # evidence only; keep each variant's source scope and claim qualifiers.
    unique_citations = []
    seen_evidence = set()
    for citation in citations:
        key = (citation.get('source_id'), citation.get('url'), citation.get('relevant_snippet'))
        if citation.get('url') and key not in seen_evidence:
            seen_evidence.add(key)
            unique_citations.append(citation)

    return {"reply": "\n\n".join(sections), "citations": unique_citations,
            'answer_claims': claims,
            'suggested_replies': suggested_chips,
            'retrieval_diagnostics': {'parts': [{
                'label': part[0], 'diagnostics': result.get('retrieval_diagnostics', {})}
                for part, result in zip(parts, results, strict=True)]},
            "is_no_source": not unique_citations and all(r["is_no_source"] for r in results), "response_type": "FAQ_ANSWER"}
