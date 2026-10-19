"""Own, serialize and atomically persist application chat turns."""
import asyncio
import hashlib
import json
import logging
import re
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from weakref import WeakValueDictionary

from fastapi import HTTPException
from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError

from src.agents.guardrails import sanitize_pii
from src.models.db_models import Case, CaseBrief, ChatRequestRecord, ChatSession, Message
from src.models.schemas import ApiResponse, ChatResponseData, EmergencyContext
from src.services.application_memory import accept_application_memory
from src.services.chat_cases import resolve_authorized_active_case
from src.services.chat_normalization import normalize_message
from src.services.conversation_context import ConversationContext, TurnUnderstanding, apply_turn, understand_turn
from src.services.conversation_progress import derive_progress
from src.services.observability import observation
from src.services.request_diagnostics import observed_lock
from src.services.session_store import encode_state, get_store

_LOCKS: WeakValueDictionary = WeakValueDictionary()
logger = logging.getLogger("chat_turns")


def safety_fields(case: Case) -> dict:
    timestamp = case.safety_acknowledged_at
    return {'safety_status': case.safety_status, 'incident_version': case.incident_version,
            'safety_acknowledged_at': timestamp.replace(tzinfo=UTC).isoformat() if timestamp and timestamp.tzinfo is None else timestamp.isoformat() if timestamp else None}


def session_emergency_context(db, owner_id: str, session_id: str) -> EmergencyContext | None:
    case = db.query(Case).filter(
        Case.user_id == owner_id, Case.session_id == session_id, Case.priority == 'CRITICAL',
        Case.status.notin_(['Closed', 'Resolved']), Case.safety_status != 'customer_reported_safe',
    ).order_by(Case.created_at.desc(), Case.id.desc()).first()
    return EmergencyContext(case_id=case.id, **safety_fields(case)) if case else None


async def run_chat_turn(payload, user, db, handler):
    from src.services.sqlite_admission import chat_writer
    async with chat_writer(db):
        return await _run_chat_turn(payload, user, db, handler)


async def _run_chat_turn(payload, user, db, handler):
    if not user and not payload.guest_session_id:
        payload = payload.model_copy(update={'guest_session_id': payload.session_id})
    owner = f'user:{user.id}' if user else f'guest:{payload.guest_session_id}'
    lock = _LOCKS.setdefault((str(db.get_bind().url), payload.session_id), asyncio.Lock())
    async with observed_lock(lock, 'application.session_lock'):
        db.expire_all()
        resolve_authorized_active_case(db, user, payload.session_id, payload.case_id, payload.guest_session_id)
        user_is_demo = bool(getattr(user, "is_demo", False)) if user else False
        session = db.get(ChatSession, payload.session_id)
        if not session:
            session = ChatSession(id=payload.session_id, owner=owner, is_demo=user_is_demo)
            db.add(session)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                session = db.get(ChatSession, payload.session_id)
        if bool(getattr(session, "is_demo", False)) != user_is_demo:
            raise HTTPException(404, "Không tìm thấy phiên trò chuyện.")
        if session.owner != owner:
            logger.warning(f"[404 NOT FOUND] session.owner mismatch: db_owner='{session.owner}', request_owner='{owner}', session_id='{payload.session_id}'")
            raise HTTPException(404, "Không tìm thấy phiên trò chuyện.")
        request_key = hashlib.sha256(f'{owner}:{payload.request_id}'.encode()).hexdigest() if payload.request_id else None
        fingerprint = hashlib.sha256(json.dumps(payload.model_dump(), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        record = db.get(ChatRequestRecord, request_key) if request_key else None
        if record:
            if record.request_hash != fingerprint:
                raise HTTPException(409, 'request_id đã được dùng cho nội dung khác.')
            replay = ApiResponse[ChatResponseData].model_validate(record.response)
            receipt = record.response.get('_personal_memory')
            if receipt and user:
                if user.role != 'CUSTOMER':
                    raise HTTPException(403, 'Thông tin cá nhân chỉ dành cho tài khoản khách hàng.')
                from src.services.user_memory import load_user_memory
                from src.services.user_memory_chat import memory_reply
                current = load_user_memory(db, user)
                mode = receipt['mode'] if current.revision == receipt['revision'] else 'stale'
                if mode in {'recall', 'stale'}:
                    replay.data.message = memory_reply(mode, current, receipt['language'], keys=receipt['keys'])
                replay.data._personal_memory_diagnostics = {'mode': mode, 'revision': current.revision, 'replay': True}
            return replay
        # Durable lease complements the process lock across API workers. Another
        # worker returns 409 rather than compute or create a duplicate incident.
        token = uuid4().hex
        now = datetime.now(UTC)
        claim = db.execute(update(ChatSession).where(
            ChatSession.id == payload.session_id,
            or_(ChatSession.lease_token.is_(None), ChatSession.lease_until < now),
        ).values(lease_token=token, lease_until=now + timedelta(minutes=2)), execution_options={'synchronize_session': False})
        if claim.rowcount != 1:
            db.rollback()
            raise HTTPException(409, 'Phiên đang xử lý một tin nhắn khác. Vui lòng thử lại.')
        db.commit()
        db.info.pop('chat_turn_customer_id', None)
        try:
            if not (session.memory_states or {}).get(payload.session_id):
                from src.config import get_settings
                if get_settings().database_url.startswith('sqlite:///'):
                    legacy = get_store().read_existing_state(payload.session_id, user.id if user else owner, 'customer' if user else 'guest')
                    if legacy:
                        session.memory_states = {**(session.memory_states or {}), payload.session_id: json.loads(encode_state(legacy))}
            before_turn = (session.memory_states or {}).get(payload.session_id, {}).get('turn', 0)
            snapshot = (session.memory_states or {}).get(payload.session_id, {})
            conversation = ConversationContext.model_validate(snapshot.get('conversation_context') or {})
            from src.config import get_settings
            from src.services.agent_llm import new_turn_budget
            budget = new_turn_budget(time.monotonic() + get_settings().agent_turn_timeout_s)
            budget.update(session_id=payload.session_id, turn=before_turn + 1)
            recent = [{'role': m.get('type'), 'content': str(m.get('data', {}).get('content', ''))[:400]}
                      for m in snapshot.get('messages', [])[-4:]]
            from src.services.chat_language import detect_language, response_language
            from src.services.customer_localization import canonical_input, localize_response
            input_language = detect_language(payload.message, conversation.preferred_language)
            language = response_language(payload.message, payload.language, conversation.preferred_language)
            conversation.preferred_language = language
            original = sanitize_pii(payload.message)[0]
            memory_snapshot, memory_changes, personal_mode, memory_result = None, [], None, None
            selected_personal_model = None
            personal_subject = bool(snapshot.get('personal_subject_from_memory'))
            personal_context_stale = False
            if get_settings().user_memory_enabled:
                from src.services.user_memory import MemorySnapshot, extract_memory_changes, load_user_memory
                from src.services.user_memory_chat import memory_mode
                if user and user.role == 'CUSTOMER':
                    memory_snapshot = load_user_memory(db, user)
                    memory_changes = extract_memory_changes(payload.message, memory_snapshot, conversation)
                    personal_mode = memory_mode(payload.message, memory_changes, memory_snapshot)
                    if snapshot.get('user_memory_revision') != memory_snapshot.revision and personal_subject and conversation.active_goal != 'incident':
                        personal_context_stale = True
                        conversation.subject = None
                        conversation.facts = {key: fact for key, fact in conversation.facts.items()
                                              if key not in {'model', 'version', 'year', 'battery', 'city'}}
                        conversation.last_answer = []
                        personal_subject = False
                elif not user:
                    empty = MemorySnapshot(revision=0)
                    if memory_mode(payload.message, extract_memory_changes(payload.message, empty, conversation), empty):
                        personal_mode = 'guest'
                from src.agents.guardrails import evaluate_hard_safety
                if payload.attachment_ids or evaluate_hard_safety(payload.message)[0]:
                    personal_mode = None
            if personal_mode:
                from src.services.chat_normalization import NormalizedMessage
                canonical = original
                spelling = NormalizedMessage(original_text=original, text=original)
            else:
                canonical = await canonical_input(original, input_language, budget)
                spelling = await normalize_message(canonical, recent_turns=recent, budget=budget)
            spelling.original_text = original
            if personal_mode:
                turn = TurnUnderstanding(move='supply_info', original_text=original, resolved_query=original,
                                         goal=conversation.active_goal, topic=conversation.topic, subject=conversation.subject)
            elif spelling.needs_confirmation:
                turn = TurnUnderstanding(original_text=spelling.original_text, resolved_query=spelling.text,
                                         needs_confirmation=True, goal=conversation.active_goal,
                                         topic=conversation.topic, subject=conversation.subject)
            else:
                turn = await understand_turn(spelling.text, conversation, recent, budget)
                turn.original_text = spelling.original_text
                if memory_snapshot is not None:
                    from src.services.chat_normalization import fold_text
                    from src.services.user_memory import resolve_personal_memory
                    selected = resolve_personal_memory(payload.message, memory_snapshot)
                    owns = selected.get('owned_vehicle.model')
                    personal_reference = re.search(r'xe (?:cua )?toi|my (?:car|vehicle)', fold_text(payload.message))
                    if (owns and personal_reference and not turn.updates.get('model')
                            and turn.goal in {'warranty', 'maintenance', 'quote', 'range', 'capacity', 'charging', 'appearance'}):
                        selected_personal_model = owns['value']
                        turn.subject = selected_personal_model
                        turn.updates['model'] = selected_personal_model
                        for memory_key, slot in [('owned_vehicle.version', 'version'), ('owned_vehicle.model_year', 'year'),
                                                 ('owned_vehicle.battery_plan', 'battery')]:
                            if memory_key in selected:
                                value = selected[memory_key]['value']
                                if slot == 'battery':
                                    value = {'purchased': 'mua kèm pin', 'subscription': 'thuê pin'}[value]
                                turn.updates.setdefault(slot, str(value))
                        personal_subject = True
                    elif turn.updates.get('model') or turn.goal == 'incident' or turn.subject is None:
                        personal_subject = False
                conversation = apply_turn(conversation, turn, before_turn + 1)
            db.info['conversation_turn'] = {'context': conversation.model_dump(), 'understanding': turn.model_dump(),
                                           'budget': budget, 'normalization': spelling.model_dump(),
                                           'personal_memory_mode': personal_mode,
                                           'personal_memory_model': selected_personal_model,
                                           'personal_context_stale': personal_context_stale,
                                           'user_memory_revision': memory_snapshot.revision if memory_snapshot else None,
                                           'preserved_vehicle_context': snapshot.get('vehicle_context', {})}
            response = await handler(payload, user, db)
            data = response.data
            if memory_snapshot is not None and memory_changes:
                from src.services.user_memory import apply_user_memory_changes, load_user_memory
                memory_result = apply_user_memory_changes(db, user, memory_changes,
                    expected_revision=memory_snapshot.revision, source_kind='chat',
                    source_session_id=payload.session_id, source_message_id=db.info.get('chat_turn_customer_id'))
                memory_snapshot = load_user_memory(db, user)
                if memory_result.status == 'written' and personal_subject and conversation.active_goal != 'incident':
                    personal_context_stale = True
                    conversation.subject = None
                    conversation.facts = {key: fact for key, fact in conversation.facts.items()
                                          if key not in {'model', 'version', 'year', 'battery', 'city'}}
                    conversation.last_answer = []
                    personal_subject = False
            if personal_mode == 'recall' and memory_snapshot is not None:
                from src.services.user_memory import fence_user_memory_revision, load_user_memory
                memory_snapshot = load_user_memory(db, user)
                fence = fence_user_memory_revision(db, user, memory_snapshot.revision)
                if fence.status == 'conflict':
                    raise HTTPException(409, 'Thông tin ghi nhớ vừa thay đổi. Vui lòng hỏi lại.')
            if personal_mode:
                from src.services.user_memory import MemorySnapshot
                from src.services.user_memory_chat import memory_reply
                data.message = memory_reply(personal_mode, memory_snapshot or MemorySnapshot(revision=0), language,
                                            text=payload.message, changes=memory_changes, result=memory_result)
                data.response_type = 'CLARIFICATION' if personal_mode == 'clarify' else 'FAQ_ANSWER'
                data.citations, data.vehicle_cards, data.suggested_replies = [], [], []
                data._personal_memory_diagnostics = {'mode': personal_mode,
                    'revision': memory_snapshot.revision if memory_snapshot else None,
                    'status': memory_result.status if memory_result else 'read',
                    'keys': [change.key for change in memory_changes]}
            from src.services.vehicle_catalog import (
                is_generic_vehicle_comparison,
                select_vehicle_cards,
                vehicle_comparison_reply,
                vehicle_overview_reply,
            )
            card_text = '' if spelling.needs_confirmation or personal_mode else spelling.text
            if not spelling.needs_confirmation and not personal_mode and is_generic_vehicle_comparison(turn.resolved_query):
                card_text = turn.resolved_query
            generated_outcome = db.info.pop('conversation_final', {})
            answer_path = ('clarification' if spelling.needs_confirmation else
                           'personal_memory' if personal_mode else
                           'incident' if turn.goal == 'incident' else
                           'refusal' if data.response_type == 'OOS' else
                           generated_outcome.get('answer_path') or ('rag' if data.citations else 'general'))
            from src.services.vehicle_card_intent import is_generic_vehicle_overview
            data.vehicle_cards = select_vehicle_cards(card_text, active_goal=conversation.active_goal, context_topic=conversation.topic, understanding=turn)
            data.vehicle_comparison = len(data.vehicle_cards) == 2 and 'so sánh' in card_text.casefold()
            if data.vehicle_cards:
                if is_generic_vehicle_overview(card_text):
                    data.message = vehicle_overview_reply(data.vehicle_cards)
                    data.response_type = 'FAQ_ANSWER'
                    answer_path = 'snapshot'
                if re.fullmatch(r'\s*(?:(?:(?:tư vấn|giới thiệu|thông tin)(?: về)?(?: xe| mẫu xe)?\s+)?(?:vinfast\s+)?vf\s*[356789](?:\s+(?:(?:phiên bản|bản)\s+)?(?:eco|plus))?|so sánh\s+vf\s*[356789]\s+(?:và|với)\s+vf\s*[356789]|so sánh\s+vf\s*8\s+(?:eco|plus)\s+(?:và|với)\s+(?:vf\s*8\s+)?(?:eco|plus))[.!?]?\s*', payload.message, re.I):
                    data.message = vehicle_overview_reply(data.vehicle_cards)
                    data.response_type = 'FAQ_ANSWER'
                    answer_path = 'snapshot'
                if all(card.rolling_cost_url for card in data.vehicle_cards):
                    data.suggested_replies = ['Dự toán lăn bánh ' + card.name for card in data.vehicle_cards]
                if data.vehicle_comparison:
                    if is_generic_vehicle_comparison(card_text):
                        from src.models.schemas import Citation
                        from src.services.vehicle_catalog import catalog_citations
                        data.message = vehicle_comparison_reply(data.vehicle_cards)
                        data.citations = [Citation(**item) for item in catalog_citations(data.vehicle_cards)]
                        data.response_type = 'FAQ_ANSWER'
                        answer_path = 'snapshot'
                    data.suggested_replies = []
                if answer_path == 'snapshot' and is_generic_vehicle_overview(card_text):
                    owned = getattr(user, 'vehicle_model', None) or (payload.client_context.vehicle_model if payload.client_context else None)
                    if owned and turn.subject and re.sub(r'\s+', '', owned).upper() != turn.subject:
                        owned_label = re.sub(r'^VF\s*', 'VF ', owned, flags=re.I)
                        data.message += f'\n\nQuý khách có muốn so sánh {turn.subject} với xe {owned_label} đang sử dụng không?'
                agent_message = db.query(Message).filter_by(session_id=payload.session_id, sender_type='AGENT').order_by(Message.created_at.desc(), Message.id.desc()).first()
                if agent_message:
                    agent_message.content = data.message
                    agent_message.msg_metadata = {**(agent_message.msg_metadata or {}),
                        'response_type': data.response_type,
                        'vehicle_comparison': data.vehicle_comparison,
                        'suggested_replies': data.suggested_replies or [],
                        'vehicle_cards': [card.model_dump() for card in data.vehicle_cards]}
            if data.case_id and not user:
                # Every branch shares this persistence boundary: guests may
                # receive guidance, but cannot commit an ownerless case.
                raise HTTPException(401, 'Vui lòng đăng nhập để tạo và theo dõi hồ sơ hỗ trợ.')
            if data.case_id:
                from src.services.auth import scoped_cases
                case = scoped_cases(db, user).filter(Case.id == data.case_id).first()
                if case:
                    for key, value in safety_fields(case).items():
                        setattr(data, key, value)
                    data.priority = case.priority
                    data.status = case.status
                    data.show_emergency_banner = case.priority == 'CRITICAL' and case.status not in {'Closed', 'Resolved'}
            if user:
                data.emergency_context = session_emergency_context(db, user.id, payload.session_id)
                data.show_emergency_banner = bool(data.show_emergency_banner or data.emergency_context)
            # Booking capability is a server fact, never a model-generated receipt.
            booking_progress = None
            from src.services.faq_questions import faq_parts
            compound_help = bool(faq_parts(canonical))
            if (conversation.active_goal == 'test_drive' or
                conversation.active_goal == 'maintenance' and re.search(r'đặt lịch|đặt hẹn', conversation.topic, re.I)) and not data.show_emergency_banner and not compound_help and not personal_mode:
                from src.services.conversation_progress import progress_reply
                booking_progress = derive_progress(conversation, {}, None, None)
                operational_reply = progress_reply(turn, conversation, booking_progress)
                if operational_reply:
                    data.message = operational_reply
                    data.citations = []
                    data.vehicle_cards = []
                    data.suggested_replies = []
                    answer_path = 'operational'
            if personal_mode:
                data.language = language
            else:
                await localize_response(data, language, budget, snapshot=answer_path == 'snapshot', operational=booking_progress,
                                        conversation=conversation)
                if memory_result:
                    from src.services.user_memory_chat import memory_reply
                    data.message += '\n\n' + memory_reply('write', memory_snapshot, language,
                        changes=memory_changes, result=memory_result)
            agent_message = db.query(Message).filter_by(session_id=payload.session_id, sender_type='AGENT').order_by(Message.created_at.desc(), Message.id.desc()).first()
            if agent_message:
                agent_message.content = data.message
                agent_message.msg_metadata = {**(agent_message.msg_metadata or {}), 'language': language,
                    'response_type': data.response_type, 'suggested_replies': data.suggested_replies or [],
                    'citations': [citation.model_dump(mode='json') for citation in (data.citations or [])],
                    'safe_guidance': data.safe_guidance, 'vehicle_comparison': data.vehicle_comparison,
                    'vehicle_cards': [card.model_dump() for card in data.vehicle_cards]}
            if request_key:
                receipt = response.model_dump(mode='json')
                if personal_mode:
                    # Store a receipt reference, not another durable copy of
                    # recalled fact values. Replays resolve the current revision.
                    from src.services.user_memory import personal_memory_keys
                    if personal_mode == 'recall':
                        receipt['data']['message'] = ''
                    receipt['_personal_memory'] = {'mode': personal_mode, 'language': language,
                        'revision': memory_snapshot.revision if memory_snapshot else 0,
                        'keys': list(personal_memory_keys(payload.message) or [])}
                db.add(ChatRequestRecord(id=request_key, owner=owner, session_id=payload.session_id,
                                         request_hash=fingerprint, response=receipt))
            # Bind a vehicle/incident scope only after the accepted response.
            # A new vehicle awaiting details must stay unbound on its next turn.
            db.flush()
            latest = db.get(Message, db.info.pop('chat_turn_customer_id', None)) if db.info.get('chat_turn_customer_id') else None
            if latest:
                meta = dict(latest.msg_metadata or {})
                meta['language'] = language
                if memory_snapshot is not None:
                    meta['user_memory_revision'] = memory_snapshot.revision
                latest.msg_metadata = meta
                context = dict(meta.get('vehicle_context') or {})
                if personal_context_stale and not context.get('is_incident'):
                    context['owned_model'] = None
                    if not turn.updates.get('model'):
                        context.update(models=[], target_model=None)
                    meta['vehicle_context'] = context
                    latest.msg_metadata = meta
                    cache = dict((session.memory_states or {}).get(payload.session_id, {}))
                    cache['captured_fields'] = {key: value for key, value in cache.get('captured_fields', {}).items() if key != 'vehicle_model'}
                    cache['fact_history'] = [row for row in cache.get('fact_history', []) if row.get('field') != 'vehicle_model']
                    cache.update(memory_summary='', summary_evidence=[])
                    session.memory_states = {**(session.memory_states or {}), payload.session_id: cache}
                if context.get('is_incident'):
                    context['incident_case_id'] = data.case_id
                    meta['vehicle_context'] = context
                    latest.msg_metadata = meta
                accept_application_memory(session, payload.session_id, latest.content, data, context, before_turn,
                                          observation_text='' if spelling.needs_confirmation or personal_mode else spelling.text)
            stored = (session.memory_states or {}).get(payload.session_id, {})
            from src.services.auth import scoped_cases
            case = scoped_cases(db, user).filter(Case.id == data.case_id).first() if data.case_id else None
            brief = db.query(CaseBrief).filter_by(case_id=case.id).first() if case else None
            case_snapshot = {'id': case.id, 'status': case.status,
                             'facts': dict(brief.captured_fields or {}) if brief else {}} if case else None
            progress = derive_progress(conversation, {}, case_snapshot, None)
            conversation.pending_question = {'slots': progress.missing_fields, 'purpose': progress.next_action}
            claims = db.info.pop('conversation_claims', [])
            if answer_path == 'snapshot':
                # A discarded handler answer cannot populate authoritative facts.
                claims = []
            if claims:
                conversation.last_answer = [*conversation.last_answer, {'turn': before_turn + 1, 'claims': claims}][-3:]
            from src.services.request_diagnostics import final_response_diagnostics
            answer_status = ('error' if budget.get('presentation_failed') or memory_result and memory_result.status == 'conflict' else
                             'external_action_required' if personal_mode == 'guest' else
                             'answered' if answer_path == 'snapshot' else
                             'needs_clarification' if spelling.needs_confirmation or data.response_type == 'CLARIFICATION' else
                             'refused' if data.response_type == 'OOS' else
                             'external_action_required' if booking_progress and booking_progress.state == 'external_action_required' else
                             generated_outcome.get('answer_status'))
            final_diagnostics = final_response_diagnostics(answer_path=answer_path,
                successful=not budget.get('presentation_failed') and (answer_path == 'snapshot' or generated_outcome.get('successful', data.response_type not in {'NO_SOURCE', 'ERROR'})),
                stages=budget.get('stage_outcomes', []), answer_status=answer_status)
            if agent_message:
                agent_message.msg_metadata = {**(agent_message.msg_metadata or {}),
                    'answer_status': final_diagnostics['answer_status'],
                    'answer_parts': (db.info.get('conversation_retrieval') or {}).get('parts', [])}
            from src.services.tracer import record_trace_step
            try:
                record_trace_step(payload.session_id, before_turn + 1, 'application', 'final_response',
                                  final_diagnostics['final_outcome'], metadata=final_diagnostics)
            except Exception:
                pass
            session.memory_states = {**(session.memory_states or {}), payload.session_id: {
                **stored, 'conversation_context': conversation.model_dump(), 'turn_understanding': turn.model_dump(),
                **({'user_memory_revision': memory_snapshot.revision,
                    'personal_subject_from_memory': personal_subject} if memory_snapshot is not None else {}),
                'conversation_progress': progress.model_dump(),
                'final_diagnostics': final_diagnostics,
                'conversation_retrieval': db.info.pop('conversation_retrieval', {}),
                'conversation_route': db.info.pop('conversation_route', None) or (
                    'safety' if turn.move == 'new_incident' and data.priority == 'CRITICAL' else
                    'incident' if conversation.active_goal == 'incident' else data.response_type),
            }}
            released = db.execute(update(ChatSession).where(ChatSession.id == payload.session_id, ChatSession.lease_token == token)
                                  .values(lease_token=None, lease_until=None), execution_options={'synchronize_session': False})
            if released.rowcount != 1:
                raise HTTPException(409, 'Phiên đã thay đổi trong lúc xử lý. Vui lòng thử lại.')
            with observation('business.persist'):
                db.commit()
            return response
        except BaseException:
            db.info.pop('chat_turn_customer_id', None)
            db.rollback()
            db.execute(update(ChatSession).where(ChatSession.id == payload.session_id, ChatSession.lease_token == token)
                       .values(lease_token=None, lease_until=None), execution_options={'synchronize_session': False})
            db.commit()
            raise
        finally:
            db.info.pop('conversation_turn', None)
            db.info.pop('conversation_claims', None)
            db.info.pop('conversation_retrieval', None)
            db.info.pop('conversation_route', None)
            db.info.pop('conversation_final', None)
