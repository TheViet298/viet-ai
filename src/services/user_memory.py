"""Consented personal facts, scoped by principal and fenced by a SQL revision.

No model output or transcript replay enters this service. Helpers never commit:
the accepted chat/profile/delete transaction owns their writes and acknowledgements.
"""
from datetime import UTC, datetime
import re
from typing import Literal
import unicodedata

from pydantic import BaseModel, Field, StrictInt, StrictStr, model_validator
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.models.db_models import ChatSession, Message, User, UserMemoryFact
from src.services.chat_normalization import fold_text
from src.services.conversation_context import ConversationContext

MemoryKey = Literal['owned_vehicle.model', 'owned_vehicle.version', 'owned_vehicle.model_year',
                    'owned_vehicle.battery_plan', 'home_city', 'registration_city']
KEYS = ('owned_vehicle.model', 'owned_vehicle.version', 'owned_vehicle.model_year',
        'owned_vehicle.battery_plan', 'home_city', 'registration_city')
VEHICLE_CHILDREN = KEYS[1:4]


class MemoryFact(BaseModel):
    value: StrictStr | StrictInt | None
    status: Literal['confirmed', 'unknown', 'retracted']
    source_kind: Literal['chat', 'profile']
    source_session_id: str | None = None
    source_message_id: str | None = None
    updated_at: datetime


class MemorySnapshot(BaseModel):
    revision: int = Field(ge=0)
    facts: dict[str, MemoryFact] = Field(default_factory=dict)


class MemoryChange(BaseModel):
    key: MemoryKey
    value: StrictStr | StrictInt | None
    status: Literal['confirmed', 'unknown', 'retracted'] = 'confirmed'

    @model_validator(mode='after')
    def validate_value(self):
        if self.status != 'confirmed':
            if self.value is not None:
                raise ValueError('Unknown/retracted facts must erase their value')
            return self
        if self.value is None:
            raise ValueError('Confirmed facts require a value')
        if self.key == 'owned_vehicle.model_year':
            if type(self.value) is not int or not 1900 <= self.value <= 2099:
                raise ValueError('Invalid vehicle year')
            return self
        if not isinstance(self.value, str) or not self.value.strip() or len(self.value) > 80:
            raise ValueError('Invalid fact value')
        if re.search(r'[\x00-\x1f\x7f<>`{}\[\]\\]', self.value):
            raise ValueError('Invalid fact characters')
        value = ' '.join(self.value.split())
        if self.key == 'owned_vehicle.model':
            value = re.sub(r'\s+', '', value).upper()
            value = 'VFE34' if value == 'E34' else value
            if value not in {'VF3', 'VF5', 'VF6', 'VF7', 'VF8', 'VF9', 'VFE34'}:
                raise ValueError('Unsupported vehicle model')
        elif self.key == 'owned_vehicle.version':
            versions = {'eco': 'Eco', 'plus': 'Plus', 'plus awd': 'Plus AWD',
                        'eco fwd': 'Eco FWD', 'plus fwd': 'Plus FWD'}
            if value.casefold() not in versions:
                raise ValueError('Unsupported vehicle version')
            value = versions[value.casefold()]
        elif self.key == 'owned_vehicle.battery_plan':
            if value not in {'purchased', 'subscription'}:
                raise ValueError('Unsupported battery plan')
        elif re.search(r'\d|[^\w\s.,\u2019\x27-]', value):
            raise ValueError('A city is not an address or instruction')
        self.value = value
        return self


class MemoryWriteResult(BaseModel):
    status: Literal['written', 'unchanged', 'conflict']
    revision: int


def _principal(user: User | None) -> str:
    if not user or user.role != 'CUSTOMER':
        raise ValueError('Personal memory requires an authenticated customer')
    return user.id


def load_user_memory(db: Session, user: User) -> MemorySnapshot:
    identity = _principal(user)
    # One SELECT gives a consistent statement snapshot of revision and facts.
    rows = db.execute(select(User.memory_revision, User.vehicle_model, User.created_at, UserMemoryFact)
        .outerjoin(UserMemoryFact, UserMemoryFact.user_id == User.id)
        .where(User.id == identity, User.role == 'CUSTOMER')
        .execution_options(populate_existing=True)).all()
    if not rows:
        raise ValueError('Customer is no longer available')
    revision, projection, created_at = rows[0][:3]
    facts = {}
    for _, _, _, row in rows:
        if row is not None:
            facts[row.key] = MemoryFact(value=row.value, status=row.status, source_kind=row.source_kind,
                source_session_id=row.source_session_id, source_message_id=row.source_message_id,
                updated_at=row.updated_at.replace(tzinfo=UTC) if row.updated_at.tzinfo is None else row.updated_at)
    if 'owned_vehicle.model' not in facts and projection:
        # Legacy profile is a separate legitimate input, never a chat backfill.
        try:
            model = MemoryChange(key='owned_vehicle.model', value=projection).value
        except ValueError:
            model = None
        if model:
            facts['owned_vehicle.model'] = MemoryFact(value=model, status='confirmed', source_kind='profile',
                updated_at=created_at.replace(tzinfo=UTC) if created_at.tzinfo is None else created_at)
    return MemorySnapshot(revision=revision, facts=facts)


def _verify_chat_source(db: Session, identity: str, session: str | None, message: str | None):
    if not session or not message:
        raise ValueError('Chat memory needs an accepted customer message source')
    found = db.execute(select(Message.id).join(ChatSession, ChatSession.id == Message.session_id).where(
        Message.id == message, Message.session_id == session, Message.sender_type == 'CUSTOMER',
        ChatSession.owner == f'user:{identity}')).scalar_one_or_none()
    if not found:
        raise ValueError('Memory source does not belong to this customer')


def apply_user_memory_changes(db: Session, user: User, changes: list[MemoryChange], *, expected_revision: int,
                              source_kind: Literal['chat', 'profile'], source_session_id: str | None,
                              source_message_id: str | None) -> MemoryWriteResult:
    identity = _principal(user)
    if source_kind not in {'chat', 'profile'}:
        raise ValueError('Invalid memory source')
    supplied = {change.key: change for change in (MemoryChange.model_validate(value) for value in changes)}
    snapshot = load_user_memory(db, user)
    if snapshot.revision != expected_revision:
        return MemoryWriteResult(status='conflict', revision=snapshot.revision)
    if not supplied:
        return MemoryWriteResult(status='unchanged', revision=snapshot.revision)
    if source_kind == 'chat':
        _verify_chat_source(db, identity, source_session_id, source_message_id)
    elif source_session_id is not None or source_message_id is not None:
        raise ValueError('Profile facts cannot claim a chat source')
    model = supplied.get('owned_vehicle.model')
    previous_model = snapshot.facts.get('owned_vehicle.model')
    if model and (not previous_model or (model.value, model.status) != (previous_model.value, previous_model.status)):
        supplied.update({key: MemoryChange(key=key, value=None, status='retracted')
                         for key in VEHICLE_CHILDREN if key not in supplied})
    changed = []
    for key, change in supplied.items():
        old = snapshot.facts.get(key)
        persisted = db.get(UserMemoryFact, (identity, key))
        if (persisted is None or old is None or
                (old.value, old.status, old.source_kind, old.source_session_id, old.source_message_id) !=
                (change.value, change.status, source_kind, source_session_id, source_message_id)):
            changed.append(change)
    if not changed:
        return MemoryWriteResult(status='unchanged', revision=snapshot.revision)
    values = {'memory_revision': expected_revision + 1}
    if model:
        values['vehicle_model'] = ('e34' if model.value == 'VFE34' else model.value) if model.status == 'confirmed' else None
    claim = db.execute(update(User).where(User.id == identity, User.role == 'CUSTOMER',
        User.memory_revision == expected_revision).values(**values), execution_options={'synchronize_session': False})
    if claim.rowcount != 1:
        latest = db.execute(select(User.memory_revision).where(User.id == identity)).scalar_one()
        return MemoryWriteResult(status='conflict', revision=latest)
    timestamp = datetime.now(UTC)
    for change in changed:
        row = db.get(UserMemoryFact, (identity, change.key))
        if row is None:
            row = UserMemoryFact(user_id=identity, key=change.key)
            db.add(row)
        row.value, row.status, row.source_kind = change.value, change.status, source_kind
        row.source_session_id, row.source_message_id, row.updated_at = source_session_id, source_message_id, timestamp
    db.flush()
    db.expire(user, ['memory_revision', 'vehicle_model'])
    return MemoryWriteResult(status='written', revision=expected_revision + 1)


def _city(segment: str) -> str:
    body = fold_text(segment.strip(' .'))
    names = {'ha noi': 'Hà Nội', 'hanoi': 'Hà Nội', 'da nang': 'Đà Nẵng', 'danang': 'Đà Nẵng',
             'ho chi minh': 'TP. Hồ Chí Minh', 'tp ho chi minh': 'TP. Hồ Chí Minh', 'hcm': 'TP. Hồ Chí Minh'}
    return names.get(body, segment.strip(' .'))


def extract_memory_changes(text: str, snapshot: MemorySnapshot, context: ConversationContext) -> list[MemoryChange]:
    """Interpret direct human consent/identified corrections, never quoted instructions."""
    text = unicodedata.normalize('NFC', text)
    if '```' in text or re.search(r'^(?:tai lieu|the document|according to|assistant|system)\b', fold_text(text)):
        return []
    direct = re.sub(r'"[^"\n]*"|“[^”\n]*”|`[^`\n]*`', '', text)
    body = fold_text(direct)
    forget = re.match(r'^(?:(?:hay|vui long|please)\s+)?(?:quen|xoa|forget|delete)\b', body.strip())
    if forget:
        personal_target = re.search(r'ghi nho|da nho|da luu|nho luu|thong tin.*toi|'
                                    r'\b(?:memory|memories|everything)\b|\bmy\b|about me|'
                                    r'xe (?:cua )?toi|thanh pho.*toi|noi o|toan bo thong tin|quen het', body)
        if not personal_target or re.search(r'mat khau|password|ma loi|\bloi\s+[a-z]*\d|lich su sac', body):
            return []
        keys = (['registration_city'] if re.search(r'dang ky|registration', body) else
                ['home_city'] if re.search(r'thanh pho|noi o|city|nha toi', body) else
                list(KEYS[:4]) if re.search(r'\bxe\b|vehicle|car', body) else list(KEYS))
        return [MemoryChange(key=key, value=None, status='retracted') for key in keys]
    if re.search(r'dung (?:ghi )?nho|khong (?:muon|cho phep|can).{0,20}nho|do not remember|don.t remember', body):
        return []
    consent = bool(re.match(r'^(?:(?:hay|vui long|ban|please)\s+)?(?:ghi nho|nho|luu thong tin|remember|save my)\b', body.strip()))
    correction = bool(re.search(r'khong phai|dinh chinh|y toi la|correction|actually|not .{0,30}but', body))
    if not consent and not correction:
        return []
    owner = bool(re.search(r'\bxe (?:cua )?toi\b|\btoi (?:so huu|su dung)\b|\bmy (?:car|vehicle)\b|\bi (?:own|drive)\b', body))
    if re.search(r'toi khong (?:so huu|co xe|su dung)|i do not own|i don.t own|not my (?:car|vehicle)', body):
        owner = False
    affirmative = re.sub(r'\b(?:chu khong phai|khong phai|not)\s+(?:vf\s*(?:e34|[356789])(?:\s+(?:eco|plus))?|eco|plus)\b', '', body)
    affirmative = re.sub(r'\bkhong\s+(?:mua kem pin|mua dut pin|thue pin)\b', '', affirmative)
    values = {}
    if owner:
        match = re.search(r'\bvf\s*(e34|[356789])\b', affirmative)
        model_known = bool(match or snapshot.facts.get('owned_vehicle.model') and snapshot.facts['owned_vehicle.model'].status == 'confirmed')
        if match:
            values['owned_vehicle.model'] = 'VF' + match[1].upper()
        version = re.search(r'\b(?:eco|plus)(?:\s+(?:awd|fwd))?\b', affirmative)
        if version and model_known:
            values['owned_vehicle.version'] = version[0].title().replace('Awd', 'AWD').replace('Fwd', 'FWD')
        year = re.search(r'\b(?:doi|nam san xuat|model year|year)\s+(20\d{2})\b', affirmative)
        if year and model_known:
            values['owned_vehicle.model_year'] = int(year[1])
        if model_known:
            if re.search(r'mua kem pin|mua dut pin|purchased battery|own the battery', affirmative):
                values['owned_vehicle.battery_plan'] = 'purchased'
            elif re.search(r'thue pin|battery subscription|leased battery', affirmative):
                values['owned_vehicle.battery_plan'] = 'subscription'
    city_patterns = {'home_city': r'\b(?:toi (?:song|cu tru) (?:o|tai)|nha toi (?:o|tai)|toi (?:o|tai)|i live in|my home city is)\s+',
                     'registration_city': r'\b(?:dang ky(?: bien so)?(?: xe)?(?: o| tai)?|registration city(?: is)?|registered(?: my car)? in)\s+'}
    for key, pattern in city_patterns.items():
        if key == 'home_city' and re.search(r'toi dang|hien tai|bay gio|tram sac|xuong|showroom|currently|right now', body):
            continue
        match = re.search(pattern, body)
        if match:
            tail = direct[match.end():]
            end = re.search(r'[,;!?\n]|\s+(?:va|and|dang ky)\b', fold_text(tail))
            values[key] = _city(tail[:end.start()] if end else tail)
    changes = []
    for key, value in values.items():
        # Corrections update only identified facts the user already allowed.
        if not consent and (key not in snapshot.facts or snapshot.facts[key].status != 'confirmed'):
            continue
        try:
            changes.append(MemoryChange(key=key, value=value))
        except ValueError:
            continue
    return changes


def personal_memory_keys(text: str) -> tuple[str, ...] | None:
    body = fold_text(text)
    if re.search(r'dang ky|registration', body) and re.search(r'toi|my|previous|truoc', body):
        return ('registration_city',)
    if re.search(r'thanh pho|song o dau|noi o|home city|where do i live|city', body) and re.search(r'toi|my|i |truoc|previous', body):
        return ('home_city',)
    if re.search(r'xe (?:cua )?toi|my (?:car|vehicle)|toi (?:su dung|so huu).*xe|what (?:car|vehicle).*i|which model', body):
        return KEYS[:4]
    if re.search(r'phien ban.*(?:toi|truoc)|(?:trim|version).*(?:i |my|previous)', body):
        return KEYS[:2]
    if re.search(r'nhac lai thong tin|thong tin.*(?:khai bao|da luu)|remember about me', body):
        return KEYS
    return None


def resolve_personal_memory(text: str, snapshot: MemorySnapshot) -> dict:
    selected = personal_memory_keys(text)
    if not selected:
        return {}
    return {key: snapshot.facts[key].model_dump(mode='json') for key in selected
            if key in snapshot.facts and snapshot.facts[key].status == 'confirmed'}
