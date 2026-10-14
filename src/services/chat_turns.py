"""Own, serialize and atomically persist application chat turns."""
import asyncio
import hashlib
import re
import json
import logging
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
from src.services.conversation_context import ConversationContext, apply_turn, understand_turn
from src.services.conversation_progress import derive_progress
from src.services.observability import observation
from src.services.session_store import encode_state, get_store
from src.services.request_diagnostics import observed_lock

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
    if not user and not payload.guest_session_id:
        payload = payload.model_copy(update={'guest_session_id': payload.session_id})
    owner = f'user:{user.id}' if user else f'guest:{payload.guest_session_id}'
    lock = _LOCKS.setdefault((str(db.get_bind().url), payload.session_id), asyncio.Lock())
    async with observed_lock(lock, 'application.session_lock'):
        db.expire_all()
        resolve_authorized_active_case(db, user, payload.session_id, payload.case_id, payload.guest_session_id)
        session = db.get(ChatSession, payload.session_id)
        if not session:
            session = ChatSession(id=payload.session_id, owner=owner)
            db.add(session)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                session = db.get(ChatSession, payload.session_id)
        if session.owner != owner:
            if session.owner and (session.owner.startswith('guest:') or session.owner == 'guest:None'):
                session.owner = owner
                db.commit()
            else:
                logger.warning(f"[403 FORBIDDEN] session.owner mismatch: db_owner='{session.owner}', request_owner='{owner}', session_id='{payload.session_id}'")
                raise HTTPException(403, f'Phiên hội thoại không thuộc khách hàng này (owner={session.owner}).')
        request_key = hashlib.sha256(f'{owner}:{payload.request_id}'.encode()).hexdigest() if payload.request_id else None
        fingerprint = hashlib.sha256(json.dumps(payload.model_dump(), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        record = db.get(ChatRequestRecord, request_key) if request_key else None
        if record:
            if record.request_hash != fingerprint:
                raise HTTPException(409, 'request_id đã được dùng cho nội dung khác.')
            return ApiResponse[ChatResponseData].model_validate(record.response)
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
            budget = {'deadline': time.monotonic() + get_settings().agent_turn_timeout_s, 'attempts': 0}
            recent = [{'role': m.get('type'), 'content': str(m.get('data', {}).get('content', ''))[:400]}
                      for m in snapshot.get('messages', [])[-4:]]
            turn = await understand_turn(sanitize_pii(payload.message)[0], conversation, recent, budget)
            conversation = apply_turn(conversation, turn, before_turn + 1)
            db.info['conversation_turn'] = {'context': conversation.model_dump(), 'understanding': turn.model_dump(), 'budget': budget}
            response = await handler(payload, user, db)
            data = response.data
            from src.services.vehicle_catalog import select_vehicle_cards, vehicle_overview_reply, vehicle_comparison_reply, is_generic_vehicle_comparison
            data.vehicle_cards = select_vehicle_cards(payload.message, active_goal=conversation.active_goal, context_topic=conversation.topic)
            data.vehicle_comparison = len(data.vehicle_cards) == 2 and 'so sánh' in payload.message.casefold()
            if data.vehicle_cards:
                if re.fullmatch(r'\s*(?:(?:(?:tư vấn|giới thiệu|thông tin)(?: về)?(?: xe| mẫu xe)?\s+)?(?:vinfast\s+)?vf\s*[356789](?:\s+(?:(?:phiên bản|bản)\s+)?(?:eco|plus))?|so sánh\s+vf\s*[356789]\s+(?:và|với)\s+vf\s*[356789]|so sánh\s+vf\s*8\s+(?:eco|plus)\s+(?:và|với)\s+(?:vf\s*8\s+)?(?:eco|plus))[.!?]?\s*', payload.message, re.I):
                    data.message = vehicle_overview_reply(data.vehicle_cards)
                    data.response_type = 'FAQ_ANSWER'
                if all(card.model == 'VF8' for card in data.vehicle_cards):
                    data.suggested_replies = ['Dự toán lăn bánh ' + card.name for card in data.vehicle_cards]
                if data.vehicle_comparison:
                    if is_generic_vehicle_comparison(payload.message):
                        data.message = vehicle_comparison_reply(data.vehicle_cards)
                        data.response_type = 'FAQ_ANSWER'
                    data.suggested_replies = []
                agent_message = db.query(Message).filter_by(session_id=payload.session_id, sender_type='AGENT').order_by(Message.created_at.desc()).first()
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
                case = db.get(Case, data.case_id)
                for key, value in safety_fields(case).items():
                    setattr(data, key, value)
                data.priority = case.priority
                data.status = case.status
                data.show_emergency_banner = case.priority == 'CRITICAL' and case.status not in {'Closed', 'Resolved'}
            if user:
                data.emergency_context = session_emergency_context(db, user.id, payload.session_id)
                data.show_emergency_banner = bool(data.show_emergency_banner or data.emergency_context)
            if request_key:
                db.add(ChatRequestRecord(id=request_key, owner=owner, session_id=payload.session_id,
                                         request_hash=fingerprint, response=response.model_dump(mode='json')))
            # Bind a vehicle/incident scope only after the accepted response.
            # A new vehicle awaiting details must stay unbound on its next turn.
            db.flush()
            latest = db.get(Message, db.info.pop('chat_turn_customer_id', None)) if db.info.get('chat_turn_customer_id') else None
            if latest:
                meta = dict(latest.msg_metadata or {})
                context = dict(meta.get('vehicle_context') or {})
                if context.get('is_incident'):
                    context['incident_case_id'] = data.case_id
                    meta['vehicle_context'] = context
                    latest.msg_metadata = meta
                accept_application_memory(session, payload.session_id, latest.content, data, context, before_turn)
            stored = (session.memory_states or {}).get(payload.session_id, {})
            case = db.get(Case, data.case_id) if data.case_id else None
            brief = db.query(CaseBrief).filter_by(case_id=case.id).first() if case else None
            case_snapshot = {'id': case.id, 'status': case.status,
                             'facts': dict(brief.captured_fields or {}) if brief else {}} if case else None
            progress = derive_progress(conversation, {}, case_snapshot, None)
            conversation.pending_question = {'slots': progress.missing_fields, 'purpose': progress.next_action}
            claims = db.info.pop('conversation_claims', [])
            if claims:
                conversation.last_answer = [*conversation.last_answer, {'turn': before_turn + 1, 'claims': claims}][-3:]
            session.memory_states = {**(session.memory_states or {}), payload.session_id: {
                **stored, 'conversation_context': conversation.model_dump(), 'turn_understanding': turn.model_dump(),
                'conversation_progress': progress.model_dump(),
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
