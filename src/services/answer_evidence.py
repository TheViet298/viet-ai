"""Select complete answer sections and reject descriptions posing as procedures."""
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field


class AnswerClaim(BaseModel):
    claim_key: str
    value: str
    unit: str
    subject: str
    conditions: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


QUANTITY = re.compile(r'(\d+(?:[.,]\d+)*(?:\s*[-–]\s*\d+(?:[.,]\d+)*)?)\s*((?:tỷ|triệu)\s*đồng|km|kwh|phút|năm|vnđ|vnd|đồng|%)(?!\w)', re.I)


def numeric_value(value: str) -> Decimal | tuple | None:
    value = value.strip()
    if re.search(r'[-–]', value):
        endpoints = tuple(numeric_value(v) for v in re.split(r'[-–]', value))
        return endpoints if len(endpoints) == 2 and all(isinstance(v, Decimal) for v in endpoints) else None
    if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+', value):
        value = value.replace('.', '').replace(',', '')
    else:
        value = value.replace(',', '.')
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def battery_condition(text: str) -> str | None:
    body = normalized(text)
    if re.search(r'khong (?:bao gom|kem|gom) pin|chua (?:bao gom|kem) pin', body):
        return 'pin_excluded'
    if re.search(r'mua (?:kem|dut) pin|bao gom pin|gia.*kem pin', body):
        return 'pin_included'
    if 'thue pin' in body:
        return 'battery_rental'
    return None


def validate_answer_claims(claims: list[AnswerClaim], citations: list[dict], prior_claims: list[AnswerClaim]) -> dict:
    unsupported, conflicts = [], []
    keywords = {'range': ('quang duong', 'mot lan sac', 'pham vi'),
                'warranty': ('bao hanh',), 'charging_time': ('sac',),
                'capacity': ('dung luong',), 'price': ('gia',)}
    for claim in claims:
        supported = False
        for citation in citations:
            if citation.get('source_id') not in claim.source_ids:
                continue
            # Validate one sentence/line, so an unrelated number in the same
            # document cannot certify a claim about another component.
            for section in re.split(r'\n|(?<=[.!?])\s+', citation.get('relevant_snippet', '')):
                body = normalized(section)
                target = numeric_value(claim.value)
                if target is None or not any(numeric_value(m[1]) == target and normalized(m[2]) == normalized(claim.unit)
                                             for m in QUANTITY.finditer(section)):
                    continue
                subjects = re.findall(r'vf\s*(?:e34|[356789])|plus|eco|pin cao ap|\bpin\b|ac quy|soh|soc', normalized(claim.subject))
                if any(re.sub(r'\s', '', subject) not in re.sub(r'\s', '', body) for subject in subjects):
                    continue
                policy_duration = (claim.claim_key == 'warranty' and 'bao hanh' in normalized(citation.get('title', ''))
                                   and normalized(claim.unit) in {'nam', 'km'})
                if not policy_duration and not any(word in body for word in keywords.get(claim.claim_key, (claim.claim_key,))):
                    continue
                if claim.claim_key == 'range' and any(term in body for term in ('lich su', 'da chay', 'bao duong', 'bao hanh')):
                    continue
                if claim.claim_key == 'warranty' and ('khong bao hanh' in body or 'khong ap dung' in body):
                    continue
                battery_requirements = [c for c in claim.conditions if c in {'pin_included', 'pin_excluded', 'battery_rental'}]
                if battery_requirements and battery_condition(section) not in battery_requirements:
                    continue
                if any(normalized(condition) not in body for condition in claim.conditions if condition not in battery_requirements):
                    continue
                if claim.claim_key == 'price':
                    if 'tu ' in body and 'tu' not in [normalized(c) for c in claim.conditions]:
                        continue
                    if any(term in body for term in ('uu dai', 'sau giam', 'lan banh')) and not any(normalized(c) in body for c in claim.conditions if normalized(c) in {'uu dai', 'lan banh'}):
                        continue
                    years = [int(y) for y in re.findall(r'\b20\d{2}\b', body)]
                    if years and max(years) < date.today().year - 1:
                        continue
                supported = True
        if not supported:
            unsupported.append(claim.model_dump())
        for old in prior_claims:
            if old.claim_key == claim.claim_key and old.subject == claim.subject and old.value != claim.value:
                conflicts.append({'prior': old.model_dump(), 'current': claim.model_dump(),
                                  'same_conditions': old.conditions == claim.conditions})
    return {'supported': not unsupported, 'unsupported_claims': unsupported, 'conflicts': conflicts}


def extract_numeric_claims(answer: str, citations: list[dict], subject: str = '', query: str = '') -> list[AnswerClaim]:
    """Also inspect answer text: omitted structured claims cannot bypass checks."""
    claims = []
    for section in re.split(r'\n|(?<=[.!?])\s+', answer):
        body = normalized(section)
        for match in QUANTITY.finditer(section):
            value, unit = match.groups()
            key = ('price' if normalized(unit) in {'vnd', 'dong', 'ty dong', 'trieu dong'} else
                   'capacity' if unit.casefold() == 'kwh' else
                   'charging_time' if normalized(unit) == 'phut' else
                   'warranty' if 'bao hanh' in body or 'bao hanh' in normalized(query) else 'range' if unit.casefold() == 'km' else 'capacity')
            conditions = [term for term in ('WLTP', 'NEDC', 'từ', 'ưu đãi', 'lăn bánh') if normalized(term) in body]
            battery = battery_condition(section)
            if key == 'price' and battery:
                conditions.append(battery)
            claim_subject = subject
            if not re.search(r'plus|eco|\bpin\b|ac quy', normalized(subject)):
                model_version = re.search(r'vf\s*(e34|[356789])\s*(plus|eco)?', body)
                if model_version:
                    claim_subject = 'VF' + model_version[1].upper() + (' ' + model_version[2].title() if model_version[2] else '')
            claims.append(AnswerClaim(claim_key=key, value=value, unit=unit, subject=claim_subject,
                                      conditions=conditions, source_ids=[c['source_id'] for c in citations]))
    return claims


def normalized(text: str) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
                            if not unicodedata.combining(c)).split())


def is_turtle_question(query: str) -> bool:
    return any(term in normalized(query) for term in ("con rua", "rua vang", "turtle"))


def clean_section(text: str) -> str:
    lines = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if line and line not in seen:
            lines.append(line)
            seen.add(line)
    return "\n".join(lines)


def answer_section(query: str, text: str) -> str:
    lower = query.casefold()
    subject = normalized(query)
    body = normalized(text)
    if any(term in subject for term in ("lai thu", "chay thu")) and not any(term in body for term in ("lai thu", "chay thu")):
        return ""
    if any(term in subject for term in ("gia lan banh", "chi phi lan banh")):
        if not any(term in body for term in ("lan banh", "du toan")):
            return ""
    elif any(term in subject for term in ("gia xe", "bang gia")):
        if not any(term in body for term in ("gia", "chi phi")):
            return ""
    if any(term in subject for term in ("cac dong xe", "cac mau xe", "mau xe", "dai san pham")) and not any(term in body for term in ("vf3", "vf 3", "vf5", "vf 5", "vf6", "vf 6", "vf7", "vf 7", "vf8", "vf 8", "vf9", "vf 9")):
        return ""
    if is_turtle_question(query):
        subjects = ("rua", "turtle", "gioi han cong suat", "han che cong suat", "limited driving power")
        lines = text.splitlines()
        start = next((i for i, line in enumerate(lines) if any(term in normalized(line) for term in subjects)), None)
        if start is None:
            return ""
        end = next((i for i in range(start + 1, len(lines))
                    if normalized(lines[i]).startswith(("chi bao ", "den bao "))
                    and not any(term in normalized(lines[i]) for term in subjects)), len(lines))
        section = "\n".join(lines[start:end]).strip()
        # An indicator list is not an explanation of its meaning.
        if not any(term in normalized(section) for term in ("khi ", "la ", "giam", "han che")):
            return ""
        return section
    if "bảo hành" in lower and "điều kiện" in lower and not any(term in lower for term in ("bao lâu", "thời hạn")):
        # A duration's 'whichever comes first' clause does not explain eligibility.
        body = text.casefold()
        if "sử dụng tiêu chuẩn" in lower and not re.search(r"(?:sử dụng tiêu chuẩn|điều kiện tiêu chuẩn)[^\n]{0,80}(?:được hiểu|là\s|bao gồm|không dùng|không sử dụng)", body):
            return ""
        components = ("pin", "sơn", "kim loại", "xuyên thủng", "gỉ", "phụ tùng", "phụ kiện", "truyền động", "ắc-quy", "ắc quy", "bộ phận treo", "lốp")
        if not any(term in lower for term in components) and any(term in body for term in components):
            return ""
        if not any(term in body for term in ("sử dụng đúng", "bảo dưỡng định kỳ", "tuân thủ", "không bảo hành", "không áp dụng", "dịch vụ thương mại", "được hiểu là", "bao gồm", "không sử dụng để", "không dùng để")):
            return ""
    if "đặt lịch" in lower:
        lines = clean_section(text).splitlines()
        start = next((i for i, line in enumerate(lines) if "đặt lịch" in line.casefold()), None)
        if start is None:
            return ""
        end = next((i for i in range(start + 1, len(lines)) if re.match(r"^\d+(?:\.\d+)*\.\s", lines[i]) or "kiểm tra cảnh báo" in lines[i].casefold()), len(lines))
        section = "\n".join(lines[start:end])
        if any(term in lower for term in ("hướng dẫn", "cách", "làm thế nào", "như thế nào")):
            if not re.search(r"bước\s*\d+|(?:bấm|chọn|nhập)\s", section, re.I):
                return ""
            steps = [int(n) for n in re.findall(r"bước\s*(\d+)", section, re.I)]
            if steps and steps != list(range(1, max(steps) + 1)):
                return ""
        return section
    if "bảo hành" in lower and any(term in lower for term in ("bao lâu", "thời hạn", "mấy năm")):
        components = ("pin", "sơn", "kim loại", "xuyên thủng", "gỉ", "phụ tùng", "phụ kiện", "truyền động", "ắc quy", "bộ phận treo", "lốp")
        requested = [term for term in components if term in lower]
        if not requested:
            lines = text.splitlines()
            boundary = next((i for i, line in enumerate(lines) if any(term in line.casefold() for term in components)), len(lines))
            text = "\n".join(lines[:boundary])
            # A whole-vehicle question cannot use a component policy or a menu.
            if any(term in text.casefold() for term in components):
                return ""
            if not re.search(r"\d+\s*năm", text, re.I):
                return ""
            if "the all new" in text.casefold() and "the all new" not in lower:
                return ""
    return text
