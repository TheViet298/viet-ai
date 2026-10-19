"""Select complete answer sections and reject descriptions posing as procedures."""
import ast
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


QUANTITY = re.compile(r'(?<![\w])(\d+(?:[.,]\d+)*(?:\s*[-–]\s*\d+(?:[.,]\d+)*)?)\s*((?:tỷ|triệu)\s*đồng|(?:vnđ|vnd|đồng)(?:/(?:kwh|phút))?|km/h|km|kwh|kw|phút|tháng|năm|chỗ(?: ngồi)?|seats?|%)(?!\w)', re.I)


def canonical_quantity_unit(unit: str) -> str:
    return re.sub(r'^(?:dong|vnd)(?=/|$)', 'vnd', normalized(unit))


def canonical_answer_claim(claim: AnswerClaim) -> AnswerClaim:
    if re.match(r'^vnd/', canonical_quantity_unit(claim.unit)):
        return claim.model_copy(update={'claim_key': 'price'})
    return claim


def price_from(text: str) -> bool:
    return bool(re.search(r'\btu\s*:?\s*\d[\d.,]*\s*(?:(?:ty|trieu)\s*dong|vnd|dong)', normalized(text)))


def textual_claim_supported(claim: AnswerClaim, section: str) -> bool:
    """Conservative source-bound wording check; never infer a new capability."""
    if claim.claim_key not in {'features', 'feature', 'procedure', 'steps', 'instruction', 'instructions', 'warranty', 'policy'} or claim.unit:
        return False
    value, body = normalized(claim.value), normalized(section)
    if any((term in value) != (term in body) for term in ('khong', 'chua', 'chi khi', 'neu ')):
        return False
    # Drop grammatical connectors only; all substantive words must occur in order
    # in one sentence, rather than borrowing capabilities from another section.
    value = re.sub(r'^co the\s+', '', value)
    tokens = [word for word in re.findall(r'\w+', value) if word not in {'va', 'de', 'cac', 'nhung'}]
    position = 0
    source_tokens = re.findall(r'\w+', body)
    for token in tokens:
        try:
            position = source_tokens.index(token, position) + 1
        except ValueError:
            return False
    return len(tokens) >= 2


def catalog_fact_sections(citation: dict) -> list[str]:
    text = citation.get('relevant_snippet', '')
    sections = re.split(r'\n|(?<=[.!?])\s+', text)
    if citation.get('source_type') == 'official_service':
        # "Free" is an explicit zero price, scoped to the same source tier.
        sections += [re.sub(r'miễn phí', 'Giá 0 đồng/phút', line, flags=re.I) for line in text.splitlines()
                     if re.match(r'^\s*(?:[-*]\s*)?miễn phí\s+từ phút thứ \d+', line, re.I)]
    if citation.get('source_type') != 'official_catalog':
        # A policy table often puts the component and usage condition above
        # its model rows. Attach only those headers, never a neighbouring row's
        # quantities or model list. New headings replace the previous scope.
        heading, condition = '', ''
        scoped = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            is_heading = (not QUANTITY.search(line) and len(line) <= 220
                          and not re.search(r'[.!?]$', line)
                          and not re.match(r'^[-*]\s', line))
            if is_heading:
                subordinate = heading and (
                    normalized(line).startswith(normalized(heading).rstrip(':'))
                    or re.match(r'^(?:dieu kien|su dung|mua theo|xe dang|xe da)\b', normalized(line)))
                if line.endswith(':') and subordinate:
                    condition = line
                else:
                    heading, condition = line, ''
            else:
                scoped.append('\n'.join(value for value in (heading, condition, line) if value))
        return list(dict.fromkeys([*sections, *scoped]))
    header = text.splitlines()[0] if text else ''
    # Only expand a version-scoped catalog record, never mix facts across trims.
    if not re.search(r'phien ban.*vf\s*(?:e34|[356789]).*\b(?:eco|plus)\b', normalized(header)):
        return sections
    for line in text.splitlines()[1:]:
        match = re.match(r'- (hero|specs_raw):\s*(\{.*\})\s*$', line)
        if not match:
            continue
        try:
            data = ast.literal_eval(match[2])
        except (ValueError, SyntaxError, RecursionError):
            continue
        if not isinstance(data, dict):
            continue
        if match[1] == 'hero':
            highlights = data.get('highlights') or {}
            if isinstance(highlights, dict):
                sections.extend(f'{header} {label}: {value}' for label, value in highlights.items()
                                if isinstance(value, (str, int, float)))
            price = data.get('price_from_vnd')
            if isinstance(price, (int, float)) and not isinstance(price, bool):
                sections.append(f'{header} Giá từ: {price} VNĐ (giá trong nguồn catalog).')
        else:
            for group in data.values():
                if isinstance(group, dict):
                    sections.extend(f'{header} {label}: {value}' for label, value in group.items()
                                    if isinstance(value, (str, int, float)))
    return sections


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


def tariff_conditions(text: str) -> list[str]:
    body = re.sub(r'\bthu(?=\d)', 'thu ', normalized(text))
    return re.findall(r'ap dung tu ngay \d{1,2}/\d{1,2}/\d{4}|'
                      r'tu phut thu \d+ (?:den phut thu \d+|tro di)', body)


def validate_answer_claims(claims: list[AnswerClaim], citations: list[dict], prior_claims: list[AnswerClaim]) -> dict:
    unsupported, conflicts = [], []
    keywords = {'range': ('quang duong', 'mot lan sac', 'pham vi'),
                'warranty': ('bao hanh',), 'charging_time': ('sac',),
                'capacity': ('dung luong',), 'power': ('cong suat',), 'seats': ('cho', 'seats'), 'price': ('gia',),
                'soc': ('soc', 'muc pin', 'sac'), 'speed': ('toc do',),
                'maintenance_interval': ('bao duong',), 'odometer': ('da chay', 'cong to met')}
    for claim in claims:
        claim = canonical_answer_claim(claim)
        supported = False
        for citation in citations:
            if citation.get('source_id') not in claim.source_ids:
                continue
            # Numeric facts stay line scoped. A procedure may span ordered steps
            # in one selected source section, never across different citations.
            sections = catalog_fact_sections(citation)
            if claim.claim_key in {'procedure', 'steps', 'instruction', 'instructions'} and numeric_value(claim.value) is None:
                sections.append(citation.get('relevant_snippet', ''))
            for section in sections:
                body = normalized(section)
                target = numeric_value(claim.value)
                textual = target is None
                if textual and not textual_claim_supported(claim, section):
                    continue
                if not textual and not any(numeric_value(m[1]) == target and canonical_quantity_unit(m[2]) == canonical_quantity_unit(claim.unit)
                                           for m in QUANTITY.finditer(section)):
                    continue
                subjects = re.findall(r'vf\s*(?:e34|[356789])|plus|eco|\bawd\b|\bfwd\b|pin cao ap|\bpin\b|ac quy|soh|soc', normalized(claim.subject))
                if claim.claim_key == 'price' and '/' in claim.unit and citation.get('source_type') == 'official_service':
                    models = citation.get('applicable_models', [])
                    models = models.split(',') if isinstance(models, str) else models
                    applicable = {re.sub(r'\s', '', normalized(model)) for model in models}
                    subjects = [subject for subject in subjects if not (
                        subject.startswith('vf') and ('all' in applicable or re.sub(r'\s', '', subject) in applicable))]
                if any(re.sub(r'\s', '', subject) not in re.sub(r'\s', '', body) for subject in subjects):
                    continue
                policy_duration = (claim.claim_key == 'warranty' and 'bao hanh' in normalized(citation.get('title', ''))
                                   and normalized(claim.unit) in {'nam', 'km'})
                tariff = claim.claim_key == 'price' and '/' in claim.unit
                if tariff and any(condition not in [normalized(c) for c in claim.conditions]
                                  for condition in tariff_conditions(section)):
                    continue
                if not textual and not policy_duration and not tariff and not any(word in body for word in keywords.get(claim.claim_key, (claim.claim_key,))):
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
                    if price_from(section) and 'tu' not in [normalized(c) for c in claim.conditions]:
                        continue
                    if any(term in body for term in ('uu dai', 'sau giam', 'lan banh')) and not any(normalized(c) in body for c in claim.conditions if normalized(c) in {'uu dai', 'lan banh'}):
                        continue
                    years = [int(y) for y in re.findall(r'\b20\d{2}\b', body)]
                    if years and max(years) < date.today().year - 1 and not (
                            tariff and citation.get('source_type') == 'official_service' and 'ap dung tu ngay' in body):
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
    for section in re.split(r'\n|(?<=[.!?;])\s+', answer):
        # "Free" asserts a zero price even when the model omits structured
        # claims. Use only its stated minute unit/tier, never a source default.
        for free in reversed(list(re.finditer(r'\bmiễn phí\b', section, re.I))):
            prefix = normalized(section[:free.start()])
            if re.search(r'(?:khong|chua)(?: duoc| con| he| phai)*$', prefix):
                continue
            tail = section[free.end():]
            next_quantity = QUANTITY.search(tail)
            if next_quantity:
                tail = tail[:next_quantity.start()]
            unit = 'đồng/phút' if re.search(r'\bphút\b', tail, re.I) else 'đồng'
            section = section[:free.start()] + '0 ' + unit + section[free.end():]
        body = normalized(section)
        quantities = list(QUANTITY.finditer(section))
        for index, match in enumerate(quantities):
            value, unit = match.groups()
            key = ('price' if normalized(unit).split('/')[0] in {'vnd', 'dong', 'ty dong', 'trieu dong'} else
                   'capacity' if unit.casefold() == 'kwh' else 'power' if unit.casefold() == 'kw' else
                   'seats' if normalized(unit) in {'cho', 'cho ngoi', 'seat', 'seats'} else
                   'charging_time' if normalized(unit) == 'phut' else
                   'speed' if unit.casefold() == 'km/h' else
                   'soc' if unit == '%' and re.search(r'sac|soc|muc pin', body) else
                   'maintenance_interval' if 'bao duong' in body and normalized(unit) in {'thang', 'nam', 'km'} else
                   'warranty' if 'bao hanh' in body or 'bao hanh' in normalized(query) else
                   'odometer' if 'da chay' in body and unit.casefold() == 'km' else
                   'range' if unit.casefold() == 'km' else 'unknown_quantity')
            conditions = [term for term in ('WLTP', 'NEDC', 'từ', 'ưu đãi', 'lăn bánh')
                          if re.search(r'\b' + re.escape(normalized(term)) + r'\b', body)]
            battery = battery_condition(section)
            if key == 'price' and battery:
                conditions.append(battery)
            if key == 'price' and '/' in unit:
                # Each rate keeps its own following tier/date, even when the
                # model renders all source rows in one paragraph.
                end = quantities[index + 1].start() if index + 1 < len(quantities) else len(section)
                free_tier = re.search(r'miễn phí', section[match.end():end], re.I)
                if free_tier:
                    end = match.end() + free_tier.start()
                conditions = [condition for condition in conditions if normalized(condition) != 'tu']
                conditions.extend(tariff_conditions(section[match.start():end]))
                if price_from(section[match.start():end]):
                    conditions.append('từ')
            claim_subject = subject
            model_version = re.search(r'vf\s*(e34|[356789])\s*(plus|eco)?\s*(awd|fwd)?', body)
            if model_version:
                # Explicit answer entities are claims, never silently relabel them
                # using the requested model/trim to make unrelated evidence pass.
                model = 'VF' + model_version[1].upper()
                version = model_version[2]
                context_model = re.search(r'vf\s*(e34|[356789])', normalized(subject))
                if version or not context_model or context_model[1] != model_version[1]:
                    component = ' '.join(re.findall(r'pin cao ap|ac quy|\bpin\b', normalized(subject)))
                    claim_subject = (model + (' ' + version.title() if version else '')
                                     + (' ' + model_version[3].upper() if model_version[3] else '') + ' ' + component).strip()
                elif not re.search(r'plus|eco|\bpin\b|ac quy', normalized(subject)):
                    claim_subject = model
            component = re.search(r'pin cao ap|ac quy(?: 12\s*v)?', body)
            if component:
                claim_subject = re.sub(r'pin cao ap|ac quy(?: 12\s*v)?|\bpin\b', '', normalized(claim_subject)).strip()
                claim_subject += ' ' + component[0]
            claims.append(AnswerClaim(claim_key=key, value=value, unit=unit, subject=claim_subject,
                                      conditions=conditions, source_ids=[c['source_id'] for c in citations]))
    return claims


def normalized(text: str) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
                            if not unicodedata.combining(c)).split())


def is_turtle_question(query: str) -> bool:
    return any(term in normalized(query) for term in ("con rua", "rua vang", "turtle"))


def is_color_question(query: str) -> bool:
    if any(term in normalized(query) for term in ('den bao', 'canh bao', 'bieu tuong', 'con rua', 'warning', 'indicator')):
        return False
    return bool(re.search(r'\bmàu\b|\bcolou?rs?\b', query, re.I))


def has_color_evidence(citation: dict) -> bool:
    # A catalog URL or model_colors label alone does not certify color entities.
    return citation.get('source_type') == 'official_catalog' and bool(re.search(
        r'(?:\bmàu(?:\s+sắc)?|\bcolou?rs?)[^:\n]{0,100}:\s*\S', citation.get('relevant_snippet', ''), re.I))


def is_maintenance_schedule(query: str) -> bool:
    body = normalized(query)
    if re.search(r'(?<!dat )\blich(?: trinh)? bao duong\b', body):
        return True
    return 'dat lich' not in body and 'bao duong' in body and any(
        term in body for term in ('chu ky', 'dinh ky', 'bao lau', 'khi nao', 'moc bao duong'))


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
    from src.services.charging_questions import is_public_charging_procedure
    if is_public_charging_procedure(query):
        steps = [int(n) for n in re.findall(r'buoc\s*(\d+)', body)]
        if (not steps or steps != list(range(1, max(steps) + 1))
                or not re.search(r'cam.{0,40}(?:sung sac|cap sac)|(?:sung sac|cap sac).{0,40}cam', body)):
            return ''
    if is_maintenance_schedule(query):
        from src.services.warranty_questions import is_general_maintenance_query
        if (is_general_maintenance_query(query)
                and 'lich bao duong theo dung mau xe' in body
                and 'quang duong va thoi gian' in body):
            return text
        if re.search(r'\b(?:tai lieu|so bao duong|so tay)\b.{0,30}\b(?:nao|o dau)\b', subject):
            return text if any(reference in body for reference in ('so bao duong', 'so tay', 'tai lieu bao duong')) else ''
        interval_lines = [normalized(line) for line in text.splitlines()
                          if re.search(r'\d[\d.,]*\s*(?:km|thang|nam)\b', normalized(line))]
        if not any(re.search(r'(?:bao duong|chu ky)[^.!?]{0,80}\d', line) for line in interval_lines):
            return ''
        if 'dat lich' in normalized(text.splitlines()[0] if text.splitlines() else ''):
            return ''
        return text
    if any(term in subject for term in ('bieu phi', 'phi sac', 'gia sac')):
        if not re.search(r'\d[\d.,]*\s*(?:vnđ|vnd|đồng)/(?:kwh|phút)', text, re.I):
            return ''
        tariff_heading = re.search(r'VinFast cung cấp đơn giá sạc', text, re.I)
        if tariff_heading and 'pin hong' in normalized(text[:tariff_heading.start()]):
            text = text[tariff_heading.start():]
    for app_goal in ('lich su sac', 'dieu hoa'):
        if app_goal in subject and any(term in subject for term in ('ung dung', 'app', 'tu xa', 'lich su sac')):
            if app_goal not in body:
                return ''
            if any(term in subject for term in ('cach ', 'huong dan', 'lam the nao', 'nhu the nao')):
                header = text.splitlines()[0] if text.splitlines() else ''
                if app_goal not in normalized(header):
                    return ''
                steps = [int(n) for n in re.findall(r'buoc\s*(\d+)', body)]
                if steps and steps != list(range(1, max(steps) + 1)):
                    return ''
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
        if not lines or 'đặt lịch' not in lines[0].casefold():
            return ''
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
            if "the all new" not in lower and any(
                    "the all new" in line.casefold() and not normalized(line).startswith("khong ap dung")
                    for line in text.splitlines()):
                return ""
    return text
