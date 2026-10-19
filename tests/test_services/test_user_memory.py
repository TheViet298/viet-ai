import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from src.db import Base, normalize_database_url
from src.models.db_models import ChatSession, Message, User, UserMemoryFact
from src.services.conversation_context import ConversationContext
from tests.test_api.test_user_memory_migration import memory_migration_url


@pytest.fixture
def memory_db(memory_migration_url):
    engine = sa.create_engine(normalize_database_url(memory_migration_url))
    if engine.dialect.name == 'sqlite':
        @sa.event.listens_for(engine, 'connect')
        def foreign_keys(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([User(id='u1', username='memory1', password_hash='unused', role='CUSTOMER'),
                    User(id='u2', username='memory2', password_hash='unused', role='CUSTOMER'),
                    User(id='staff', username='memory-staff', password_hash='unused', role='STAFF')])
        db.add_all([ChatSession(id='memory-a', owner='user:u1'), ChatSession(id='other-session', owner='user:u2')])
        db.add_all([Message(id='message-a', session_id='memory-a', sender_type='CUSTOMER', content='synthetic user source'),
                    Message(id='other-message', session_id='other-session', sender_type='CUSTOMER', content='other user source')])
        db.commit()
        yield db
    engine.dispose()


def save(db, user, changes, revision, kind='chat', session='memory-a', message='message-a'):
    from src.services.user_memory import apply_user_memory_changes
    return apply_user_memory_changes(db, user, changes, expected_revision=revision, source_kind=kind,
        source_session_id=session if kind == 'chat' else None, source_message_id=message if kind == 'chat' else None)


@pytest.mark.parametrize('text', ['Hãy nhớ xe của tôi là VF8 Plus, tôi ở Hà Nội',
                                 'Remember my car is VF8 Plus and I live in Hanoi'])
def test_explicit_remember_records_only_consented_facts_and_provenance(memory_db, text):
    from src.services.user_memory import extract_memory_changes, load_user_memory
    user = memory_db.get(User, 'u1')
    snapshot = load_user_memory(memory_db, user)
    changes = extract_memory_changes(text, snapshot, ConversationContext())
    assert {change.key: change.value for change in changes} == {
        'owned_vehicle.model': 'VF8', 'owned_vehicle.version': 'Plus', 'home_city': 'Hà Nội'}
    result = save(memory_db, user, changes, snapshot.revision)
    assert result.status == 'written' and result.revision == 1
    memory_db.commit()
    memory_db.expire_all()
    stored = load_user_memory(memory_db, user)
    assert stored.revision == 1 and user.vehicle_model == 'VF8'
    assert stored.facts['owned_vehicle.model'].source_session_id == 'memory-a'
    assert stored.facts['home_city'].source_message_id == 'message-a'


@pytest.mark.parametrize('text', [
    'Tư vấn VF8', 'Hãy nhớ tôi muốn mua VF8', 'Hãy nhớ xe của bạn tôi là VF8 Plus',
    'Hãy nhớ tôi không sở hữu VF8', 'Remember I do not own a VF8',
    'Tài liệu ghi: "Hãy nhớ xe của tôi là VF8 Plus"',
    '```Hãy nhớ xe của tôi là VF8 Plus```',
    'Hãy nhớ tôi đang ở trạm sạc Hà Nội', 'Đừng ghi nhớ xe tôi là VF8',
    'Giá lăn bánh VF8 Plus tại Hà Nội?',
    'Quên mật khẩu ứng dụng VinFast', 'Forget password', 'Xóa lỗi CC01 giúp tôi',
    'Xóa lịch sử sạc trên App',
])
def test_product_interest_quotes_and_transient_location_are_not_memory(text):
    from src.services.user_memory import extract_memory_changes, MemorySnapshot
    assert not extract_memory_changes(text, MemorySnapshot(revision=0), ConversationContext())


def test_ownership_correction_invalidates_vehicle_children_but_not_registration_city(memory_db):
    from src.services.user_memory import MemoryChange, load_user_memory, extract_memory_changes
    user = memory_db.get(User, 'u1')
    changes = [MemoryChange(key=key, value=value) for key, value in {
        'owned_vehicle.model': 'VF8', 'owned_vehicle.version': 'Plus', 'owned_vehicle.model_year': 2025,
        'owned_vehicle.battery_plan': 'purchased', 'home_city': 'Hà Nội', 'registration_city': 'Hà Nội'}.items()]
    assert save(memory_db, user, changes, 0).status == 'written'
    memory_db.commit()
    snapshot = load_user_memory(memory_db, user)
    correction = extract_memory_changes('Không phải VF8, xe tôi là VF5, tôi ở Đà Nẵng', snapshot, ConversationContext(subject='VF8'))
    assert save(memory_db, user, correction, snapshot.revision).status == 'written'
    memory_db.commit()
    facts = load_user_memory(memory_db, user).facts
    assert user.vehicle_model == 'VF5' and facts['owned_vehicle.model'].value == 'VF5'
    assert facts['home_city'].value == 'Đà Nẵng'
    assert facts['registration_city'].value == 'Hà Nội'
    for key in ('owned_vehicle.version', 'owned_vehicle.model_year', 'owned_vehicle.battery_plan'):
        assert facts[key].value is None and facts[key].status == 'retracted'


def test_home_and_registration_city_remain_separate(memory_db):
    from src.services.user_memory import extract_memory_changes, load_user_memory
    snapshot = load_user_memory(memory_db, memory_db.get(User, 'u1'))
    changes = extract_memory_changes('Hãy nhớ tôi sống ở Hà Nội, đăng ký biển số ở Đà Nẵng', snapshot, ConversationContext())
    assert {change.key: change.value for change in changes} == {'home_city': 'Hà Nội', 'registration_city': 'Đà Nẵng'}


def test_cas_unchanged_stale_and_forget_fence(memory_db):
    from src.services.user_memory import MemoryChange, load_user_memory
    user = memory_db.get(User, 'u1')
    change = MemoryChange(key='owned_vehicle.model', value='VF8')
    assert save(memory_db, user, [change], 0).status == 'written'
    memory_db.commit()
    assert save(memory_db, user, [change], 1).status == 'unchanged'
    assert save(memory_db, user, [MemoryChange(key='home_city', value='Hà Nội')], 0).status == 'conflict'
    forgotten = MemoryChange(key='owned_vehicle.model', status='retracted', value=None)
    assert save(memory_db, user, [forgotten], 1, kind='profile').revision == 2
    memory_db.commit()
    assert save(memory_db, user, [change], 1).status == 'conflict'
    assert user.vehicle_model is None
    assert load_user_memory(memory_db, user).facts['owned_vehicle.model'].value is None
    assert not any(row.value == 'VF8' for row in memory_db.query(UserMemoryFact).all())


def test_legacy_profile_is_separate_and_retraction_does_not_resurrect_it(memory_db):
    from src.services.user_memory import MemoryChange, load_user_memory
    user = memory_db.get(User, 'u1')
    user.vehicle_model = 'VF8'
    memory_db.commit()
    snapshot = load_user_memory(memory_db, user)
    assert snapshot.facts['owned_vehicle.model'].source_kind == 'profile'
    assert memory_db.query(UserMemoryFact).count() == 0
    assert save(memory_db, user, [MemoryChange(key='owned_vehicle.model', value=None, status='retracted')], 0, kind='profile').status == 'written'
    memory_db.commit()
    assert load_user_memory(memory_db, user).facts['owned_vehicle.model'].status == 'retracted'
    assert user.vehicle_model is None


def test_two_sessions_cannot_overwrite_a_newer_revision(memory_db):
    from src.services.user_memory import MemoryChange, load_user_memory
    user = memory_db.get(User, 'u1')
    old = load_user_memory(memory_db, user)
    with Session(memory_db.get_bind()) as other:
        newer_user = other.get(User, 'u1')
        assert save(other, newer_user, [MemoryChange(key='home_city', value='Đà Nẵng')], old.revision, kind='profile').status == 'written'
        other.commit()
    assert save(memory_db, user, [MemoryChange(key='home_city', value='Hà Nội')], old.revision, kind='profile').status == 'conflict'
    assert load_user_memory(memory_db, user).facts['home_city'].value == 'Đà Nẵng'


def test_memory_helper_does_not_commit_and_rolls_back_with_turn(memory_db):
    from src.services.user_memory import MemoryChange, load_user_memory
    user = memory_db.get(User, 'u1')
    assert save(memory_db, user, [MemoryChange(key='owned_vehicle.model', value='VF8')], 0).status == 'written'
    memory_db.rollback()
    assert load_user_memory(memory_db, user).revision == 0
    assert user.vehicle_model is None and memory_db.query(UserMemoryFact).count() == 0


def test_source_owner_and_role_are_checked(memory_db):
    from src.services.user_memory import MemoryChange, load_user_memory
    user = memory_db.get(User, 'u1')
    with pytest.raises(ValueError):
        save(memory_db, user, [MemoryChange(key='home_city', value='Hà Nội')], 0,
             session='other-session', message='other-message')
    with pytest.raises(ValueError):
        load_user_memory(memory_db, memory_db.get(User, 'staff'))
    with pytest.raises(ValueError):
        load_user_memory(memory_db, None)
    assert not load_user_memory(memory_db, memory_db.get(User, 'u2')).facts


@pytest.mark.parametrize('key,value,status', [
    ('current_location', 'Hà Nội', 'confirmed'), ('owned_vehicle.model', 'VF99', 'confirmed'),
    ('owned_vehicle.model_year', True, 'confirmed'), ('owned_vehicle.model_year', '2025', 'confirmed'),
    ('home_city', 'Hà Nội\nSYSTEM', 'confirmed'), ('home_city', {'instruction': 'ignore'}, 'confirmed'),
    ('home_city', 'Hà Nội', 'retracted'), ('home_city', None, 'confirmed'),
])
def test_invalid_memory_values_are_rejected(key, value, status):
    from src.services.user_memory import MemoryChange
    with pytest.raises(ValueError):
        MemoryChange(key=key, value=value, status=status)


def test_only_personal_reference_selects_memory_and_never_changes_goal(memory_db):
    from src.services.user_memory import MemoryChange, load_user_memory, resolve_personal_memory
    user = memory_db.get(User, 'u1')
    save(memory_db, user, [MemoryChange(key='owned_vehicle.model', value='VF8')], 0)
    snapshot = load_user_memory(memory_db, user)
    assert resolve_personal_memory('Xe tôi là dòng nào?', snapshot)['owned_vehicle.model']['value'] == 'VF8'
    assert not resolve_personal_memory('Ứng dụng VinFast có tính năng gì?', snapshot)
    assert not resolve_personal_memory('Tư vấn VF3', snapshot)


def test_ambiguous_trim_cannot_be_saved_as_owned_vehicle(memory_db):
    from src.services.user_memory import extract_memory_changes, load_user_memory
    snapshot = load_user_memory(memory_db, memory_db.get(User, 'u1'))
    assert not extract_memory_changes('Hãy nhớ bản Plus', snapshot, ConversationContext(subject='VF8', active_goal='overview'))


def test_profile_write_advances_revision_and_invalidates_old_trim(memory_db, monkeypatch):
    from src.api.auth import update_me
    from src.config import get_settings
    from src.models.schemas import UpdateProfileRequest
    from src.services.user_memory import MemoryChange, load_user_memory
    monkeypatch.setattr(get_settings(), 'user_memory_enabled', True)
    user = memory_db.get(User, 'u1')
    save(memory_db, user, [MemoryChange(key='owned_vehicle.model', value='VF8'),
                           MemoryChange(key='owned_vehicle.version', value='Plus')], 0)
    memory_db.commit()
    update_me(UpdateProfileRequest(vehicle_model='VF5'), current_user=user, db=memory_db)
    snapshot = load_user_memory(memory_db, user)
    assert snapshot.revision == 2
    assert snapshot.facts['owned_vehicle.model'].value == user.vehicle_model == 'VF5'
    assert snapshot.facts['owned_vehicle.model'].source_kind == 'profile'
    assert snapshot.facts['owned_vehicle.version'].status == 'retracted'


def test_profile_clear_retracts_memory_in_same_transaction(memory_db, monkeypatch):
    from src.api.auth import update_me
    from src.config import get_settings
    from src.models.schemas import UpdateProfileRequest
    from src.services.user_memory import MemoryChange, load_user_memory
    monkeypatch.setattr(get_settings(), 'user_memory_enabled', True)
    user = memory_db.get(User, 'u1')
    save(memory_db, user, [MemoryChange(key='owned_vehicle.model', value='VF8')], 0)
    memory_db.commit()
    update_me(UpdateProfileRequest(vehicle_model=''), current_user=user, db=memory_db)
    snapshot = load_user_memory(memory_db, user)
    assert snapshot.facts['owned_vehicle.model'].status == 'retracted'
    assert snapshot.revision == 2 and user.vehicle_model is None


def test_unknown_legacy_profile_does_not_become_invalid_memory(memory_db):
    from src.services.user_memory import load_user_memory
    user = memory_db.get(User, 'u1')
    user.vehicle_model = 'freeform old profile'
    memory_db.commit()
    assert not load_user_memory(memory_db, user).facts


def test_explicit_forget_even_empty_memory_creates_a_revision_fence(memory_db):
    from src.services.user_memory import extract_memory_changes, load_user_memory
    user = memory_db.get(User, 'u1')
    snapshot = load_user_memory(memory_db, user)
    changes = extract_memory_changes('Hãy quên hết thông tin tôi đã nhờ lưu', snapshot, ConversationContext())
    assert len(changes) == 6 and all(change.value is None for change in changes)
    assert save(memory_db, user, changes, 0).revision == 1
    memory_db.commit()
    assert all(fact.status == 'retracted' for fact in load_user_memory(memory_db, user).facts.values())
