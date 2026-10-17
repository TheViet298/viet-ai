"""Presentation translation after business decisions and evidence verification.

The canonical Vietnamese answer remains the evidence boundary. A translation
cannot change database receipts, safety flags, citations or structured facts.
"""
import json
import re

from pydantic import BaseModel

from src.services.agent_llm import structured_call
from src.services.chat_language import protect_literals, restore_literals


class Translation(BaseModel):
    text: str


class BatchTranslation(BaseModel):
    texts: list[str]


ENGLISH_SAFETY = (
    'Your safety comes first. If you are driving, move to a safe place and stop only if you can do so safely. '
    'Keep away from the vehicle if there is smoke or fire, and keep others away. '
    'Do not touch the battery, high-voltage wiring or charging connector. '
    'Contact local emergency services if there is immediate danger, and contact VinFast roadside assistance on 1900-232389. '
    'Do not continue driving until qualified personnel have assessed the vehicle.'
)


async def translate(text: str, target: str, budget: dict, *, many: bool = False) -> str | None:
    if many:
        try:
            source = json.loads(text)
        except (ValueError, TypeError):
            return None
        if not isinstance(source, list) or not all(isinstance(item, str) for item in source):
            return None
        tokens = {}
        # Mask real text, before JSON escapes turn newline boundaries into words.
        masked = json.dumps([protect_literals(item, tokens=tokens)[0] for item in source], ensure_ascii=False)
    else:
        masked, tokens = protect_literals(text)
    parsed = await structured_call({'latest_user_message': masked,
        'memory_summary': {'target_language': target}, 'llm_budget': budget},
        'customer_translation', BatchTranslation if many else Translation)
    if not isinstance(parsed, BatchTranslation if many else Translation):
        return None
    rendered = json.dumps(parsed.texts, ensure_ascii=False) if many else parsed.text
    try:
        # All source numbers are protected; any new number is an added fact.
        without_tokens = re.sub(r'__LITERAL_\d+__', '', rendered)
        if re.search(r'\d', without_tokens):
            return None
        if target == 'en' and re.search(r'Quý khách|theo tài liệu|màu sắc|phiên bản|bảo hành|bảo dưỡng|được|chưa|không|quãng đường|câu hỏi', without_tokens, re.I):
            return None
        if target == 'en' and re.search(
            r'\b(?:booking|appointment|test drive)\b.{0,55}\b(?:is confirmed|has been confirmed|is booked|has been booked|is scheduled)\b'
            r'|\b(?:I|we)\s+(?:have\s+)?(?:booked|scheduled|arranged|forwarded|dispatched)\b'
            r'|\b(?:I|we|a specialist)\s+will\s+(?:call|contact|arrange|book|forward|dispatch)\b', rendered, re.I):
            return None
        replacements = {key: json.dumps(value, ensure_ascii=False)[1:-1] for key, value in tokens.items()} if many else tokens
        if target == 'en':
            # Edit observed wording before restoring protected source facts.
            for original, edited in [
                ('tabs above', 'cards above'), ('service centre', 'service center'),
                ('I am very sorry for your inconvenient experience.', 'I’m sorry about your experience.'),
                ('I cannot guide high-voltage battery interventions',
                 'I cannot provide instructions for work on the high-voltage battery'),
            ]:
                rendered = rendered.replace(original, edited)
        return restore_literals(rendered, replacements)
    except ValueError:
        return None


async def canonical_input(text: str, language: str, budget: dict) -> str:
    from src.services.chat_language import canonical_query, needs_semantic_translation
    if language != 'en':
        return text
    mapped = canonical_query(text)
    from src.agents.guardrails import evaluate_hard_safety
    if evaluate_hard_safety(text)[0] or not needs_semantic_translation(mapped):
        return mapped
    # Fail closed on an untranslated intent; do not send an unknown English
    # question down the ungrounded general-generation branch.
    return await translate(text, 'vi', budget) or 'Vui lòng làm rõ câu hỏi về VinFast.'


def english_snapshot(cards, comparison: bool) -> str:
    lines = ['Here is a comparison of the requested versions:' if comparison else 'Here are the available versions:']
    labels = {'Số chỗ ngồi': 'Seats', 'Quãng đường': 'Range', 'Thời gian sạc': 'Fast charging',
              'Công suất tối đa': 'Maximum power'}
    for card in cards:
        specs = '; '.join(f'{labels.get(s.label, s.label)}: {english_spec(s.value)}' for s in card.specs)
        if comparison and card.battery_capacity:
            specs += '; Usable battery capacity: ' + english_spec(card.battery_capacity)
        lines.append(f'- **{card.name}** — {english_spec(card.price_label)}. {specs}.')
    if comparison:
        lines.append('NEDC and WLTP figures use different test standards and should not be compared directly.')
    lines.append('Actual range depends on operating conditions. These are listed prices, not on-road prices. '
                 'Please confirm the applicable configuration and purchase conditions with a showroom.')
    return '\n\n'.join(lines)


def english_spec(value: str) -> str:
    relative_dates = {'ngay mai': 'tomorrow', 'hom nay': 'today', 'thu bay': 'Saturday',
                      'chu nhat': 'Sunday', 'sáng': 'morning', 'chiều': 'afternoon', 'tối': 'evening'}
    if value.casefold().strip() in relative_dates:
        return relative_dates[value.casefold().strip()]
    for source, target in [('Giá bán từ', 'From'), ('Giá từ', 'From'), ('Từ ', 'From '), ('Chưa có giá xác thực', 'Price not yet verified'), ('Liên hệ', 'Contact showroom'),
                            ('Chưa công bố', 'Not published'), ('chưa công bố', 'Not published'),
                            ('phút', 'minutes'), ('từ ', 'from '), ('chỗ', 'seats')]:
        value = value.replace(source, target)
    return value


async def localize_response(data, language: str, budget: dict, *, snapshot: bool = False, operational=None, conversation=None):
    data.language = language
    data.message = data.message.replace('\\n', '\n').replace('sạccông cộng', 'sạc công cộng')
    if language != 'en':
        return
    if data.service_handoff and data.service_handoff.app_feature_name == 'Đặt lịch dịch vụ / Tra cứu':
        data.service_handoff.app_feature_name = 'Service booking / Information lookup'
    if data.priority == 'CRITICAL' or data.emergency_context:
        data.safe_guidance = ENGLISH_SAFETY
        receipt = f' Support case {data.case_id} has been recorded.' if data.case_id else ' Sign in to create and track a support case.'
        status = {'New': 'newly received', 'Needs Information': 'awaiting additional information',
                  'Staff Reviewing': 'awaiting staff review', 'In Progress': 'in progress',
                  'Resolved': 'resolved', 'Closed': 'closed', 'Reopened': 'reopened'}.get(data.status)
        if data.case_id and status:
            receipt += f' Its current status is {status}.'
        reported = conversation.facts.get('reported_condition') if conversation else None
        acknowledgment = ''
        if reported and reported.status == 'confirmed':
            acknowledgment = {
                'khách báo đã ở nơi an toàn': 'I have noted that you reported being in a safe place. ',
                'khách báo cảnh báo đã hết': 'I have noted that you reported that the warning has cleared. ',
            }.get(reported.value, 'I have noted your update about the situation. ')
            acknowledgment += 'This does not confirm that the vehicle is safe to drive. '
        persisted_status = data.emergency_context.safety_status if data.emergency_context else data.safety_status
        if persisted_status == 'customer_reported_safe':
            acknowledgment += 'Your safety confirmation has been saved; a technical assessment is still required. '
        elif reported and reported.status == 'confirmed':
            acknowledgment += 'Your safety confirmation has not yet been saved; please use the safety confirmation button. '
        data.message = acknowledgment + ENGLISH_SAFETY + receipt
        if data.request_location:
            data.message += ' Please share your current location when it is safe to do so.'
        data.suggested_replies = []
        return
    if operational is not None:
        data.message = ('No appointment has been booked through this chat. '
            'You can register through the VinFast app or contact a showroom/service center to confirm availability.')
        known = operational.known_facts
        preferences = [english_spec(known[k]) for k in ('model', 'version', 'city', 'date', 'time_window') if known.get(k)]
        if preferences:
            data.message += ' Preferences shared: ' + ', '.join(preferences) + '.'
        labels = {'city': 'a convenient location', 'date': 'your preferred date', 'exact_date': 'the exact day, month and year'}
        missing = [labels[k] for k in operational.missing_fields if k in labels]
        if missing:
            data.message += ' Please provide ' + ' and '.join(missing) + ' when registering.'
        if operational.state == 'cancelled_intent':
            data.message = ('I have stopped collecting preferences for this request in our conversation. '
                'Any appointment made outside this chat must be cancelled where it was booked.')
        data.suggested_replies = []
    elif 'CẢNH BÁO AN TOÀN CAO ÁP' in data.message:
        data.message = ('For your safety, do not dismantle, open or touch the high-voltage battery or wiring. '
            'Keep a safe distance and contact qualified VinFast technicians. I cannot provide instructions for this work.')
        data.safe_guidance = data.message
        data.suggested_replies = []
    elif data.message.startswith('Đây là hướng dẫn an toàn chung cho tình huống giả định'):
        data.message = ('This is general safety guidance for a hypothetical situation, '
                        'not confirmation of a current incident. ' + ENGLISH_SAFETY)
        data.suggested_replies = []
    elif data.message.startswith('Dạ chào Quý khách!'):
        data.message = 'Hello! I’m the VFServ assistant. How can I help you today?'
        data.suggested_replies = ['Vehicle advice', 'Charging stations & app', 'Warranty & maintenance', 'Report a technical issue']
    elif data.message.startswith('Chào Quý khách! Em là Trợ lý CSKH VinFast (VFServ). Em có thể hỗ trợ'):
        data.message = ('I can help you explore VinFast vehicles, check warranty and maintenance information, '
            'find charging and app guidance, report technical issues or complaints, and track your support cases. '
            'What would you like help with?')
        data.suggested_replies = ['Vehicle advice', 'Charging stations & app', 'Warranty & maintenance', 'Report a technical issue']
    elif data.suggested_replies == ['Tư vấn xe VF3', 'Tư vấn xe VF8'] and not data.vehicle_cards:
        data.message = ('VinFast offers the VF3, VF5, VF6, VF7, VF8 and VF9 electric vehicle ranges. '
            'I can introduce each model, its versions and list prices, and help you explore test-drive options. '
            'Which model would you like to know more about?')
        data.suggested_replies = ['Tell me about VF3', 'Tell me about VF8']
    elif snapshot and data.vehicle_cards:
        data.message = english_snapshot(data.vehicle_cards, data.vehicle_comparison)
        data.suggested_replies = ['Estimate on-road price for ' + c.name for c in data.vehicle_cards]
        if data.vehicle_comparison:
            data.suggested_replies = []
    elif data.message == 'Dạ, rất vui được hỗ trợ Quý khách. Khi cần thêm thông tin, Quý khách cứ nhắn em nhé.':
        data.message = 'You’re welcome. Feel free to ask if you need any more help.'
        data.suggested_replies = []
    else:
        source = [data.message, *(data.suggested_replies or [])]
        if data.safe_guidance:
            source.append(data.safe_guidance)
        translated = await translate(json.dumps(source, ensure_ascii=False), 'en', budget, many=True)
        try:
            values = json.loads(translated) if translated else None
            if not isinstance(values, list) or len(values) != len(source) or not all(isinstance(x, str) and x.strip() for x in values):
                raise ValueError('Invalid translation shape')
            data.message = values[0].replace('\\n', '\n')
            data.suggested_replies = values[1:1 + len(data.suggested_replies or [])]
            if data.safe_guidance:
                data.safe_guidance = values[-1].replace('\\n', '\n')
        except (ValueError, TypeError):
            budget['presentation_failed'] = True
            data.message = ('I could not prepare a reliable English answer to this question. '
                            'Please try again or contact a VinFast specialist for help.')
            if data.case_id:
                data.message += f' Your support case reference is {data.case_id}.'
            data.suggested_replies = []
            data.safe_guidance = None
    labels = {'Số chỗ ngồi': 'Seats', 'Quãng đường': 'Range', 'Thời gian sạc': 'Fast charging', 'Công suất tối đa': 'Maximum power'}
    for card in data.vehicle_cards:
        card.price_label = english_spec(card.price_label)
        if card.fast_charge_time:
            card.fast_charge_time = english_spec(card.fast_charge_time)
        for spec in card.specs:
            spec.label = labels.get(spec.label, spec.label)
            spec.value = english_spec(spec.value)
