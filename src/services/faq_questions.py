"""Bounded FAQ decomposition with the original question and vehicle scope retained."""
import re

from src.agents.guardrails import strip_accents


TOPICS = {
    'charging': ('Cách sạc tại trạm công cộng', 'Hướng dẫn cách sạc pin tại trạm sạc công cộng', 'guide'),
    'tariff': ('Biểu phí sạc', 'Biểu phí sạc tại trạm sạc công cộng VinFast', 'policy'),
    'app': ('Tính năng trên App VinFast', 'Tính năng sạc trên ứng dụng VinFast', 'guide'),
    'warranty': ('Bảo hành pin', 'Chính sách bảo hành pin VinFast', 'policy'),
    'capacity': ('Dung lượng pin', 'Dung lượng pin khả dụng', 'catalog'),
    'range': ('Quãng đường công bố', 'Quãng đường công bố', 'catalog'),
    'maintenance': ('Bảo dưỡng định kỳ', 'Lịch bảo dưỡng định kỳ VinFast', 'manual'),
}
CHARGING_TOPICS = ('charging', 'tariff', 'app')
WARRANTY_TOPICS = ('warranty', 'maintenance')


def canonical_service_clauses(text: str) -> str:
    """Map recognized English FAQ phrases; retain every unrecognized qualifier."""
    rules = [
        (r'\bhow (?:do|can) i charge at (?:a|the) public (?:charging )?station\b|\bpublic charging (?:steps|instructions)\b', TOPICS['charging'][1]),
        (r'\bcharging (?:fees|rates)\b', TOPICS['tariff'][1]),
        (r'\b(?:vinfast )?app features\b', TOPICS['app'][1]),
        (r'\bbattery warranty(?: policy| coverage)?\b', TOPICS['warranty'][1]),
        (r'\b(?:scheduled|periodic|regular) maintenance\b|\bmaintenance schedule\b', TOPICS['maintenance'][1]),
    ]
    if sum(bool(re.search(pattern, text, re.I)) for pattern, _ in rules) < 2:
        return text
    for pattern, replacement in rules:
        text = re.sub(pattern, replacement, text, flags=re.I)
    for pattern, replacement in [
        (r'\b(?:please explain|tell me about|i (?:want|would like) to ask about|what (?:is|are) (?:the|my))\s*', ''),
        (r'\band\b', 'và'),
        (r'\bfor (?=(?:my |the )?(?:vinfast )?vf\s*(?:e34|[356789])\b)(?:my |the )?', 'của '),
        (r'\bdo not include\b', 'không hỏi'), (r'\bbut\b', 'nhưng'),
        (r'\bnext month\b', 'tháng sau'), (r'\binternal\b', 'nội bộ'), (r'\bconfidential\b', 'bí mật'),
    ]:
        text = re.sub(pattern, replacement, text, flags=re.I)
    return text


def topic_flags(query: str) -> set[str]:
    text = strip_accents(query.casefold())
    found = set()
    if re.search(r'tram (?:sac|cong cong)', text) and re.search(r'huong dan|cach sac|cac buoc sac', text):
        found.add('charging')
    if re.search(r'bieu phi|phi sac|gia sac|chi phi sac', text):
        found.add('tariff')
    service_context = bool(found or re.search(r'bao duong|bao hanh', text))
    if re.search(r'\bapp\b|ung dung', text) and (not service_context or 'tinh nang' in text):
        found.add('app')
    if 'bao hanh' in text:
        found.add('warranty')
    if 'bao duong' in text:
        found.add('maintenance')
    if re.search(r'dung luong|battery capacity', text):
        found.add('capacity')
    if re.search(r'tam hoat dong|tam di chuyen|quang duong (?:cong bo|toi da|mot lan sac|khi sac)|di duoc bao xa|driving range', text):
        found.add('range')
    return found


def vehicle_models(query: str) -> list[str]:
    return list(dict.fromkeys('VF' + model.upper() for model in re.findall(r'\bvf\s*(e34|[356789])\b', query, re.I)))


def generic_help_query(query: str, vocabulary: str) -> bool:
    text = strip_accents(query.casefold())
    return set(re.findall(r'\w+', text)) <= set(vocabulary.split())


def faq_parts(query: str, keys=tuple(TOPICS)) -> list[tuple[str, str, str | None]]:
    text = strip_accents(query.casefold())
    if re.search(r'khieu nai|bao loi|su co|ket sung|khong sac duoc|khong khoi dong|dang boc khoi', text):
        return []
    warranty_requirement = re.search(r'dieu kien bao hanh|bao hanh.{0,45}yeu cau|de duoc bao hanh', text)
    separate_schedule = re.search(r'lich bao duong|chu ky|moc bao duong|bao duong.{0,30}(?:bao lau|khi nao)|dat lich|hang muc|chi phi', text)
    if warranty_requirement and not separate_schedule:
        return []
    clauses = [part.strip(' .?!') for part in re.split(
        r'[;?!\n]+|\.(?=\s)|,(?!\d)|\s+(?:và|va|đồng thời|dong thoi|kèm theo|nhưng|nhung)\s+', query, flags=re.I) if part.strip(' .?!')]
    clauses = [clause for clause in clauses if not re.search(
        r'\bkhong (?:can |muon )?(?:hoi|biet)\b|\bkhong can (?:bieu phi|tinh nang|bao hanh|bao duong)\b',
        strip_accents(clause.casefold()))]
    found = set().union(*(topic_flags(clause) for clause in clauses))
    chosen = [key for key in keys if key in found]
    if len(chosen) < 2:
        return []
    context, unhandled = [], []
    for clause in clauses:
        if not topic_flags(clause):
            if re.search(r'gia xe|lai thu|thoi tiet|toi muon hoi|cho toi biet', strip_accents(clause.casefold())):
                unhandled.append(clause)
            else:
                context.append(clause)
    # A single model can qualify later clauses. Distinct models stay clause-local.
    inherited = []
    if len(vehicle_models(query)) == 1:
        inherited = re.findall(
            r'\bVF\s*(?:e34|[356789])(?:\s+(?:Eco|Plus)(?:\s+(?:AWD|FWD))?)?\b|\b20\d{2}\b|\b\d[\d.,]*\s*(?:km|tháng|năm)\b|'
            r'\b(?:(?:không|chưa|đã từng|đang)\s+)*(?:chạy dịch vụ|dịch vụ thương mại|cá nhân|thuê pin|mua pin)\b', query, re.I)
    parts = []
    for key in chosen:
        label, base, source_need = TOPICS[key]
        scoped = [clause for clause in clauses if key in topic_flags(clause)]
        details = list(dict.fromkeys([*scoped, *context, *inherited]))
        if key == 'warranty' and 'pin' not in strip_accents(' '.join(scoped).casefold()):
            label, base = 'Bảo hành xe', 'Chính sách bảo hành xe VinFast'
        if key == 'maintenance' and any('dat lich' in strip_accents(clause.casefold()) for clause in scoped):
            label, base, source_need = 'Đặt lịch bảo dưỡng', 'Hướng dẫn đặt lịch bảo dưỡng trên ứng dụng VinFast', 'guide'
        parts.append((label, base + (' — ' + '; '.join(details) if details else ''), source_need))
    if unhandled and keys == tuple(TOPICS):
        parts.append(('Câu hỏi khác', '; '.join(unhandled), None))
    return parts
