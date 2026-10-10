"""Grounded, goal-scoped context shared by sales, knowledge and case turns."""
import re
from typing import Literal

from pydantic import BaseModel, Field

from src.agents.guardrails import strip_accents
from src.services.chat_classification import classify_chat_context

Move = Literal['new_question', 'elaborate', 'supply_info', 'correct', 'verify_claim',
               'ask_status', 'ask_next_step', 'request_action', 'cancel_intent', 'new_incident']


class ConversationFact(BaseModel):
    value: str | None = None
    source_turn: int
    status: Literal['confirmed', 'unknown', 'retracted'] = 'confirmed'


class ConversationContext(BaseModel):
    schema_version: int = 1
    active_goal: str | None = None
    topic: str = ''
    subject: str | None = None
    facts: dict[str, ConversationFact] = Field(default_factory=dict)
    pending_question: dict = Field(default_factory=dict)
    last_answer: list[dict] = Field(default_factory=list)
    action: dict = Field(default_factory=dict)


class TurnUnderstanding(BaseModel):
    move: Move = 'new_question'
    goal: str | None = None
    topic: str = ''
    subject: str | None = None
    updates: dict[str, str | None] = Field(default_factory=dict)
    retracted_fields: list[str] = Field(default_factory=list)
    needs_confirmation: bool = False
    original_text: str
    resolved_query: str


class ContextualMove(BaseModel):
    move: Move
    continues_goal: bool


def normalized(text: str) -> str:
    return strip_accents(text.casefold()).replace('đ', 'd')


def user_updates(text: str) -> dict[str, str | None]:
    """Only explicit customer observations; never extract assistant claims."""
    lower = normalized(text)
    updates = {}
    model = re.search(r'\bvf\s*(e34|[356789])\b', lower)
    if model:
        updates['model'] = 'VF' + model[1].upper()
    version = re.search(r'\b(plus|eco)\b', lower)
    if version:
        updates['version'] = version[1].title()
    if re.search(r'mua (?:kem|dut|ca|luon) pin|kem pin', lower):
        updates['battery'] = 'mua kèm pin'
    elif 'thue pin' in lower:
        updates['battery'] = 'thuê pin'
    if 'ha noi' in lower:
        updates['city'] = 'Hà Nội'
    elif re.search(r'ho chi minh|\bhcm\b|sai gon', lower):
        updates['city'] = 'TP. Hồ Chí Minh'
    elif 'da nang' in lower:
        updates['city'] = 'Đà Nẵng'
    else:
        locality = re.search(r'đăng ký(?: biển số)?\s+(?:ở|tại)\s+([^,.!?]{2,60})', text, re.I)
        if locality:
            updates['city'] = locality[1].strip()
    area = re.search(r'tôi ở\s+([^,.!?]{2,60})', text, re.I)
    if area and not any(city in normalized(area[1]) for city in ('ha noi', 'ho chi minh', 'da nang')):
        updates['area'] = area[1].strip()
    time_window = re.search(r'\b(?:sáng|chiều|tối|sang|chieu|toi)\s+(?:thứ bảy|chủ nhật|thu bay|chu nhat|\d{1,2}h)', text, re.I)
    if time_window:
        updates['time_window'] = time_window[0]
    if 'pin cao ap' in lower:
        updates['component'] = 'pin cao áp'
    elif re.search(r'ac quy|pin 12\s*v', lower):
        updates['component'] = 'ắc quy 12V'
    soc = re.search(r'(?:pin (?:con|o)|soc)\s*(\d{1,3})\s*%', lower)
    if soc and 0 <= int(soc[1]) <= 100:
        updates['soc'] = soc[1] + '%'
    error = re.search(r'\b(?:cc\d{2}|e\d{3}|p\d{4}|bms_\d{3})\b', lower)
    if error and not re.search(r'khong phai|khong con', lower):
        updates['error_code'] = error[0].upper()
    year = re.search(r'(?:doi|nam san xuat|xe nam)\s*(20\d{2})', lower)
    if year:
        updates['year'] = year[1]
    date = re.search(r'\b\d{1,2}/\d{1,2}(?:/\d{4})?\b|thu bay|chu nhat|ngay mai|hom nay', lower)
    if date:
        updates['date'] = date[0]
    for slot, pattern in {'version': 'phien ban', 'city': 'tinh|thanh|noi dang ky',
                          'battery': 'pin', 'year': 'doi xe|nam san xuat'}.items():
        if re.search(r'(?:khong biet|chua biet|khong nho).{0,25}(?:' + pattern + ')', lower):
            updates[slot] = None
    if re.search(r'(?:khong biet|chua biet|khong nho).{0,30}(?:eco|plus)', lower):
        updates['version'] = None
    if re.search(r'den.*(?:tat|het)|da an toan|khong con.*canh bao', lower):
        updates['reported_condition'] = 'khách báo cảnh báo đã hết/an toàn'
    return updates


async def understand_turn(text: str, context: ConversationContext, recent_turns: list[dict], budget: dict) -> TurnUnderstanding:
    lower = normalized(text)
    classification = classify_chat_context(text)
    updates = user_updates(text)
    goal = context.active_goal
    topic = context.topic
    explicit_goal = next((g for g, pattern in [
        ('quote', r'\bgia\b|lan banh|tra gop|uu dai'),
        ('test_drive', r'lai thu|chay thu'),
        ('maintenance', r'bao duong|dat lich dich vu'),
        ('warranty', r'bao hanh'),
        ('range', r'quang duong|di duoc|\bkm\b.*(?:dung|hay)|mot lan sac'),
        ('charging', r'sac.*(?:bao lau|thoi gian)|sac nhanh'),
        ('capacity', r'dung luong pin|\bkwh\b'),
        ('concept', r'\b(?:soh|soc|bms|abs|adas)\b'),
    ] if re.search(pattern, lower)), None)
    move: Move = 'new_question'
    ambiguous_reference = False
    actual_failure = classification.request_kind == 'incident'
    if classification.is_critical or classification.request_kind == 'incident':
        move, goal = 'new_incident', 'incident'
    if re.search(r'khong phai|y toi la|toi noi.*(?:chu|khong)|dinh chinh', lower) and not classification.is_critical and not actual_failure:
        move, goal = 'correct', context.active_goal
    elif re.search(r'\d+.*hay.*\d+|\d+.*\d+.*(?:nao dung|nao chinh xac)|so nao dung|con so.*dung|co chac|chinh xac khong', lower) and not classification.is_critical and not actual_failure:
        move, goal = 'verify_claim', context.active_goal
    elif move != 'new_incident':
        if re.search(r'(?:thoi|khong).*dat|huy.*(?:lich|y dinh)|khong muon.*nua', lower):
            move = 'cancel_intent'
        elif re.search(r'can lam gi|buoc tiep|lam gi tiep|gio.*lam sao|tiep theo', lower):
            move = 'ask_next_step'
        elif re.search(r'con thieu|da noi|da.*(?:tao|dat|gui).*chua|trang thai|tinh trang ho so|da co.*thong tin|co the.*(?:xac nhan|ho tro|kiem tra)|can them.*thong tin', lower):
            move = 'ask_status'
        elif re.search(r'dat.*(?:luon|ngay|duoc)|(?:tao|dat|dang ky).*giup|muon dat', lower):
            move = 'request_action'
        elif re.search(r'\b(?:sao|vi sao|tai sao)\b|giai thich|cach tinh|vi du|cu the hon', lower):
            move = 'elaborate'
        elif updates and goal:
            move = 'supply_info'
    if (move == 'new_question' and context.active_goal and not explicit_goal and not updates
            and len(text) < 180 and not re.search(r'thoi tiet|may bay|bong da|tesla|hyundai', lower)):
        from src.services.agent_llm import structured_call
        parsed = await structured_call({'latest_user_message': text, 'llm_budget': budget,
                                        'memory_summary': context.model_dump_json()[:2500] + '\n' + str(recent_turns[-4:])[:1800]},
                                       'conversation_turn', ContextualMove)
        if parsed and parsed.continues_goal and parsed.move != 'new_incident':
            move = parsed.move
        elif re.search(r'con .*thi sao|tu van tiep|tiep duoc|di tiep|con can.*kiem tra', lower):
            move = 'ask_next_step'
        elif not parsed and re.search(r'^(?:vay|the|no|cai do)\b|duoc khong', lower):
            move, ambiguous_reference = 'elaborate', True
    if move != 'new_incident' and explicit_goal:
        goal = explicit_goal
        if goal != context.active_goal or move == 'new_question':
            topic = text[:300]
    elif move == 'new_question' and not updates:
        goal, topic = None, ''
    subject = updates.get('model') or context.subject
    if move == 'new_incident' and context.active_goal != 'incident':
        # Interest in a car does not identify the vehicle reporting an incident.
        subject = updates.get('model')
    query = text
    if goal and move != 'new_incident':
        prefix = {'quote': 'Giá niêm yết và dự toán lăn bánh', 'test_drive': 'Đăng ký lái thử',
                  'maintenance': 'Đặt lịch bảo dưỡng', 'warranty': 'Bảo hành',
                  'range': 'Quãng đường một lần sạc', 'charging': 'Thời gian sạc',
                  'capacity': 'Dung lượng pin',
                  'concept': context.topic or topic}.get(goal, '')
        facts = {k: v.value for k, v in context.facts.items() if v.status == 'confirmed'}
        facts.update(updates)
        details = ' '.join(str(facts[k]) for k in ('version', 'battery', 'city', 'component', 'year') if facts.get(k))
        query = f'{prefix} {subject or ""} {details}. {text}'[:1000]
    retracted = []
    denied_code = re.search(r'(?:khong con|khong phai|het).*?\b(cc\d{2}|e\d{3}|p\d{4}|bms_\d{3})\b', lower)
    if denied_code and context.facts.get('error_code') and context.facts['error_code'].value == denied_code[1].upper():
        retracted.append('error_code')
    return TurnUnderstanding(move=move, goal=goal, topic=topic, subject=subject, updates=updates, retracted_fields=retracted,
                             original_text=text, resolved_query=query,
                             needs_confirmation=ambiguous_reference or bool(goal and not explicit_goal and move == 'new_question'))


def apply_turn(context: ConversationContext, turn: TurnUnderstanding, turn_number: int) -> ConversationContext:
    result = context.model_copy(deep=True)
    if turn.goal != result.active_goal:
        result.facts = {}
        result.pending_question = {}
        result.action = {}
    if turn.subject != result.subject:
        for key in ('version', 'battery', 'year', 'component'):
            result.facts.pop(key, None)
        result.last_answer = []
    result.active_goal, result.topic, result.subject = turn.goal, turn.topic, turn.subject
    if result.action.get('state') == 'cancelled_intent' and turn.move in {'new_question', 'request_action'}:
        result.action = {}
    if turn.move == 'new_incident':
        result.facts.pop('reported_condition', None)
    for key in turn.retracted_fields:
        result.facts[key] = ConversationFact(value=None, source_turn=turn_number, status='retracted')
    for key, value in turn.updates.items():
        result.facts[key] = ConversationFact(value=value, source_turn=turn_number,
                                              status='confirmed' if value is not None else 'unknown')
    if turn.move == 'cancel_intent':
        result.action = {'state': 'cancelled_intent'}
        result.pending_question = {}
    return result
