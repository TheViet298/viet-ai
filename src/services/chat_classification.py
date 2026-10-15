"""Shared temporal interpretation, independent of agent and persistence."""
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from src.services.chat_normalization import normalize_chat_text


def normalized(text: str) -> str:
    text = normalize_chat_text(text)
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold()) if unicodedata.category(c) != 'Mn').replace('đ', 'd')


DENIED_REPORT = re.compile(
    r'(?:(?:không(?: còn)?|chưa|hết)\s+(?:báo|hiện|có|gặp|lỗi)?(?:\s+(?:mã|lỗi|biểu tượng|đèn|trụ))*\s+'
    r'(?:CC\d{2}|E\d{3}|P\d{4}|BMS_\d{3}|0x[0-9a-f]+|rùa vàng|con rùa|đèn đỏ|P\d{2})(?:\s+nữa)?)|'
    r'(?:(?:không phải|chứ không phải)\s+(?:trụ|mã|lỗi)?\s*(?:CC\d{2}|E\d{3}|P\d{4}|BMS_\d{3}|0x[0-9a-f]+|rùa vàng|con rùa|đèn đỏ|P\d{2}))',
    re.I
)


def without_denied_reports(text: str) -> str:
    return DENIED_REPORT.sub('', normalize_chat_text(text))


def denied_reports(text: str) -> list[str]:
    text = normalize_chat_text(text)
    if temporal_context(text) in {'hypothetical', 'knowledge', 'resolved_past'}:
        return []
    return [m.group(0) for m in DENIED_REPORT.finditer(text)]


def current_clause(text: str) -> str:
    """Keep actual reports without letting another clause suppress a hazard."""
    text = normalize_chat_text(text)
    parts = re.split(r'[,.;!?]+|\b(?:nhưng|nhung|tuy nhiên|tuy nhien)\b', text, flags=re.I)
    actual = []
    inherited = None
    for part in parts:
        lower = normalized(part.strip())
        if not lower:
            continue
        if re.search(r'\b(neu|gia su|lo nhu|co the bi|truong hop xe)\b', lower):
            inherited = 'hypothetical'
            continue
        if re.search(r'\b(hom qua|thang truoc|tuan truoc|lan truoc|truoc day|da tung|tung bi)\b', lower):
            inherited = 'past'
            continue
        fresh = bool(re.search(r'\b(dang|vua|hom nay|bay gio|hien tai|gio lai|xe toi|xe em)\b', lower))
        # A denied individual symptom cannot resolve another current hazard.
        if re.search(r'\bkhong con\b', lower):
            continue
        if re.search(r'\b(da het|het roi|da khac phuc|(?:gio|bay gio|hien tai)\s+(?:da\s+)?(?:het|binh thuong))\b', lower):
            actual.clear()
            inherited = 'resolved'
            continue
        if inherited and not fresh:
            continue
        inherited = None
        actual.append(part.strip())
    return ', '.join(actual) if actual else text


def temporal_context(text: str) -> Literal['current', 'resolved_past', 'hypothetical', 'knowledge', 'uncertain']:
    lower = normalized(current_clause(text))
    past = bool(re.search(r'\b(hom qua|thang truoc|tuan truoc|lan truoc|truoc day|da tung|tung bi)\b', lower))
    resolved = bool(re.search(r'\b((?:gio|bay gio|hien tai)\s+(?:da\s+)?(?:het|binh thuong|khong con)|da het|het roi|da khac phuc)\b', lower))
    if resolved or (past and not re.search(r'\b(bay gio|hien tai|gio lai|van dang|hom nay)\b', lower)):
        return 'resolved_past'
    if re.search(r'\b(neu|gia su|lo nhu|co the bi|truong hop xe)\b', lower):
        return 'hypothetical'
    if re.search(r'\b(?:co phai\b.*?\b(?:khong|dung khong|phai khong)|co dung\b.*?\bkhong)\b', lower):
        return 'knowledge'
    if re.search(r'\b(?:co\s+duoc\s+bao\s+hanh\s+khong|chinh\s+sach\s+bao\s+hanh|quy\s+dinh\s+bao\s+hanh|co\s+bao\s+hanh\s+khong)\b', lower) and not re.search(r'\b(dang|vua|xe toi|xe em|bay gio)\b', lower):
        return 'knowledge'
    if re.search(r'\b(nghia la gi|y nghia|la gi|tim hieu)\b', lower) and not re.search(r'\b(dang|vua|xe toi|xe cua toi|bay gio)\b', lower):
        return 'knowledge'
    if re.search(r'\b(dang|vua|bay gio|xe toi|xe em|khong (?:sac|chay|di|khoi dong|di chuyen))\b', lower):
        return 'current'
    return 'uncertain'


@dataclass(frozen=True)
class ChatClassification:
    temporal_context: str
    request_kind: str
    is_critical: bool
    safety_rule: str | None
    needs_clarification: bool


def classify_chat_context(text: str, previous: dict | None = None) -> ChatClassification:
    # Local imports keep the temporal helpers available to guardrails and triage.
    from src.agents.guardrails import evaluate_hard_safety
    from src.agents.nodes.triage_node import classify_request_kind
    critical, rule, _ = evaluate_hard_safety(text)
    kind = classify_request_kind(text)
    return ChatClassification(temporal_context(text), kind, critical, rule, kind == 'incident' and not critical)
