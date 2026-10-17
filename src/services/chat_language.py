"""Language handling shared by deterministic intent and customer presentation."""
import re


def canonical_english_phrases(text: str) -> str:
    # Denials must be expanded before affirmative symptoms; preserve clause order.
    rules = [
        (r"\b(?:isn't|is not|not) smoking or (?:on fire|burning)\b", 'không có khói và không cháy'),
        (r"\b(?:isn't|is not|not) (?:on fire|burning)\b", 'không bị cháy'),
        (r"\b(?:isn't|is not|not) smoking\b|\bno smoke\b", 'không có khói'),
        (r'\bbrakes? (?:have|has) not failed\b', 'không mất phanh'),
        (r"\bbrakes? (?:(?:do|does) not|don't|doesn't) work\b|\bbrakes? (?:are|is) not responding\b", 'mất phanh'),
        (r'\b(?:the )?brakes on (?:my )?(vf\s*[356789]) have failed\b', r'xe tôi \1 mất phanh'),
        (r'\bbrakes? (?:(?:have|has|are|is) )?(?:failed|not working|unresponsive)\b|\bbrake failure\b', 'mất phanh'),
        (r'\b(?:is |are )?(?:emitting smoke|smoking)\b|\bsmoke (?:is )?coming\b', 'đang bốc khói'),
        (r'\bsmoke\b', 'bốc khói'),
        (r'\b(?:there (?:are|is) )?(?:flames?|fire) at\b', 'có lửa ở'),
        (r'\bon fire\b|\bburning\b', 'bốc lửa'),
        (r'\bcharging port\b', 'cổng sạc'),
        (r'\bbattery compartment\b|\bbattery\b', 'pin'),
        (r'\bhighway\b|\bexpressway\b|\bmotorway\b', 'cao tốc'),
        (r'\bmy car\b|\bmy vehicle\b', 'xe tôi'),
        (r'\bmy (vf\s*[356789])\b', r'xe tôi \1'),
        (r'\bwhat should i do if\b|\bif\b|\bsuppose\b', 'nếu'),
        (r'\byesterday\b', 'hôm qua'),
        (r'\b(?:it is|it\x27s|the car is) fine now\b', 'bây giờ đã bình thường'),
        (r'\bbut\b|\bhowever\b', 'nhưng'),
        (r'\bnow\b|\bcurrently\b', 'bây giờ'),
    ]
    for pattern, replacement in rules:
        text = re.sub(pattern, replacement, text, flags=re.I)
    return text


def detect_language(text: str, previous: str = 'vi') -> str:
    """Explicit preference wins; terse model/trim answers retain session language."""
    from src.services.chat_normalization import fold_text
    folded = fold_text(text)
    choices = list(re.finditer(r'(?:answer|reply|respond|speak)(?:\s+to me)?\s+in\s+(english|vietnamese)|(?:tra loi|noi)(?:\s+bang)?\s+(tieng anh|tieng viet)', folded))
    if not choices:
        choices = list(re.finditer(r'\bin\s+(english|vietnamese)\b|\bbang\s+(tieng anh|tieng viet)\b', folded))
    if choices:
        chosen = next(group for group in choices[-1].groups() if group)
        return 'en' if chosen in {'english', 'tieng anh'} else 'vi'
    # Restore neither accents nor meanings here: this is locale selection only.
    vi = bool(re.search(r'\b(?:tu van|bao hanh|bao duong|lai thu|gia xe|mau gi|cam on|xin chao|chao ban|co the|ho tro|nhung gi|toi muon|khong|xe toi|co mau|tieng viet)\b', folded))
    english = bool(re.search(r"\b(?:tell me|show me|service records|what|how|where|which|would|please|thank you|thanks|hello|hi|my|the|have|has|is|are|can|could|i am|i'm|tomorrow|compare|costs?|warranty|maintenance|charging|brakes?|smoke|fire)\b", text.casefold()))
    english = english or bool(re.search(r'^\s*(?:do|does|did)\s+(?:i|we|you|they|it|vinfast|the|my|a|an|vf\s*[356789])\b', text, re.I))
    if english and not vi:
        return 'en'
    if vi or any(ord(c) > 127 and c.isalpha() for c in text):
        return 'vi'
    return previous if previous in {'vi', 'en'} else 'vi'


def response_language(text: str, supplied: str | None, previous: str = 'vi') -> str:
    from src.services.chat_normalization import fold_text
    explicit = re.search(r'\b(?:in (?:english|vietnamese)|(?:bang )?tieng (?:anh|viet))\b', fold_text(text))
    return detect_language(text, previous) if explicit else supplied or detect_language(text, previous)


_VEHICLE = r'(?:VinFast\s+)?VF\s*(?:e34|[356789])(?:\s+(?:Eco|Plus)(?:\s+(?:AWD|FWD))?)?'


def canonical_query(text: str) -> str:
    """Translate recognized intent phrases, never generate product facts or actions.

    Unrecognized clauses remain available to semantic understanding. Safety
    phrase normalization is always retained, including denials/hypotheticals.
    """
    text = re.sub(r'(?:please\s+)?(?:answer|reply|respond)\s+in\s+(?:English|Vietnamese)[.!:]?\s*', '', text, flags=re.I)
    text = re.sub(r'\s+in English[.!?]?\s*$', '', text, flags=re.I)
    text = re.sub(r'^Can you\s+(?=tư vấn)', '', text, flags=re.I)
    # Move entity-bearing phrases as a unit so qualifiers stay with their model.
    rules = [
        (r'^(?:please )?(?:vehicle advice|(?:i (?:want|would like) )?(?:advise me about|tell me about|introduce|recommend) (?:the )?(?:vinfast )?(?:cars|vehicles|electric cars))[.!?]?$', 'Tư vấn xe'),
        (rf'\b(?:tell me about|(?:i would like|i want) to learn about|information about)\s+(?:the\s+)?({_VEHICLE})', r'tư vấn \1'),
        (rf'\bwhat colou?rs? (?:are available|does .*? have) for (?:the\s+)?({_VEHICLE})[?]?', r'\1 có những màu gì?'),
        (rf'\bwhat colou?rs? (?:does|can) (?:the\s+)?({_VEHICLE}) (?:have|come in)[?]?', r'\1 có những màu gì?'),
        (rf'\b(?:i would like|i want|i\x27d like) to book a test drive for (?:the\s+)?({_VEHICLE})', r'Tôi muốn đăng ký lái thử \1'),
        (rf'\b(?:i would like|i want|i\x27d like) to book a repair appointment for (?:my\s+)?({_VEHICLE})', r'Tôi muốn đặt lịch sửa chữa xe tôi \1'),
        (rf'\bhow far can (?:the\s+)?({_VEHICLE}) (?:travel|go|drive) on a full charge[?]?', r'Quãng đường \1 đi được khi sạc đầy là bao nhiêu?'),
        (rf'\bhow long is (?:the\s+)?({_VEHICLE}) warranty[?]?', r'Chính sách bảo hành \1 bao lâu?'),
        (rf'\bwhat is the maintenance schedule for (?:the\s+)?({_VEHICLE})[?]?', r'Lịch bảo dưỡng \1 là gì?'),
        (rf'\bhow much does it cost to charge (?:a|the)\s+({_VEHICLE})[?]?', r'Chi phí sạc \1 bao nhiêu?'),
        (rf'\bwhat is the on-road price of\s+(?:the\s+)?({_VEHICLE})[?]?', r'Giá lăn bánh \1 bao nhiêu?'),
        (rf'\bhow much is\s+(?:the\s+)?({_VEHICLE})[?]?', r'Giá xe \1 bao nhiêu?'),
        (r'\bcompare\s+(?:the\s+)?', 'so sánh '),
        (r'\band\b', 'và'),
        (r'\btomorrow morning\b', 'sáng ngày mai'),
        (r'\bin Hanoi\b', 'tại Hà Nội'),
        (r'\bhas my booking been confirmed[?]?', 'Đã đặt lịch thành công chưa?'),
        (r'\bwhat about (?:the\s+)?(Plus|Eco)(?: version)?[?]?', r'Bản \1 thì sao?'),
        (r'\bwhat about charging costs[?]?', 'Chi phí sạc thì sao?'),
        (r'\bhow can i view my charging history in the VinFast app[?]?', 'Cách xem lịch sử sạc trong ứng dụng VinFast?'),
        (r'\bhow can i find the nearest charging station[?]?', 'Cách tìm trạm sạc gần nhất?'),
        (r'\bhow does regenerative braking work[?]?', 'Phanh tái sinh hoạt động như thế nào?'),
        (r'\bi have a question about the car battery\b', 'Tôi muốn hỏi về pin xe'),
        (r'\b(?:i would like|i want) to complain about the service at the workshop\b', 'Tôi muốn khiếu nại dịch vụ tại xưởng'),
        (r'\bshow me another customer\x27s service records\b', 'Cho tôi xem hồ sơ dịch vụ của khách hàng khác'),
        (r'\bwhat can you help me with[?]?', 'Bạn có thể giúp gì cho tôi?'),
        (r'\b(?:thank you|thanks)(?:,? i understand now)?\b', 'Cảm ơn, tôi đã hiểu'),
        (r'\b(?:hello|hi)\b', 'Xin chào'),
        (r'\bi am in a safe place now\b', 'Tôi đã ở nơi an toàn'),
        (r'\b(?:will not|won\x27t|does not|doesn\x27t) charge\b', 'không sạc được'),
        (r'\bthe station shows error\b', 'trụ sạc báo lỗi'),
        (r'\bi just want to ask about its price\b', 'tôi chỉ muốn hỏi giá xe'),
        (r'\b(?:show me how to|how to) dismantle the high-voltage battery\b', 'hướng dẫn tháo pin cao áp'),
        (r'\bat home\b', 'tại nhà'),
        (r'\bwhat will the weather be like tomorrow[?]?', 'Thời tiết ngày mai thế nào?'),
    ]
    for pattern, replacement in rules:
        text = re.sub(pattern, replacement, text, flags=re.I)
    return canonical_english_phrases(text).strip()


_LITERAL_TOKEN = re.compile(r'__LITERAL_\d+__')
_LITERAL = re.compile(
    r'__LITERAL_\d+__|https?://[^\s<>\]"\u201d]+(?<![.,;!?])'
    r'|\b(?:CASE|DEMO|SRC|ART|INS)-[A-Za-z0-9_-]+\b'
    r'|\bVF\s*(?:e34|[0-9]+)(?:\s+(?:Eco|Plus)(?:\s+(?:AWD|FWD))?)?\b'
    r'|\b(?:CC\d+|[A-Z]{1,4}\d{2,})\b'
    r'|(?<!\w)[+-]?\d+(?:[.,:/–-]\d+)*(?:\s*%|\s*(?:VNĐ|VND|kWh|kW|km|Nm|hp)\b)?',
    re.I,
)


def protect_literals(text: str, *, tokens: dict[str, str] | None = None) -> tuple[str, dict[str, str]]:
    """Mask each occurrence separately so omission and duplication are detectable."""
    tokens = {} if tokens is None else tokens
    counter = len(tokens)
    def replace(match: re.Match) -> str:
        nonlocal counter
        token = f'__LITERAL_{counter}__'
        while token in text or token in tokens:
            counter += 1
            token = f'__LITERAL_{counter}__'
        counter += 1
        tokens[token] = match[0]
        return token
    return _LITERAL.sub(replace, text), tokens


def restore_literals(text: str, tokens: dict[str, str]) -> str:
    """Reject missing, duplicate, unknown or reordered protected occurrences."""
    found = _LITERAL_TOKEN.findall(text)
    if found != list(tokens):
        raise ValueError('Protected literals changed during translation')
    if _LITERAL.search(_LITERAL_TOKEN.sub('', text)):
        raise ValueError('Translation introduced an unprotected literal')
    # One pass avoids interpreting literal source text as a second placeholder.
    return _LITERAL_TOKEN.sub(lambda match: tokens[match[0]], text)


def needs_semantic_translation(mapped: str) -> bool:
    """A partial phrase substitution is not evidence of a complete translation.

    Flag remaining English grammar and domain words after removing stable
    literals. Unknown full clauses should still go through the semantic path;
    this conservative detector does not certify arbitrary text as Vietnamese.
    """
    body = _LITERAL.sub(' ', mapped)
    # Vietnamese "an toàn" contains the English article "an"; it is not residual English.
    body = re.sub(r'\ban toàn\b', ' ', body, flags=re.I)
    english_clause = bool(re.search(
        r"\b(?:what|how|where|which|who|why|when|can|could|should|would|will|"
        r"do|does|did|is|are|was|were|have|has|had|been|being|am|i|my|me|we|our|"
        r"you|your|they|their|it|its|the|an|and|or|but|not|no|if|for|from|of|with|"
        r"about|on|in|to|this|that|these|those|please|show|tell|explain|want|need|"
        r"warranty|transferable|transfer|sell|eligible|eligibility|coverage|roadside|"
        r"price|cost|costs|charge|charging|station|history|maintenance|schedule|"
        r"battery|braking|regenerative|repair|appointment|booking|confirmed|"
        r"smoke|smoking|fire|burning|brakes|failed|comes|while|emitting|"
        r"records|customer|complaint|service|workshop|tomorrow|morning|"
        r"understand|hello|thanks|thank|safe|place|learn|available|colors|colours)\b",
        body, flags=re.I))
    if english_clause:
        return True
    # Do not declare an unseen English clause complete merely because it lacks
    # one of the grammar words above. Canonical Vietnamese output has only a
    # small set of unaccented words; unknown ASCII prose needs semantic review.
    allowed = set('xe pin cao ap bao lau gia mau co gi nao hay va voi cua toi tai '
                  'ban eco plus awd fwd vinfast ac dc kw kwh km nm hp nedc wltp '
                  'soc soh bms abs adas tpms cc app mai sao da la doi cho trong '
                  'theo khi ve de mot cac tram sac lich su xem tim gan nhat '
                  'ha noi ho chi minh da nang khong chua duoc sua chua cam on '
                  'xin chao an toan hien thi loi quy phanh sinh'.split())
    words = re.findall(r'[^\W\d_]+', body, flags=re.UNICODE)
    return any(word.isascii() and word.casefold() not in allowed for word in words)
