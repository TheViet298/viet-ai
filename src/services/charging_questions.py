"""Separate charging instructions, tariffs and app help before evidence filtering."""
import json
import re
from pathlib import Path

from src.agents.guardrails import strip_accents


def is_public_charging_procedure(query: str) -> bool:
    text = strip_accents(query.casefold())
    return ('tram sac' in text and any(word in text for word in ('huong dan', 'cach sac', 'cac buoc sac'))
            and not any(word in text for word in ('loi', 'khong sac', 'ket sung', 'bieu phi', 'phi sac', 'gia sac')))


def charging_parts(query: str) -> list[tuple[str, str, str]]:
    text = strip_accents(query.casefold())
    if not ('tram sac' in text and any(word in text for word in ('huong dan', 'cach sac'))
            and any(word in text for word in ('bieu phi', 'phi sac', 'gia sac'))
            and re.search(r'\bapp\b|ung dung', text)):
        return []
    if any(word in text for word in ('bao loi', 'khong sac', 'ket sung', 'su co')):
        return []
    return [
        ('Cách sạc tại trạm công cộng', 'Hướng dẫn cách sạc pin tại trạm sạc công cộng', 'guide'),
        ('Biểu phí sạc', 'Biểu phí sạc tại trạm sạc công cộng VinFast', 'policy'),
        ('Tính năng trên App VinFast', 'Tính năng sạc trên ứng dụng VinFast', 'guide'),
    ]


def reviewed_charging_guides(query: str) -> list[dict]:
    text = strip_accents(query.casefold())
    scope = 'public_charging' if is_public_charging_procedure(query) else (
        'charging_app' if 'tinh nang' in text and 'sac' in text and re.search(r'\bapp\b|ung dung', text) else None)
    if scope is None:
        return []
    path = Path(__file__).resolve().parents[2] / 'fixtures/knowledge/charging_guides.json'
    return [record for record in json.loads(path.read_text(encoding='utf-8')) if record['scope'] == scope]
