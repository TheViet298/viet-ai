"""Small reviewed source sections with explicit, conservative applicability."""
import json
from pathlib import Path
import re

from src.services.answer_evidence import normalized

ROOT = Path(__file__).resolve().parents[2]
SCHEDULE_PATH = ROOT / 'fixtures/knowledge/maintenance_schedules.json'
COLOR_PATH = ROOT / 'data/verified/catalog_colors.json'


def _approved(record: dict) -> bool:
    return record.get('review_status') == 'verified' and bool(record.get('reviewer') and record.get('reviewed_at'))


def _model_only(query: str, model: str | None) -> bool:
    if not model:
        return False
    body = normalized(query)
    models = {match.upper().replace(' ', '') for match in re.findall(r'\bvf\s*(?:e34|[356789])\b', body)}
    return (not models or models == {model}) and not re.search(r'\b20\d{2}\b|\b(?:eco|plus|awd|fwd)\b', body)


def reviewed_maintenance_schedules(query: str, vehicle_model: str | None) -> list[dict]:
    body = normalized(query)
    if (not _model_only(query, vehicle_model) or 'bao duong' not in body
            or not re.search(r'lich|dinh ky|chu ky|lan dau|bao nhieu km|khi nao|bao lau', body)
            or re.search(r'lam mat|dau phanh|t-box|thay|dat lich|dat hen|chi phi|\bgia\b|thuong mai|dich vu|khac nghiet|ngap|khong', body)):
        return []
    records = json.loads(SCHEDULE_PATH.read_text(encoding='utf-8'))
    return [{**record, 'applicable_models': [record['model']]} for record in records
            if _approved(record) and record['model'] == vehicle_model
            and record.get('operation') == 'scheduled_maintenance' and record.get('model_year') is None]


def reviewed_model_colors(query: str, vehicle_model: str | None) -> list[dict]:
    from src.services.answer_evidence import is_color_question
    if (not _model_only(query, vehicle_model) or not is_color_question(query)
            or re.search(r'ton kho|con hang|hom nay|giao ngay|noi that|\bkhong\b', normalized(query))):
        return []
    rows = json.loads(COLOR_PATH.read_text(encoding='utf-8'))['records']
    return [{**record, 'url': record['source_url'], 'source_type': 'official_catalog',
             'applicable_models': [record['model']], 'catalog_scope': 'model_colors'}
            for record in rows if _approved(record) and record['model'] == vehicle_model]
