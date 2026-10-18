"""Keep battery warranty separate from model-specific maintenance schedules."""
import json
import re
from pathlib import Path

from src.agents.guardrails import strip_accents


def warranty_maintenance_parts(query: str) -> list[tuple[str, str, str]]:
    text = strip_accents(query.casefold())
    if not all(term in text for term in ('bao hanh', 'pin', 'bao duong')):
        return []
    if any(term in text for term in ('khieu nai', 'bao loi', 'hu hong', 'su co', 'khong duoc bao hanh')):
        return []
    # Both requests must retain the same vehicle and usage conditions.
    details = re.findall(
        r'\bVF\s*(?:e34|[356789])\b|\b20\d{2}\b|\b\d[\d.,]*\s*(?:km|tháng|năm)\b|'
        r'\b(?:(?:không|chưa|đã từng|đang)\s+)*(?:chạy dịch vụ|dịch vụ thương mại|sử dụng tiêu chuẩn|cá nhân|thuê pin|mua pin)\b',
        query, re.I)
    suffix = (' — ' + ', '.join(details)) if details else ''
    return [('Bảo hành pin', 'Chính sách bảo hành pin VinFast' + suffix, 'policy'),
            ('Bảo dưỡng định kỳ', 'Lịch bảo dưỡng định kỳ VinFast' + suffix, 'manual')]


def is_general_maintenance_query(query: str) -> bool:
    text = strip_accents(query.casefold())
    return ('bao duong' in text and not re.search(r'\bvf\s*(?:e34|[356789])\b|\d', text)
            and not any(term in text for term in ('bao lau', 'khi nao', 'lan dau', 'dat lich', 'chi phi', 'gia', 'mien phi', 'dich vu', 'thuong mai')))


def reviewed_warranty_overviews(query: str, vehicle_model: str | None = None) -> list[dict]:
    text = strip_accents(query.casefold())
    if (vehicle_model or re.search(r'\bvf\s*(?:e34|[356789])\b|\d', text)
            or any(term in text for term in ('bao lau', 'may nam', 'bao nhieu', 'khi nao', 'dich vu', 'thuong mai', 'thue pin', 'mua pin', 'ac quy', 'khieu nai', 'khong duoc bao hanh'))):
        return []
    if 'bao hanh' in text and 'pin' in text and 'bao duong' not in text:
        scope = 'battery_warranty'
    elif is_general_maintenance_query(query) and 'bao hanh' not in text:
        scope = 'maintenance_overview'
    else:
        return []
    path = Path(__file__).resolve().parents[2] / 'fixtures/knowledge/warranty_maintenance.json'
    return [record for record in json.loads(path.read_text(encoding='utf-8')) if record['scope'] == scope]
