import sqlite3

from src.config import get_settings
from src.services.session_store import get_store


def test_agent_turn_does_not_use_backend_messages_table(tmp_path, monkeypatch):
    backend_path = tmp_path / "backend.db"
    with sqlite3.connect(backend_path) as db:
        db.execute("CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT, case_id TEXT, sender_type TEXT, content TEXT, created_at TEXT, metadata TEXT)")
        db.execute("INSERT INTO messages VALUES ('backend-message', 'backend-session', NULL, 'CUSTOMER', 'existing', 'now', '{}')")
    monkeypatch.setattr(get_settings(), "database_url", f"sqlite:///{backend_path}")
    store = get_store()
    state, version = store.claim("agent-session", "guest:agent-session", "guest")
    state.update(latest_user_message="Hello", response="Hello")
    store.save_turn("agent-session", "guest:agent-session", version, state)
    with sqlite3.connect(backend_path) as db:
        assert db.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 1
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 2
