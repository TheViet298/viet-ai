"""Source-reviewed sections for gaps; never infer unknown trim/year coverage."""
import json
from pathlib import Path
import re
from src.services.answer_evidence import normalized, is_color_question

PATH = Path(__file__).resolve().parents[2] / 'fixtures/knowledge/answer_gap_sections.json'


def reviewed_gap_answers(query: str, model: str | None) -> list[dict]:
    body = normalized(query)
    models = {'VF' + m.upper() for m in re.findall(r'\bvf\s*(e34|[356789])\b', body)}
    if len(models) > 1 or models and models != {model}:
        return []
    years = re.findall(r'\b20\d{2}\b', body)
    # No contemporary public policy record proves a particular historic car.
    if years and not ('adas' in body and set(years) == {'2026'}):
        return []
    if re.search(r'noi bo|bi mat|thang sau|philippines|indonesia|united states|the all new|all-new', body):
        return []
    if re.search(r'khong.{0,15}(?:taxi|thuong mai|chay dich vu|cho thue|grab)', body):
        return []
    key = None
    if 'bao hanh' in body and re.search(r'ngap nuoc|lu lut', body):
        key = 'flood_exclusion'
    elif model in {'VF8','VF5'} and 'bao hanh' in body:
        if re.search(r'ac[ -]*quy|12\s*v', body) and model == 'VF8': key = 'auxiliary_warranty'
        elif 'pin' in body and model == 'VF8': key = 'high_voltage_warranty'
        elif re.search(r'thuong mai|chay dich vu|taxi|kinh doanh van tai|cho thue|grab|be car', body) and model == 'VF8': key = 'commercial_warranty'
        elif not re.search(r'pin|ac[ -]*quy|gi set|son|lop|phu tung|phu kien|treo|thuong mai|chay dich vu|taxi|kinh doanh van tai|cho thue|grab|be car', body): key = 'vehicle_warranty'
    elif model == 'VF8' and 'adas' in body and not re.search(r'bat|tat|kich hoat|cach|bao loi|loi |activate|enable|turn on|turn off|instructions|configure', body):
        key = 'adas_overview'
    elif model == 'VF7' and is_color_question(query) and not re.search(r'ton kho|con hang|hom nay|giao ngay|noi that', body):
        key = 'vf7_model_colors'
    elif model == 'VF3' and 'dung luong' in body and not re.search(r'\b(?:eco|plus|awd|fwd)\b|danh dinh|nominal', body):
        key = 'vf3_model_capacity'
    if not key:
        return []
    records = json.loads(PATH.read_text(encoding='utf-8'))
    return [{**r,'applicable_models': [model] if model else ['ALL']} for r in records
        if r['key'] == key and r['model'] == (None if key == 'flood_exclusion' else model)
        and r.get('review_status') == 'verified' and r.get('reviewer') and r.get('reviewed_at')]


def foreign_market_request(query: str) -> bool:
    body = normalized(query)
    return bool(re.search(
        r'philippines|indonesia|united states|canada|chau au|hoa ky|han quoc|thai lan|uc chau|australia|europe|germany|france'
        r'|\b(?:tai|o|in|market|thi truong)\s+(?:the\s+)?(?:us|usa|uk|eu|uc|duc|phap|anh)\b'
        r'|\b(?:tai|o|thi truong)\s+my\b', body))
