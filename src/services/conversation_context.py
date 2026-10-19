"""Grounded, goal-scoped context shared by sales, knowledge and case turns."""
import re
from typing import Literal

from pydantic import BaseModel, Field

from src.agents.guardrails import strip_accents
from src.services.chat_classification import classify_chat_context
from src.services.chat_normalization import normalize_chat_text

Move = Literal['new_question', 'elaborate', 'supply_info', 'correct', 'verify_claim',
               'ask_status', 'ask_next_step', 'request_action', 'cancel_intent', 'new_incident']


class ConversationFact(BaseModel):
    value: str | None = None
    source_turn: int
    status: Literal['confirmed', 'unknown', 'retracted'] = 'confirmed'


class ConversationContext(BaseModel):
    preferred_language: Literal['vi', 'en'] = 'vi'
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
    request_kind: Literal['faq', 'incident', 'complaint', 'oos', 'uncertain'] = 'uncertain'
    cost_subject: Literal['vehicle_purchase', 'charging', 'battery_rental', 'maintenance', 'repair'] | None = None
    source_need: Literal['catalog', 'policy', 'manual', 'guide'] | None = None
    updates: dict[str, str | None] = Field(default_factory=dict)
    retracted_fields: list[str] = Field(default_factory=list)
    needs_confirmation: bool = False
    original_text: str
    resolved_query: str


class ContextualMove(BaseModel):
    move: Move
    continues_goal: bool


def normalized(text: str) -> str:
    return strip_accents(normalize_chat_text(text).casefold()).replace('đ', 'd')


def user_updates(text: str) -> dict[str, str | None]:
    """Only explicit customer observations; never extract assistant claims."""
    text = normalize_chat_text(text)
    lower = normalized(text)
    # A correction may mention the rejected value before or after its replacement.
    slot_value = (r'(?:xe\s+)?vf\s*(?:e34|[356789])(?:\s+(?:(?:phien ban|ban)\s+)?(?:plus|eco)(?:\s+(?:awd|fwd))?)?'
                  r'|(?:phien ban\s+|ban\s+)?(?:plus|eco)'
                  r'|ha noi|(?:tp\.?\s*)?(?:ho chi minh|hcm)|sai gon|da nang'
                  r'|pin cao ap|ac quy(?:\s+12\s*v)?|pin 12\s*v'
                  r'|(?:doi|nam san xuat|xe nam)\s*20\d{2}|mua (?:kem|dut|ca|luon) pin|thue pin')
    lower = re.sub(r'\b(?:chu khong phai|khong phai)\s+(?:' + slot_value + r')\b', '', lower)
    lower = re.sub(r'\bkhong\s+(?:mua (?:kem|dut|ca|luon) pin|thue pin)\b', '', lower)
    updates = {}
    model = re.search(r'\bvf\s*(e34|[356789])\b', lower)
    if model:
        updates['model'] = 'VF' + model[1].upper()
    version = re.search(r'\b((?:plus|eco)(?:\s+(?:awd|fwd))?)\b', lower)
    if version:
        updates['version'] = version[1].title().replace('Awd', 'AWD').replace('Fwd', 'FWD')
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
    relative_time = re.search(r'\b(sang|chieu|toi)\s+(?:ngay\s+)?mai\b', lower)
    if relative_time:
        updates['time_window'] = {'sang': 'sáng', 'chieu': 'chiều', 'toi': 'tối'}[relative_time[1]]
    if 'pin cao ap' in lower:
        updates['component'] = 'pin cao áp'
    elif re.search(r'ac quy|pin 12\s*v', lower):
        updates['component'] = 'ắc quy 12V'
    soc = re.search(r'(?:pin (?:con|o)|soc)\s*(\d{1,3})\s*%', lower)
    if soc and 0 <= int(soc[1]) <= 100:
        updates['soc'] = soc[1] + '%'
    from src.services.chat_classification import without_denied_reports
    error = re.search(r'\b(?:cc\d{2}|e\d{3}|p\d{4}|bms_\d{3})\b', normalized(without_denied_reports(text)))
    if error:
        updates['error_code'] = error[0].upper()
    year = re.search(r'(?:doi|nam san xuat|xe nam)\s*(20\d{2})', lower)
    if year:
        updates['year'] = year[1]
    date = re.search(r'\b\d{1,2}/\d{1,2}(?:/\d{4})?\b|thu bay|chu nhat|ngay mai|hom nay', lower)
    if date:
        updates['date'] = date[0]
    elif relative_time:
        updates['date'] = 'ngay mai'
    for slot, pattern in {'version': 'phien ban', 'city': 'tinh|thanh|noi dang ky',
                          'battery': 'pin', 'year': 'doi xe|nam san xuat'}.items():
        if re.search(r'(?:khong biet|chua biet|khong nho).{0,25}(?:' + pattern + ')', lower):
            updates[slot] = None
    if re.search(r'(?:khong biet|chua biet|khong nho).{0,30}(?:eco|plus)', lower):
        updates['version'] = None
    if re.search(r'den.*(?:tat|het)|khong con.*canh bao', lower):
        updates['reported_condition'] = 'khách báo cảnh báo đã hết'
    if re.search(r'da (?:o noi )?an toan', lower):
        updates['reported_condition'] = 'khách báo đã ở nơi an toàn'
    return updates


def cost_subject_for(text: str) -> str | None:
    lower = normalized(text)
    return next((cost for cost, pattern in [
        ('battery_rental', r'thue pin'),
        ('maintenance', r'\b(?:gia|phi|tien)\b.{0,20}bao duong|bao duong.{0,35}\b(?:gia|phi|tien|chi phi)\b'),
        ('repair', r'\b(?:gia|phi|tien)\b.{0,20}(?:sua|thay|phu tung)|(?:sua chua|thay pin|thay lop|phu tung).{0,35}\b(?:gia|phi|tien|chi phi)\b'),
        ('charging', r'\b(?:gia|phi|tien|chi phi)\b.{0,25}(?:sac|nap dien)|(?:sac|nap dien).{0,35}\b(?:gia|phi|tien|chi phi|tinh phi)\b'),
        ('vehicle_purchase', r'(?<!danh )\bgia\b|lan banh|tra gop|uu dai|mua.{0,60}bao nhieu tien'),
    ] if re.search(pattern, lower)), None)


async def understand_turn(text: str, context: ConversationContext, recent_turns: list[dict], budget: dict) -> TurnUnderstanding:
    original_text = text
    text = normalize_chat_text(text)
    from src.services.vehicle_catalog import is_generic_vehicle_comparison
    trim_comparison = re.fullmatch(r'\s*so(?: sanh)? (?:phien )?ban (plus|eco)\s*[.!?]?\s*', normalized(text))
    if trim_comparison and context.active_goal == 'overview':
        version = trim_comparison[1].title()
        if is_generic_vehicle_comparison(context.topic):
            models = re.findall(r'\bvf\s*[356789]\b', normalized(context.topic))
            if len(set(model.replace(' ', '') for model in models)) == 2:
                text = 'So sánh ' + ' với '.join(f'{model.upper()} {version}' for model in models)
    # Resolve the comparison before replacing the previous subject.
    comparison = re.fullmatch(r'\s*(?:so sanh(?:\s+(?:xe nay|xe do|voi))?|so voi)\s+(vf\s*[356789])\s*[.!?]?\s*', normalized(text))
    if (comparison and context.subject and context.active_goal in {'overview', 'quote', 'range', 'capacity', 'test_drive'}
            and comparison[1].replace(' ', '').upper() != context.subject):
        text = f'So sánh {context.subject} với {comparison[1].upper()}'
    lower = normalized(text)
    classification = classify_chat_context(text)
    updates = user_updates(text)
    if context.active_goal == 'incident':
        from src.agents.nodes.triage_node import extract_fields
        incident_slots = extract_fields(text)
        updates.update({key: value for key, value in incident_slots.items()
                        if key in {'charger_id', 'station_location', 'current_location'}})
    retracted = []
    for key, fact in context.facts.items():
        if fact.status != 'confirmed' or not fact.value or key in updates:
            continue
        value = re.escape(normalized(fact.value))
        if key == 'model':
            value = value.replace('vf', r'vf\s*')
        if re.search(r'\b(?:chu khong phai|khong phai|khong)\s+'
                     r'(?:(?:doi|nam san xuat|xe nam)\s+)?' + value + r'\b', lower):
            retracted.append(key)
    denied_code = re.search(r'(?:khong con|khong phai|het).*?\b(cc\d{2}|e\d{3}|p\d{4}|bms_\d{3})\b', lower)
    if denied_code and context.facts.get('error_code') and context.facts['error_code'].value == denied_code[1].upper():
        if 'error_code' not in retracted:
            retracted.append('error_code')
    goal = context.active_goal
    topic = context.topic
    cost_subject = cost_subject_for(text)
    explicit_goal = next((g for g, pattern in [
        ('application', r'ung dung|\bapp\b|dang nhap|mat khau'),
        ('charging_network', r'tram sac|diem sac|tru sac.*(?:dau|tim|trong)|thue pin'),
        ('quote', r'(?<!danh )\bgia\b|lan banh|tra gop|uu dai|mua.{0,60}bao nhieu tien'),
        ('test_drive', r'lai thu|chay thu|trai nghiem lai'),
        ('maintenance', r'bao duong|dat lich dich vu|hen kiem tra dinh ky|dat (?:lich|hen).{0,20}sua (?:xe|chua)'),
        ('warranty', r'bao hanh'),
        ('range', r'quang duong|di duoc|di bao xa|chay duoc bao xa|tam hoat dong|tam di chuyen|\bkm\b.*(?:dung|hay)|mot lan sac'),
        ('charging', r'sac.*(?:bao lau|thoi gian|may phut)|bao lau.*sac|thoi gian (?:sac|nap)|sac nhanh'),
        ('capacity', r'dung luong pin|suc chua|chua duoc.*dien|\bkwh\b'),
        ('appearance', r'\bmau\s+(?:xe|gi|nao|sac|ngoai that|noi that)\b|\bco mau\b|bang mau|tuy chon mau'),
        ('concept', r'\b(?:soh|soc|bms|abs|adas)\b'),
    ] if re.search(pattern, lower) and not (g == 'appearance' and 'mẫu' in text.casefold() and 'màu' not in text.casefold())), None)
    if cost_subject in {'charging', 'battery_rental'}:
        explicit_goal = 'charging_network'
    elif cost_subject in {'repair', 'maintenance'}:
        explicit_goal = 'maintenance'
    if (context.active_goal == 'quote' and 'battery' in updates
            and explicit_goal in {None, 'quote', 'charging_network'}
            and not re.search(r'\b(?:gia|phi|tien|bao nhieu|chinh sach|dieu kien|huong dan|tram sac|ung dung|app|tim hieu|dich vu|giai thich)\b', lower)):
        cost_subject, explicit_goal = 'vehicle_purchase', 'quote'
    if (context.active_goal == 'incident' and explicit_goal == 'charging_network'
            and 'station_location' in updates and classification.request_kind == 'uncertain'
            and not re.search(r'\b(?:tim|huong dan|cach|o dau|gan|phi|gia|la gi|bao nhieu)\b', lower)):
        explicit_goal = None
    if classification.request_kind == 'complaint':
        explicit_goal = 'complaint'
    if re.search(r'thoi tiet|nau pho|bai tap toan|tesla|hyundai', lower):
        explicit_goal = 'out_of_scope'
    from src.services.vehicle_card_intent import is_generic_vehicle_overview, is_general_vehicle_advice
    if is_general_vehicle_advice(text) or (not explicit_goal and is_generic_vehicle_overview(text)):
        explicit_goal = 'overview'
        topic = text[:300]
    if is_generic_vehicle_comparison(text) and not re.search(r'khong phai|dinh chinh', lower):
        explicit_goal = 'overview'
        topic = text[:300]
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
        if (classification.temporal_context in {'hypothetical', 'resolved_past'}
                and context.active_goal != 'incident' and not explicit_goal
                and (updates.get('model') or re.search(r'\b(?:phanh|khoi|chay|loi|hong)\b', lower))):
            move, goal, topic = 'new_question', None, ''
        elif re.search(r'(?:thoi|khong).*dat|huy.*(?:lich|y dinh)|khong muon.*nua', lower):
            move = 'cancel_intent'
        elif re.search(r'can lam gi|buoc tiep|lam gi tiep|gio.*lam sao|tiep theo', lower):
            move = 'ask_next_step'
        elif re.search(r'con thieu|da noi|da.*(?:tao|dat|gui).*chua|trang thai|tinh trang ho so|da co.*thong tin|co the.*(?:xac nhan|ho tro|kiem tra)|can them.*thong tin', lower):
            move = 'ask_status'
        elif re.search(r'dat.*(?:luon|ngay|duoc)|(?:tao|dat|dang ky).*giup|muon dat', lower):
            move = 'request_action'
        elif explicit_goal == 'concept' and context.active_goal == 'concept' and re.match(r'^(?:no|cai do|he thong do)\b', lower):
            move = 'elaborate'
        elif context.active_goal == 'warranty' and re.search(r'ap dung cho|chay dich vu|su dung kinh doanh', lower) and not explicit_goal:
            move = 'elaborate'
        elif explicit_goal and explicit_goal != context.active_goal:
            # A named model/trim in a new question is not a quote slot answer.
            move = 'new_question'
        elif (context.active_goal == 'incident' and not explicit_goal
              and re.fullmatch(r'(?:toi|minh|em|xe)?\s*da\s+(?:dung(?: xe)?|do(?: xe)?|o)\s+(?:o\s+)?noi an toan[.!?\s]*', lower)):
            move = 'supply_info'
        elif re.search(r'\b(?:sao|vi sao|tai sao)\b|giai thich|cach tinh|vi du|cu the hon', lower):
            move = 'elaborate'
        elif (updates or retracted) and goal:
            if re.search(r'\b(?:nhu the nao|nhu nao|la dong|la xe gi|la xe nhu the nao)\b', lower):
                move = 'new_question'
                goal = None
            else:
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
    if (explicit_goal in {'application', 'charging_network', 'warranty', 'maintenance', 'concept'}
            and move == 'new_question' and not updates.get('model')
            and not re.search(r'xe (?:toi|cua toi|nay|do)|cua xe|cua toi', lower)):
        subject = None
    if 'model' in retracted:
        subject = None
    if move == 'new_incident' and context.active_goal != 'incident':
        # Interest in a car does not identify the vehicle reporting an incident.
        subject = updates.get('model')
    query = text
    from src.services.faq_questions import faq_parts
    if goal and move not in {'new_incident', 'new_question'} and not is_generic_vehicle_comparison(text) and not faq_parts(text):
        prefix = {'quote': 'Giá niêm yết và dự toán lăn bánh', 'test_drive': 'Đăng ký lái thử',
                  'maintenance': 'Bảo dưỡng', 'warranty': 'Bảo hành',
                  'range': 'Quãng đường một lần sạc', 'charging': 'Thời gian sạc',
                  'capacity': 'Dung lượng pin',
                  'appearance': 'Màu sắc xe',
                  'concept': context.topic if move != 'new_question' and context.active_goal == 'concept' else topic,
                  'application': 'Hướng dẫn ứng dụng VinFast',
                  'charging_network': 'Chi phí sạc' if cost_subject == 'charging' else 'Thuê pin' if cost_subject == 'battery_rental' else 'Mạng lưới trạm sạc'}.get(goal, '')
        facts = {k: v.value for k, v in context.facts.items()
                 if v.status == 'confirmed' and k not in retracted
                 and goal == context.active_goal and subject == context.subject}
        facts.update(updates)
        details = ' '.join(str(facts[k]) for k in ('version', 'battery', 'city', 'component', 'year') if facts.get(k))
        query = f'{prefix} {subject or ""} {details}. {text}'[:1000]
        if goal == 'concept':
            query = (f'{context.topic}. {text}' if move != 'new_question' and context.active_goal == 'concept' else text)[:1000]
    source_need = ('guide' if goal == 'application' or re.search(r'huong dan|cach (?:dat|su dung|tim)', lower)
                   else 'policy' if goal in {'warranty', 'charging_network'} or cost_subject in {'maintenance', 'repair'}
                   else 'manual' if goal in {'charging', 'incident'} or re.search(r'adas|canh bao', lower) and updates.get('model')
                   else 'catalog' if goal in {'overview', 'range', 'capacity', 'quote', 'test_drive', 'appearance'} else None)
    if goal == 'maintenance' and cost_subject not in {'maintenance', 'repair'}:
        source_need = 'guide' if re.search(r'dat lich|dat hen|dang ky|hen kiem tra', lower) else 'manual'
    return TurnUnderstanding(move=move, goal=goal, topic=topic, subject=subject, updates=updates, retracted_fields=retracted,
                             request_kind=classification.request_kind, cost_subject=cost_subject, source_need=source_need,
                             original_text=original_text, resolved_query=query,
                             needs_confirmation=ambiguous_reference or bool(goal and not explicit_goal and move == 'new_question'))


def apply_turn(context: ConversationContext, turn: TurnUnderstanding, turn_number: int) -> ConversationContext:
    result = context.model_copy(deep=True)
    if turn.goal != result.active_goal:
        result.facts = {}
        result.pending_question = {}
        result.action = {}
        result.last_answer = []
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
