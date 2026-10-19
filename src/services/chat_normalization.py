"""Conservative Vietnamese chat spelling shared by every decision boundary."""
import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field


def fold_text(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                   if not unicodedata.combining(c)).replace('đ', 'd')


def _fold_for_offsets(text: str) -> str:
    # Unicode casefold may expand a character (ß -> ss); keep slice offsets stable.
    return ''.join(folded if len(folded := fold_text(char)) == 1 else char for char in text)


# Restore known phrases, not arbitrary Vietnamese words ("chay" is ambiguous).
_PHRASES = (
    'không nhận sạc', 'không sạc được', 'không khởi động', 'không di chuyển được',
    'không đi được', 'không chạy được', 'không chạy nổi', 'không thể tăng tốc',
    'không vào điện', 'không lên nguồn', 'không mở được cửa', 'không mở cửa được',
    'không mở được khóa', 'không phanh được', 'phanh không ăn', 'không ăn phanh',
    'không có khói', 'không có', 'không còn', 'không phải', 'không biết', 'chưa biết',
    'không hài lòng', 'thái độ', 'nhân viên', 'khiếu nại', 'bức xúc', 'phản ánh',
    'hoàn tiền', 'thu sai', 'khen ngợi', 'bảo dưỡng', 'bảo hành', 'chính sách',
    'bao lâu', 'bao nhiêu', 'thông số', 'giá xe', 'đặt lịch', 'lái thử',
    'dung lượng', 'quãng đường', 'khuyến mãi', 'ưu đãi', 'lăn bánh', 'điều kiện',
    'cách sạc', 'sạc nhanh', 'sạc pin', 'bình thường', 'vẫn đi được', 'vẫn chạy được',
    'xe tôi', 'xe của tôi', 'của tôi', 'của mình', 'của em', 'bây giờ',
    'đang báo', 'đang bị', 'đang hiện', 'vừa bị', 'báo lỗi', 'mã lỗi',
    'rùa vàng', 'con rùa', 'đèn đỏ', 'nháy đỏ', 'nhấp nháy', 'đèn cảnh báo',
    'mùi khét', 'bốc khói', 'xì khói', 'bốc lửa', 'chập điện', 'mất phanh',
    'liệt phanh', 'kẹt chân ga', 'kẹt ga', 'nổ lốp', 'tai nạn', 'lật xe',
    'ngập nước đến sàn', 'cao tốc', 'mất lái', 'giảm công suất', 'cứu hộ',
    'chết máy', 'sập nguồn', 'vô lăng', 'ắc quy', 'pin cao áp', 'chìa khóa',
    'Hà Nội', 'Hồ Chí Minh', 'Đà Nẵng', 'là gì', 'ý nghĩa', 'giải thích',
    'bị cháy', 'đang chạy', 'vẫn chạy', 'chạy yếu', 'chạy bình thường', 'khách hàng',
)
_CANONICAL = {fold_text(phrase): phrase for phrase in _PHRASES}
_PHRASE_RE = re.compile(r'(?<!\w)(?:' + '|'.join(
    re.escape(p) for p in sorted(_CANONICAL, key=len, reverse=True)) + r')(?!\w)')
_ALIASES = {'ko': 'không', 'khong': 'không', 'hok': 'không', 'đc': 'được',
            'dc': 'được', 'duoc': 'được', 'ntn': 'như thế nào', 'bth': 'bình thường',
            'mik': 'mình', 'mn': 'mọi người'}
_ALIAS_RE = re.compile(r'(?<!\w)(?:' + '|'.join(_ALIASES) + r')(?!\w)', re.I)
_NEGATION_NEXT = r'(?:co|con|sac|di|chay|khoi|phanh|an|duoc|biet|hai|phai|thay|bao|bi|nhan)\b'


def normalize_chat_text(text: str) -> str:
    text = unicodedata.normalize('NFC', text)
    from src.services.chat_language import canonical_english_phrases
    text = canonical_english_phrases(text)
    # Stable business nouns keep translation paraphrases on the same evidence
    # route. These substitutions add no vehicle facts or operational receipt.
    for pattern, canonical in [
        (r'\b(?:phạm vi|khoảng cách) (?:lái xe|di chuyển|hoạt động)\b', 'quãng đường'),
        (r'\bphạm vi công bố\b', 'quãng đường công bố'),
        (r'\bvị trí ngồi\b', 'chỗ ngồi'),
        (r'\bpin cao thế\b', 'pin cao áp'),
        (r'\bpin khởi động/kết thúc\b', 'pin đầu/cuối'),
        (r'\bbảo trì\b', 'bảo dưỡng'),
        (r'\bđặt bảo dưỡng\b', 'đặt lịch bảo dưỡng'),
        (r'\bpin phụ\b', 'ắc quy'),
        (r'\btrụ sạc công cộng\b', 'trạm sạc công cộng'),
    ]:
        text = re.sub(pattern, canonical, text, flags=re.I)
    if re.search(r'bao nhiêu ghế|mấy ghế|số ghế', text, re.I):
        text = re.sub(r'\bghế\b', 'chỗ ngồi', text, flags=re.I)
    if re.search(r'\bsạc\b', text, re.I):
        text = re.sub(r'\btrạm công cộng\b', 'trạm sạc công cộng', text, flags=re.I)
    # Keep line breaks: callers use them to distinguish clauses and OCR evidence.
    text = re.sub(r'[^\S\n]+', ' ', text).strip()
    text = _ALIAS_RE.sub(lambda m: m[0] if m[0] == 'DC' else _ALIASES[m[0].casefold()], text)
    folded = _fold_for_offsets(text)
    matches = list(re.finditer(r'\b(?:k|kh)\b(?=\s+' + _NEGATION_NEXT + ')', folded))
    for match in reversed(matches):
        # "300 k" is a price/unit, not a negation.
        if not _is_amount_suffix(text[:match.start()]):
            text = text[:match.start()] + 'không' + text[match.end():]
    folded = _fold_for_offsets(text)
    for match in reversed(list(_PHRASE_RE.finditer(folded))):
        # Accented fire/driving words carry meaning that accent folding loses.
        original = text[match.start():match.end()]
        if re.search(r'\b(?:cháy|chạy)\b', original, re.I):
            continue
        text = text[:match.start()] + _CANONICAL[match[0]] + text[match.end():]
    return text


class Expansion(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: str = Field(min_length=1, max_length=12)
    replacement: str = Field(min_length=1, max_length=60)


class ContextualSpelling(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expansions: list[Expansion] = Field(default_factory=list, max_length=8)
    needs_confirmation: bool


class NormalizedMessage(BaseModel):
    original_text: str
    text: str
    needs_confirmation: bool = False


_AMBIGUOUS = {'bh', 'kh', 'k', 'mk', 'bt', 'chay'}
_CONTEXTUAL_EXPANSIONS = {
    'bh': {'bảo hành', 'bây giờ'}, 'kh': {'khách hàng'},
    'bt': {'bình thường', 'biết'}, 'mk': {'mình', 'mật khẩu'},
}
_KNOWN_WORDS = set(fold_text(' '.join(_PHRASES)).split()) | set(
    'xe pin toi em minh cua va hay hoac nhung thi la gi nao o tai de voi cho muon can '
    'doi mua ban den ma loi vinfast plus eco km kwh v dc ac abs soc soh bms adas '
    'co con duoc khong dang van khach hang ho tro xin chao cam on bao ve '.split())
_FORBIDDEN_EXPANSION = re.compile(
    r'\b(?:khong|chua|het|khoi|khet|chay|phanh|lua|nan|no|ngap|ket|hong|loi|'
    r'ignore|jailbreak)\b|bo qua|vo hieu|cao ap')


def _candidates(text: str) -> set[str]:
    return {m[0] for m in re.finditer(r'\b[a-z]{1,4}\b', text, re.I)
            if not (m[0].casefold() == 'k' and _is_amount_suffix(text[:m.start()]))
            and (m[0].casefold() in _AMBIGUOUS or
                 not m[0].isupper() and m[0].casefold() not in _KNOWN_WORDS and len(m[0]) >= 2
                 and not re.search(r'[aeiouy]', m[0], re.I))}


def _is_amount_suffix(prefix: str) -> bool:
    return bool(re.search(r'(?<!\w)\d+(?:[.,]\d+)*\s*$', prefix))


def _ambiguous_tokens(text: str) -> set[str]:
    return {token for token in _candidates(text) if token.casefold() in _AMBIGUOUS}


def clarification_for(text: str) -> str:
    tokens = sorted(_candidates(text))
    term = ', '.join('“' + word + '”' for word in tokens[:3]) or 'phần viết tắt'
    reply = f'Anh/chị vui lòng viết đầy đủ {term} để em hiểu đúng yêu cầu nhé.'
    if 'chay' in tokens:
        reply = 'Anh/chị muốn nói xe đang chạy hay xe bị cháy? Anh/chị vui lòng viết đầy đủ có dấu để em hiểu đúng.'
    if re.search(r'phanh|khói|khoi|cháy|chay|khét|khet|cao tốc|cao toc', text, re.I):
        reply += ' Nếu xe có dấu hiệu mất an toàn, anh/chị hãy dừng ở vị trí an toàn và liên hệ cứu hộ.'
    return reply


async def normalize_message(text: str, *, recent_turns: list[dict], budget: dict) -> NormalizedMessage:
    # Imports stay local: safety uses the deterministic normalizer itself.
    from src.agents.guardrails import evaluate_hard_safety, sanitize_pii
    from src.services.agent_llm import structured_call

    original = sanitize_pii(text.strip())[0]
    normalized = normalize_chat_text(original)
    # A direct answer to our own spelling question completes the previous text.
    if len(recent_turns) >= 2 and ('vui lòng viết đầy đủ' in recent_turns[-1].get('content', '')
                                  or 'xe đang chạy hay xe bị cháy' in recent_turns[-1].get('content', '')):
        previous = normalize_chat_text(sanitize_pii(str(recent_turns[-2].get('content', '')))[0])
        pending = _ambiguous_tokens(previous)
        explicit = {'bảo hành', 'bây giờ', 'không', 'khách hàng', 'bình thường', 'biết', 'mình', 'mật khẩu', 'cháy', 'chạy'}
        if len(pending) == 1 and normalized.casefold() in explicit:
            normalized = re.sub(r'\b' + re.escape(next(iter(pending))) + r'\b', lambda _: normalized, previous)
            normalized = normalize_chat_text(normalized)
    result = NormalizedMessage(original_text=original, text=normalized)
    if evaluate_hard_safety(normalized)[0]:
        return result
    candidates = _candidates(normalized)
    if not candidates:
        return result
    if any(token.casefold() == 'chay' for token in candidates):
        result.needs_confirmation = True
        return result
    parsed = await structured_call({
        'latest_user_message': normalized, 'llm_budget': budget,
        'memory_summary': str([{**turn, 'content': sanitize_pii(str(turn.get('content', '')))[0][:400]}
                               for turn in recent_turns[-2:]])[:1000],
    }, 'normalization', ContextualSpelling)
    if parsed is None:
        result.needs_confirmation = bool(_ambiguous_tokens(normalized))
        return result
    if parsed.needs_confirmation:
        result.needs_confirmation = True
        return result
    replacements = {}
    for expansion in parsed.expansions:
        token, replacement = expansion.token, expansion.replacement.strip()
        if (token not in candidates or token in replacements
                or token.casefold() in _CONTEXTUAL_EXPANSIONS
                and replacement.casefold() not in _CONTEXTUAL_EXPANSIONS[token.casefold()]
                or not re.fullmatch(r'[^\W\d_]+(?: [^\W\d_]+){0,4}', replacement)
                or _FORBIDDEN_EXPANSION.search(fold_text(replacement))):
            result.needs_confirmation = True
            return result
        replacements[token] = replacement
    if replacements:
        pattern = re.compile(r'\b(?:' + '|'.join(re.escape(token) for token in replacements) + r')\b')
        expanded = normalize_chat_text(pattern.sub(lambda m: replacements[m[0]], normalized))
        from src.agents.nodes.triage_node import classify_request_kind
        if (evaluate_hard_safety(expanded)[0]
                or classify_request_kind(expanded) in {'incident', 'complaint'}
                and classify_request_kind(normalized) not in {'incident', 'complaint'}
                or re.search(r'\b(?:dat|tao|huy|doi|mua|ban|thao|sua|dau day)\b',
                             fold_text(' '.join(replacements.values())))):
            result.needs_confirmation = True
            return result
        result.text = expanded
    result.needs_confirmation = bool(_ambiguous_tokens(result.text))
    return result
