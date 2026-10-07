from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from src.config import get_settings


def test_chat_migration_preserves_existing_case_and_round_trips(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setattr(get_settings(), 'database_url', url)
    config = Config('alembic.ini')
    command.upgrade(config, '777b44e9e4d6')
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO cases(id,session_id,intent,priority,status,created_at,updated_at) VALUES ('existing','existing-session','Service/Incident','CRITICAL','In Progress',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
    command.upgrade(config, 'head')
    with engine.connect() as db:
        row = db.execute(text('SELECT * FROM cases WHERE id=\'existing\'')).mappings().one()
        assert row['safety_status'] == 'unconfirmed' and row['incident_version'] == 1
        assert row['priority'] == 'CRITICAL' and row['status'] == 'In Progress'
    assert {'chat_sessions', 'chat_request_records'} <= set(inspect(engine).get_table_names())
    command.downgrade(config, '777b44e9e4d6')
    assert 'chat_sessions' not in inspect(engine).get_table_names()
    with engine.connect() as db:
        assert db.execute(text("SELECT count(*) FROM cases WHERE id='existing'")).scalar() == 1
    command.upgrade(config, 'head')
    engine.dispose()
