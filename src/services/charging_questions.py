"""Separate charging instructions, tariffs and app help before evidence filtering."""
import json
import re
from pathlib import Path

from src.agents.guardrails import strip_accents


def is_public_charging_procedure(query: str) -> bool:
    text = strip_accents(query.casefold())
    return (re.search(r'tram (?:sac|cong cong)', text) and any(word in text for word in ('huong dan', 'cach sac', 'cac buoc sac', 'cac buoc', 'thao tac sac'))
            and not re.search(r'bao loi|loi sac|khong sac|ket sung|bieu phi|phi sac|gia sac', text))


def charging_parts(query: str) -> list[tuple[str, str, str]]:
    from src.services.faq_questions import CHARGING_TOPICS, faq_parts
    return faq_parts(query, CHARGING_TOPICS)


def reviewed_charging_guides(query: str) -> list[dict]:
    from src.services.faq_questions import generic_help_query
    text = strip_accents(query.casefold())
    scope = 'public_charging' if is_public_charging_procedure(query) else (
        'charging_app' if ('tinh nang' in text or 'lich su sac' in text) and re.search(r'\bapp\b|ung dung', text) else None)
    if scope is None:
        return []
    vocabulary = ('huong dan cach sac pin tai tram cong cong o to dien vinfast cho toi vui long xin hay cac buoc '
                  'su dung can muon hoi ve tinh nang tren ung dung app cua co gi nao nhung thong tin chung '
                  'moi dung xe cac buoc thao tac o to xem trong lich su sac cho biet giup minh '
                  'mot nay bat dau voi dieu nay nhung chi tiet duoc la the nao '
                  'i am new to this walk me through charging a car at public station '
                  'which details can view in history the vinfast app application how do')
    if not generic_help_query(query, vocabulary):
        return []
    path = Path(__file__).resolve().parents[2] / 'fixtures/knowledge/charging_guides.json'
    return [record for record in json.loads(path.read_text(encoding='utf-8')) if record['scope'] == scope]
