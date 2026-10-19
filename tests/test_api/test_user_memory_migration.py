import os
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from src.config import Settings, get_settings


@pytest.fixture(params=['sqlite', 'postgresql'])
def memory_migration_url(request, tmp_path, monkeypatch):
    if request.param == 'sqlite':
        url = f'sqlite:///{tmp_path / "memory-migration.db"}'
        monkeypatch.setattr(get_settings(), 'database_url', url)
        yield url
        return
    value = os.getenv('TEST_POSTGRES_URL')
    if not value:
        pytest.skip('BLOCKED: TEST_POSTGRES_URL dedicated test database not configured')
    parsed = make_url(value)
    assert parsed.get_backend_name() == 'postgresql' and 'test' in (parsed.database or '').lower()
    schema = 'memory_test_' + uuid4().hex
    admin = sa.create_engine(parsed)
    with admin.begin() as connection:
        connection.execute(sa.schema.CreateSchema(schema))
    url = parsed.update_query_dict({'options': '-csearch_path=' + schema}).render_as_string(hide_password=False)
    monkeypatch.setattr(get_settings(), 'database_url', url)
    try:
        yield url
    finally:
        with admin.begin() as connection:
            connection.execute(sa.schema.DropSchema(schema, cascade=True))
        admin.dispose()


def test_additive_memory_migration_preserves_legacy_and_does_not_backfill(memory_migration_url):
    config = Config('alembic.ini')
    command.upgrade(config, '3d01_service_points')
    engine = sa.create_engine(memory_migration_url)
    if engine.dialect.name == 'sqlite':
        @sa.event.listens_for(engine, 'connect')
        def sqlite_foreign_keys(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')
    try:
        with engine.begin() as connection:
            connection.execute(sa.text("INSERT INTO users(id,username,password_hash,role,vehicle_model,created_at) VALUES ('memory-user','memory-user','unused','CUSTOMER','VF8',CURRENT_TIMESTAMP)"))
            sessions = sa.Table('chat_sessions', sa.MetaData(), autoload_with=engine)
            connection.execute(sessions.insert().values(id='legacy-session', owner='memory-user', memory_states={'legacy-session': {'messages': ['old transcript']}}))
            connection.execute(sa.text("INSERT INTO cases(id,session_id,intent,priority,status,created_at,updated_at) VALUES ('legacy-case','legacy-session','Service/Incident','HIGH','In Progress',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        command.upgrade(config, 'head')
        assert 'user_memory_facts' in sa.inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert connection.execute(sa.text("SELECT memory_revision FROM users WHERE id='memory-user'")).scalar_one() == 0
            assert connection.execute(sa.text("SELECT vehicle_model FROM users WHERE id='memory-user'")).scalar_one() == 'VF8'
            assert connection.execute(sa.text('SELECT count(*) FROM user_memory_facts')).scalar_one() == 0
            assert connection.execute(sa.text("SELECT count(*) FROM chat_sessions WHERE id='legacy-session'")).scalar_one() == 1
            assert connection.execute(sa.text("SELECT status FROM cases WHERE id='legacy-case'")).scalar_one() == 'In Progress'
        facts = sa.Table('user_memory_facts', sa.MetaData(), autoload_with=engine)
        value = {'user_id': 'memory-user', 'key': 'owned_vehicle.model', 'value': 'VF8',
                 'status': 'confirmed', 'source_kind': 'chat', 'source_session_id': 'legacy-session'}
        with engine.begin() as connection:
            connection.execute(facts.insert().values(**value))
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(facts.insert().values(**value))
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(facts.insert().values(**{**value, 'key': 'current_location'}))
        with engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM users WHERE id='memory-user'"))
            assert connection.execute(sa.text('SELECT count(*) FROM user_memory_facts')).scalar_one() == 0
        command.downgrade(config, '3d01_service_points')
        assert 'user_memory_facts' not in sa.inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert connection.execute(sa.text("SELECT count(*) FROM cases WHERE id='legacy-case'")).scalar_one() == 1
        command.upgrade(config, 'head')
    finally:
        engine.dispose()


def test_orm_memory_schema_and_feature_default_off():
    from src.models.db_models import User, UserMemoryFact
    assert Settings(_env_file=None).user_memory_enabled is False
    assert User.memory_revision.property.columns[0].server_default is not None
    assert {column.name for column in UserMemoryFact.__table__.primary_key} == {'user_id', 'key'}
