"""Reviewed public product snapshots, independent of model-generated answers.

Source pages were reviewed on 2026-10-12. Refresh these values when VinFast
changes a configuration; listed prices are not rolling costs or promotions.
"""
import re

from src.agents.guardrails import strip_accents
from src.models.schemas import VehicleCard
from src.services.chat_classification import classify_chat_context
from src.services.vehicle_card_intent import classify_vehicle_card_intent, affirmative_vehicle_request


_PRODUCTS = [
    ('VF3', 'VF 3 Eco', 'vf3/xe-dien-vinfast-vf3-chon-mau-nen-trang-logo-desktop.webp',
     'dat-coc-xe-dien-vf3', '4 chỗ', '215 km (NEDC)', 'Sạc nhanh 10–70%', '36 phút', '285.000.000 VNĐ'),
    ('VF5', 'VF 5', 'vf5/xe-dien-vinfast-vf5-ngoai-that-mau-xam-toan-canh-desktop.webp',
     'dat-coc-xe-dien-vf5', '5 chỗ', '326 km (NEDC)', 'Công suất tối đa', '100 kW', '496.000.000 VNĐ'),
    ('VF6', 'VF 6 Eco', 'vf6/hinh-anh-xe-vinfast-vf6-logo-vf6-mau-do-desktop.webp',
     'dat-coc-xe-dien-vf6', '5 chỗ', '485 km (NEDC)', 'Sạc nhanh 10–70%', '25 phút', '646.000.000 VNĐ'),
    ('VF7', 'VF 7 Eco', 'vf7/hinh-anh-vinfast-vf7-text-logo-banner-desktop.webp',
     'dat-coc-xe-dien-vf7', '5 chỗ', '440 km (NEDC)', 'Công suất tối đa', '130 kW', '740.000.000 VNĐ'),
    ('VF8', 'VF 8 Eco', 'vf8/hinh-anh-vinfast-vf8-eco-text-logo-banner-desktop.webp',
     'dat-coc-xe-vf8', '5 chỗ', '635 km (NEDC)', 'Công suất tối đa', '150 kW', '898.000.000 VNĐ'),
    ('VF9', 'VF 9 Eco', 'vf9/hinh-anh-vinfast-vf9-eco-text-logo-banner-desktop.webp',
     'dat-coc-xe-vf9', '7 chỗ', '626 km (WLTP)', 'Sạc nhanh 10–70%', '35 phút', '1.348.000.000 VNĐ'),
]


def select_vehicle_cards(text: str, *, active_goal: str | None = None, context_topic: str = "") -> list[VehicleCard]:
    classification = classify_chat_context(text)
    if active_goal == 'incident' or classification.request_kind in {'incident', 'complaint', 'oos'} or classification.is_critical:
        return []
    lower = affirmative_vehicle_request(text)
    models = list(dict.fromkeys('VF' + n for n in re.findall(r'\bvf\s*([356789])\b', lower)))
    card_intent = classify_vehicle_card_intent(text, active_goal=active_goal, context_topic=context_topic)
    if not card_intent:
        return []
    if not models and any(term in lower for term in ('cac dong xe', 'cac mau xe', 'tu van xe', 'tu van mua xe')):
        models = [p[0] for p in _PRODUCTS]
    cards = []
    for model in models:
        if model == 'VF8':
            requested_variants = (re.findall(r'\b(eco|plus)\b', lower) if len(models) == 1 else
                                  re.findall(r'\bvf\s*8\s+(?:ban\s+)?(eco|plus)\b', lower))
            # An overview of one model shows its versions; cross-model comparisons
            # use the entry version unless a version was explicitly selected.
            variants = list(dict.fromkeys(requested_variants)) or (['eco', 'plus'] if len(models) == 1 else ['eco'])
            for variant in variants:
                plus = variant == 'plus'
                cards.append(VehicleCard(
                    model=model, variant=variant, name='VinFast VF 8 ' + variant.title(),
                    image_url='https://static-cms-prod.vinfastauto.com/statics/car/VF-8/' + (
                        'hinh-anh-xe-VinFast-vf8-ngoai-that-mau-xanh-reu-02.webp' if plus else
                        'hinh-anh-xe-VinFast-vf8-ngoai-that-mau-trang-01.webp'),
                    source_url='https://vinfastauto.com/vn_vi/dat-coc-xe-vf8',
                    specs_source_url='https://vinfastauto.com/vn_vi/cau-hoi-thuong-gap/cau-hoi-xe-o-to/san-pham/vf-8',
                    verified_at='2026-10-14', price_label='Từ ' + ('1.079.000.000 VNĐ' if plus else '898.000.000 VNĐ'),
                    battery_capacity='87,7 kWh', fast_charge_time='31 phút',
                    test_drive_url='https://shop.vinfastauto.com/vn_vi/dang-ky-lai-thu.html?modelId=VF8',
                    rolling_cost_url='https://shop.vinfastauto.com/vn_vi/chi-phi-lan-banh',
                    specs=[{'label': 'Số chỗ ngồi', 'value': '5 chỗ'},
                           {'label': 'Quãng đường', 'value': '475 km (NEDC)' if plus else '635 km (NEDC)'},
                           {'label': 'Thời gian sạc', 'value': '31 phút (từ 10%–70%)'},
                           {'label': 'Công suất tối đa', 'value': '300 kW' if plus else '150 kW'}],
                ))
            continue
        product = next(p for p in _PRODUCTS if p[0] == model)
        _, name, image, page, seats, distance, metric, value, price = product
        cards.append(VehicleCard(
            model=model, name='VinFast ' + name,
            image_url='https://static-cms-prod.vinfastauto.com/statics/car/' + image,
            source_url='https://vinfastauto.com/vn_vi/' + page,
            verified_at='2026-10-12', price_label='Từ ' + price,
            battery_capacity='59,6 kWh' if model == 'VF6' else None,
            fast_charge_time=value if metric == 'Sạc nhanh 10–70%' else None,
            test_drive_url='https://shop.vinfastauto.com/vn_vi/dang-ky-lai-thu.html',
            specs=[{'label': 'Số chỗ ngồi', 'value': seats},
                   {'label': 'Quãng đường/lần sạc', 'value': distance},
                   {'label': metric, 'value': value}],
        ))
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
    return ('Anh/chị xem thông tin công bố của ' + ', '.join(card.name for card in cards)
            + ' trong các thẻ dưới đây. Thông số áp dụng cho phiên bản ghi trên thẻ; giá lăn bánh và ưu đãi cần showroom xác nhận.')


def vehicle_comparison_reply(cards: list[VehicleCard]) -> str:
    names = [card.name.replace('VinFast ', '') for card in cards]
    rows = [('Giá bán từ', [card.price_label.removeprefix('Từ ') for card in cards]),
            ('Quãng đường mỗi lần sạc', [next((s.value for s in card.specs if s.label.startswith('Quãng đường')), 'Chưa có dữ liệu') for card in cards]),
            ('Dung lượng pin khả dụng', [card.battery_capacity or 'Chưa có dữ liệu' for card in cards]),
            ('Thời gian sạc nhanh (10%–70%)', [card.fast_charge_time or 'Chưa có dữ liệu' for card in cards]),
            ('Số chỗ ngồi', [next((s.value for s in card.specs if s.label == 'Số chỗ ngồi'), 'Chưa có dữ liệu') for card in cards])]
    lines = [f'Dạ, em gửi anh/chị thông tin so sánh giữa {names[0]} và {names[1]}:']
    lines.extend(f'- **{label}**: {names[0]} {values[0]}; {names[1]} {values[1]}.' for label, values in rows)
    lines.append('Quãng đường thực tế phụ thuộc điều kiện sử dụng. Các chuẩn NEDC/WLTP khác nhau không nên so trực tiếp; giá lăn bánh và ưu đãi cần showroom xác nhận.')
    return '\n\n'.join(lines)


def is_generic_vehicle_comparison(text: str) -> bool:
    vehicle = r'(?:vinfast\s+)?vf\s*[356789](?:\s+(?:(?:phien ban|ban)\s+)?(?:eco|plus))?'
    return bool(re.fullmatch(r'\s*so sanh\s+' + vehicle + r'\s+(?:va|voi|vs)\s+(?:' + vehicle + r'|eco|plus)[.!?]?\s*', strip_accents(text.casefold())))
