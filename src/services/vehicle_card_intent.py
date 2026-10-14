"""Decide product-card presentation separately from the response's FAQ route.

Names and broad verbs alone do not authorize a sales card for service questions.
Unknown requests conservatively retain the normal text response.
"""
import re
from typing import Literal

from src.agents.guardrails import strip_accents

CardIntent = Literal['overview', 'price', 'specifications', 'comparison', 'test_drive']
_MODEL = r'(?:vinfast\s+)?vf\s*[356789]'
_VARIANT = r'(?:\s+(?:(?:phien ban|ban)\s+)?(?:eco|plus))?'
_SERVICE = re.compile(
    r'bao hanh|bao duong|sua chua|thay pin|thay lop|phu tung|cuu ho|'
    r'ap suat lop|adas|\b(?:abs|bms|soc|soh|tpms)\b|ung dung|\bapp\b|tai khoan|ho so|'
    r'huong dan|cach (?:sac|dung|su dung|lai)|(?:gia|chi phi|phi|tien)\s+(?:sac|thay|sua|bao duong|thue pin)|'
    r'\b(?:sac|thay pin)\b.{0,30}(?:gia|chi phi|phi|tien)|tram sac|tru sac|'
    r'canh bao|loi|khieu nai|phan anh|hoan tien|an toan'
)


def affirmative_vehicle_request(text: str) -> str:
    lower = strip_accents(text.casefold()).replace('đ', 'd')
    if re.search(r'(?:dung|khong|bo)\s+(?:hien|hien thi|them|tao|gui)\s+(?:card|the)', lower):
        return ''
    clauses = re.split(r'[,.;!?]+|\b(?:nhung|ma|chi hoi)\b', lower)
    denied = re.compile(r'(?:khong\s+(?:(?:muon|can|co nhu cau)\s+)?|dung\s+)'
                        r'(?:tu van|mua|chon|lay|thich|gioi thieu|so sanh|dang ky|lai thu|thong so|gia|'
                        r'(?:hoi|xem)(?: ve)?\s+(?:gia|thong so|xe))')
    return ' '.join(clause for clause in clauses if not denied.search(clause)).strip()


def classify_vehicle_card_intent(text: str, *, active_goal: str | None = None,
                                 context_topic: str = '') -> CardIntent | None:
    lower = affirmative_vehicle_request(text)
    if not lower:
        return None
    bare = bool(re.fullmatch(_MODEL + _VARIANT, lower))
    if bare:
        topic = strip_accents(context_topic.casefold()).replace('đ', 'd')
        if active_goal not in {None, 'quote', 'test_drive', 'range', 'capacity'} or _SERVICE.search(topic):
            return None
        return 'overview'

    purchase = bool(re.search(r'(?:^|\b(?:muon|nen|dinh|du dinh|can)\s+|\btu van\s+)(?:mua|chon)\s+(?:xe\b|' + _MODEL + r')', lower))
    overview = bool(re.search(r'tu van\s+(?:xe|mau xe)\b|gioi thieu\s+(?:xe|' + _MODEL + r')|\b(?:cac dong xe|cac mau xe|dai san pham|tong quan)\b', lower))
    vehicle_price = bool(re.search(r'\bgia\s+(?:ban\s+(?:cua\s+)?|niem yet\s+(?:cua\s+)?|xe\s+)?' + _MODEL +
                                   r'|^(?:xe\s+)?' + _MODEL + _VARIANT + r'\s+(?:gia|bao nhieu tien)|gia (?:ban xe|lan banh)|chi phi lan banh', lower))
    # A complaint/technical question cannot be promoted by a nearby price or advice token.
    if re.search(r'khieu nai|phan anh|hoan tien', lower):
        return None
    if _SERVICE.search(lower) and not purchase:
        return None
    if vehicle_price:
        return 'price'
    if purchase or overview:
        return 'overview'
    if re.search(r'lai thu|chay thu|trai nghiem xe', lower):
        return 'test_drive'
    if re.search(r'so sanh', lower):
        return 'comparison'
    if re.search(r'thong so|quang duong|di duoc|bao nhieu km|dung luong pin|\bkwh\b|cong suat|thoi gian sac|sac nhanh', lower):
        return 'specifications'
    return None
