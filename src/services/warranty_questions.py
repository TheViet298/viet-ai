"""Keep battery warranty separate from model-specific maintenance schedules."""
import json
import re
from pathlib import Path

from src.agents.guardrails import strip_accents


def warranty_maintenance_parts(query: str) -> list[tuple[str, str, str]]:
    from src.services.faq_questions import WARRANTY_TOPICS, faq_parts
    return faq_parts(query, WARRANTY_TOPICS)


def is_general_maintenance_query(query: str) -> bool:
    text = strip_accents(query.casefold())
    return ('bao duong' in text and not re.search(r'\bvf\s*(?:e34|[356789])\b|\d', text)
            and not any(term in text for term in ('bao lau', 'khi nao', 'lan dau', 'dat lich', 'chi phi', 'gia', 'mien phi', 'dich vu', 'thuong mai')))


def reviewed_warranty_overviews(query: str, vehicle_model: str | None = None) -> list[dict]:
    from src.services.faq_questions import generic_help_query
    text = strip_accents(query.casefold())
    if (vehicle_model or re.search(r'\bvf\s*(?:e34|[356789])\b|\d', text)
            or any(term in text for term in ('bao lau', 'may nam', 'bao nhieu', 'khi nao', 'dich vu', 'thuong mai', 'thue pin', 'mua pin', 'khieu nai', 'khong duoc bao hanh'))):
        return []
    if 'ac quy' in text and not re.search(r'khac|phan biet|tong quat|chung', text):
        return []
    if 'bao hanh' in text and 'pin' in text and 'bao duong' not in text:
        scope = 'battery_warranty'
    elif is_general_maintenance_query(query) and 'bao hanh' not in text:
        scope = 'maintenance_overview'
    else:
        return []
    vocabulary = ('chinh sach bao hanh pin cao ap vinfast toi muon hoi ve cac thong tin chung nguyen tac cua '
                  'cho xin vui long lich bao duong dinh ky theo dung mau xe '
                  'noi tong quat giup giai thich khac ac quy nhu the nao chua chot thoi han cu the '
                  'dua tren yeu to can doi chieu tai lieu gi nhung thong tin ve va '
                  'so voi mot cach ma khong chon khoang cho noi chung dieu xac dinh nen kiem tra quyet dinh viec gian '
                  'explain high voltage battery warranty versus auxiliary in general without choosing a vehicle specific duration '
                  'what determines scheduled maintenance and which documents should i check')
    if not generic_help_query(query, vocabulary):
        return []
    path = Path(__file__).resolve().parents[2] / 'fixtures/knowledge/warranty_maintenance.json'
    return [record for record in json.loads(path.read_text(encoding='utf-8')) if record['scope'] == scope]
