"""Reviewed public product snapshots, independent of model-generated answers.

Fact review dates and price conditions are recorded per configuration in the
canonical registry; listed prices are not rolling costs or promotions.
"""
import re

from src.agents.guardrails import strip_accents
from src.models.schemas import VehicleCard
from src.services.chat_classification import classify_chat_context
from src.services.vehicle_card_intent import classify_vehicle_card_intent, affirmative_vehicle_request


from datetime import date
import json
from pathlib import Path

FACT_PATH = Path(__file__).resolve().parents[2] / 'data/verified/vehicle_facts.json'


def catalog_facts() -> list[dict]:
    return json.loads(FACT_PATH.read_text(encoding='utf-8'))['facts']


def catalog_cards(models: list[str] | None = None) -> list[VehicleCard]:
    cards = []
    for fact in catalog_facts():
        if models is not None and fact['scope']['model'] not in models:
            continue
        card = dict(fact['card'])
        # The same freshness gate applies to displayed prices and quote evidence.
        price = fact['price']
        age = (date.today() - date.fromisoformat(price['reviewed_at'])).days
        amount = price['price_vnd']
        card['price_label'] = ('Từ ' + f'{amount:,}'.replace(',', '.') + ' VNĐ'
                               if amount is not None and 0 <= age <= 7 else 'Chưa có giá xác thực')
        cards.append(VehicleCard.model_validate(card))
    return cards


def catalog_citations(cards: list[VehicleCard]) -> list[dict]:
    result = []
    for card in cards:
        fact = next(f for f in catalog_facts() if f['scope']['model'] == card.model and f['scope']['variant'] == card.variant)
        text = card.name + ': ' + card.price_label + '; ' + '; '.join(s.label + ': ' + s.value for s in card.specs)
        if card.battery_capacity:
            text += '; Dung lượng pin khả dụng: ' + card.battery_capacity
        result.append({'source_id': 'SRC-009', 'title': card.name + ' — thông số kỹ thuật',
                       'url': card.source_url, 'verified_at': fact['price']['reviewed_at'], 'status_code': 200,
                       'specs_reviewed_at': fact['specs_reviewed_at'],
                       'applicable_models': [card.model], 'source_type': 'official_catalog',
                       'fact_scope': fact['scope'], 'source_section': fact['specs_source_section'],
                       'price_evidence': fact['price'], 'claim_evidence': fact['claim_evidence'],
                       'relevant_snippet': text})
    return result


def public_price_snapshots() -> list[dict]:
    rows = []
    for fact in catalog_facts():
        scope, price = fact['scope'], fact['price']
        amount = price['price_vnd']
        version = (scope['variant'] or '').replace('-', ' ').title()
        label = f"{amount:,} VNĐ".replace(',', '.') if amount is not None else 'chưa có giá xác minh riêng'
        rows.append({**scope, **price, 'source_id': 'SRC-009', 'source_type': 'official_catalog',
                     'version': version, 'url': price['source_url'], 'status_code': 200,
                     'verified_at': price['reviewed_at'], 'fact_scope': scope,
                     'relevant_snippet': f"{scope['model']} {version}: giá niêm yết {label}. " + price['conditions']})
    return rows


def requested_variants(text: str, model: str, single_model: bool) -> list[str]:
    version = r'((?:eco|plus)(?:\s+(?:awd|fwd))?|awd)\b'
    pattern = r'\b' + version if single_model else r'\bvf\s*' + model[2:] + r'\s+(?:(?:phien ban|ban)\s+)?' + version
    aliases = {'plus awd': 'plus'} if model in {'VF8', 'VF9'} else {}
    if model == 'VF9':
        aliases['eco awd'] = 'eco'
    if model == 'VF8':
        aliases['eco fwd'] = 'eco'
    if model in {'VF6', 'VF7'}:
        aliases.update({'eco fwd': 'eco', 'plus fwd': 'plus'})
    if model == 'VF7':
        aliases['awd'] = 'plus-awd'
    return list(dict.fromkeys(aliases.get(v, v.replace(' ', '-')) for v in re.findall(pattern, text)))


def select_vehicle_cards(text: str, *, active_goal: str | None = None, context_topic: str = "", understanding=None) -> list[VehicleCard]:
    classification = classify_chat_context(text)
    if active_goal == 'incident' or classification.request_kind in {'incident', 'complaint', 'oos'} or classification.is_critical:
        return []
    lower = affirmative_vehicle_request(text)
    models = list(dict.fromkeys('VF' + n for n in re.findall(r'\bvf\s*([356789])\b', lower)))
    card_intent = classify_vehicle_card_intent(text, active_goal=active_goal, context_topic=context_topic, understanding=understanding)
    if not card_intent:
        return []
    cards = []
    for model in models:
        available = catalog_cards([model])
        selected = requested_variants(lower, model, len(models) == 1)
        if selected and any(v not in {c.variant for c in available} for v in selected):
            return []
        cards.extend([c for v in selected for c in available if c.variant == v] if selected else available if len(models) == 1 else available[:1])
    return cards


def vehicle_overview_reply(cards: list[VehicleCard]) -> str:
    if cards and all(card.model == 'VF8' for card in cards):
        intro = 'VF 8 là mẫu SUV điện phân khúc D với 5 chỗ ngồi. '
        intro += 'Hai phiên bản Eco và Plus có những điểm khác biệt sau:' if len(cards) == 2 else 'Thông tin phiên bản anh/chị đang quan tâm:'
        lines = [intro]
        for card in cards:
            specs = {spec.label: spec.value for spec in card.specs}
            drive = 'dẫn động AWD' if card.variant == 'plus' else 'dẫn động cầu trước'
            price = card.price_label.replace('Từ ', 'từ ', 1)
            lines.append(f'- **{card.name} ({price})**: công suất {specs["Công suất tối đa"]}, '
                         f'{drive}; quãng đường công bố {specs["Quãng đường"]}, sạc nhanh {specs["Thời gian sạc"]}.')
        lines.append('Quãng đường thực tế phụ thuộc điều kiện sử dụng. Giá bán trên là giá niêm yết chưa phải là giá lăn bánh.')
        return '\n\n'.join(lines)
    lines = ['Anh/chị xem thông tin công bố của ' + ', '.join(card.name for card in cards) + ' trong các thẻ trên.']
    for card in cards:
        details = '; '.join(spec.label.lower() + ': ' + spec.value for spec in card.specs)
        lines.append(f'- **{card.name}**: {card.price_label}; {details}.')
    lines.append('Quãng đường thực tế phụ thuộc điều kiện sử dụng. Giá bán trên là giá niêm yết chưa phải là giá lăn bánh.')
    return '\n\n'.join(lines)


def vehicle_comparison_reply(cards: list[VehicleCard]) -> str:
    names = [card.name.replace('VinFast ', '') for card in cards]
    rows = [('Giá bán từ', [card.price_label.removeprefix('Từ ') for card in cards]),
            ('Quãng đường mỗi lần sạc', [next((s.value for s in card.specs if s.label.startswith('Quãng đường')), 'Chưa có dữ liệu') for card in cards]),
            ('Dung lượng pin khả dụng', [card.battery_capacity or 'Chưa có dữ liệu' for card in cards]),
            ('Công suất tối đa', [next((s.value for s in card.specs if s.label == 'Công suất tối đa'), 'Chưa có dữ liệu') for card in cards]),
            ('Thời gian sạc nhanh (10%–70%)', [card.fast_charge_time or 'Chưa có dữ liệu' for card in cards]),
            ('Số chỗ ngồi', [next((s.value for s in card.specs if s.label == 'Số chỗ ngồi'), 'Chưa có dữ liệu') for card in cards])]
    lines = [f'Dạ, em gửi anh/chị thông tin so sánh giữa {names[0]} và {names[1]}:']
    lines.extend(f'- **{label}**: {names[0]} {values[0]}; {names[1]} {values[1]}.' for label, values in rows)
    lines.append('Quãng đường thực tế phụ thuộc điều kiện sử dụng. Các chuẩn NEDC/WLTP khác nhau không nên so trực tiếp; giá lăn bánh và ưu đãi cần showroom xác nhận.')
    return '\n\n'.join(lines)


def is_generic_vehicle_comparison(text: str) -> bool:
    version = r'(?:(?:eco|plus)(?:\s+(?:awd|fwd))?|awd)'
    vehicle = r'(?:vinfast\s+)?vf\s*[356789](?:\s+(?:(?:phien ban|ban)\s+)?' + version + r')?'
    return bool(re.fullmatch(r'\s*so sanh\s+' + vehicle + r'\s+(?:va|voi|vs)\s+(?:' + vehicle + r'|' + version + r')[.!?]?\s*', strip_accents(text.casefold())))


def format_catalog_color_reply(text: str, citations: list[dict]) -> str:
    """Separate reviewed swatch labels; never tokenize arbitrary color prose.

    Formatting changes only customer presentation. Original evidence and its
    model-level availability caveats remain untouched.
    """
    path = FACT_PATH.with_name('catalog_colors.json')
    records = json.loads(path.read_text(encoding='utf-8'))['records']
    for record in records:
        names = [item['name'] for item in record['swatches']]
        joined = ' '.join(names)
        # Require the complete flattened list from the same reviewed source.
        # A prefix of some unknown longer list is not sufficient evidence.
        source_list = ': ' + joined + '.'
        if any(c.get('source_id') == record['source_id']
               and c.get('url') == record['source_url']
               and c.get('catalog_scope') == 'model_colors'
               and source_list in c.get('relevant_snippet', '') for c in citations):
            text = text.replace(source_list, ': ' + '; '.join(names) + '.')
    return text
