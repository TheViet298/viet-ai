"""SQLite storage for the demo case lifecycle.

The default connection is in memory. File-backed databases are opened only when
the file already exists, so starting the app cannot silently create app.db.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StoreError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class CaseStore:
    def __init__(self, database_url: str = "sqlite:///:memory:"):
        if database_url == "sqlite:///:memory:":
            database = ":memory:"
            uri = False
        elif database_url.startswith("sqlite:///"):
            path = Path(database_url.removeprefix("sqlite:///"))
            if not path.is_file():
                raise ValueError(f"Database file does not exist: {path}")
            database = f"file:{path.resolve()}?mode=rw"
            uri = True
        else:
            raise ValueError("Only SQLite databases are supported")
        self.connection = sqlite3.connect(database, check_same_thread=False, uri=uri)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.lock = RLock()
        with self.connection:
            self.connection.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    clarification_turn INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    mock_customer_id TEXT,
                    vehicle_model TEXT,
                    vehicle_code_mock TEXT,
                    intent TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source_channel TEXT NOT NULL DEFAULT 'WEB_CHAT',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    case_id TEXT REFERENCES cases(id),
                    sender TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS case_briefs (
                    case_id TEXT PRIMARY KEY REFERENCES cases(id),
                    brief TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    case_id TEXT REFERENCES cases(id),
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    from_status TEXT,
                    to_status TEXT,
                    reason TEXT,
                    created_at TEXT NOT NULL
                );
            """)

    def close(self):
        self.connection.close()

    def _audit(self, case_id, actor, action, before=None, after=None, reason=None):
        event_id = str(uuid4())
        self.connection.execute(
            "INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, case_id, actor, action, before, after, reason, now()),
        )
        return event_id

    def _message(self, session_id, case_id, sender, content):
        self.connection.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid4()), session_id, case_id, sender, content, now()),
        )

    def prepare_chat(self, session_id: str, message: str) -> tuple[int, list[str]]:
        with self.lock, self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO sessions VALUES (?, 0, ?)", (session_id, now())
            )
            self._message(session_id, None, "CUSTOMER", message)
            rows = self.connection.execute(
                "SELECT content FROM messages WHERE session_id=? AND case_id IS NULL AND sender='CUSTOMER' ORDER BY rowid",
                (session_id,),
            ).fetchall()
            turn = self.connection.execute(
                "SELECT clarification_turn FROM sessions WHERE id=?", (session_id,)
            ).fetchone()[0]
            return turn, [row[0] for row in rows]

    def clarify(self, session_id: str, message: str) -> int:
        with self.lock, self.connection:
            self.connection.execute(
                "UPDATE sessions SET clarification_turn=clarification_turn+1 WHERE id=?",
                (session_id,),
            )
            self._message(session_id, None, "AGENT", message)
            return self.connection.execute(
                "SELECT clarification_turn FROM sessions WHERE id=?", (session_id,)
            ).fetchone()[0]

    def create_case(self, session_id, context, intent, priority, status, brief, customer_message):
        case_id = f"CASE-{uuid4().hex[:12].upper()}"
        timestamp = now()
        with self.lock, self.connection:
            self.connection.execute(
                "INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'WEB_CHAT', ?, ?)",
                (case_id, session_id, context.mock_customer_id, context.vehicle_model,
                 context.vehicle_code_mock, intent, priority, "New", timestamp, timestamp),
            )
            self.connection.execute(
                "INSERT INTO case_briefs VALUES (?, ?, ?)",
                (case_id, json.dumps(brief, ensure_ascii=False), timestamp),
            )
            self.connection.execute(
                "UPDATE messages SET case_id=? WHERE session_id=? AND case_id IS NULL",
                (case_id, session_id),
            )
            self._audit(case_id, "SYSTEM", "CREATE", None, "New")
            self.connection.execute(
                "UPDATE cases SET status=?, updated_at=? WHERE id=?", (status, now(), case_id)
            )
            self._audit(case_id, "SYSTEM", "TRIAGE", "New", status)
            self._message(session_id, case_id, "AGENT", customer_message)
        return self.get_case(case_id)

    def get_case(self, case_id: str):
        with self.lock:
            row = self.connection.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            return dict(row) if row else None

    def require_case(self, case_id: str, session_id: str | None = None):
        case = self.get_case(case_id)
        if case is None:
            raise StoreError("NOT_FOUND", "Case not found")
        if session_id is not None and case["session_id"] != session_id:
            raise StoreError("FORBIDDEN", "Case does not belong to this session")
        return case

    def get_brief(self, case_id: str):
        with self.lock:
            row = self.connection.execute(
                "SELECT brief FROM case_briefs WHERE case_id=?", (case_id,)
            ).fetchone()
            return json.loads(row[0]) if row else None

    def list_cases(self, status=None, priority=None):
        with self.lock:
            rows = self.connection.execute(
                "SELECT * FROM cases WHERE (? IS NULL OR status=?) AND (? IS NULL OR priority=?) ORDER BY created_at DESC",
                (status, status, priority, priority),
            ).fetchall()
            return [dict(row) for row in rows]

    def detail(self, case_id: str):
        case = self.require_case(case_id)
        with self.lock:
            messages = [dict(row) for row in self.connection.execute(
                "SELECT sender, content, created_at FROM messages WHERE case_id=? ORDER BY rowid",
                (case_id,),
            ).fetchall()]
            audit = [dict(row) for row in self.connection.execute(
                "SELECT id, actor, action, from_status, to_status, reason, created_at FROM audit_logs WHERE case_id=? ORDER BY rowid",
                (case_id,),
            ).fetchall()]
        return {"case": case, "case_brief": self.get_brief(case_id),
                "conversation_history": messages, "audit": audit}

    def record_read(self, case_id: str, actor: str, action: str):
        with self.lock, self.connection:
            self._audit(case_id, actor, action)

    def add_case_message(self, case_id: str, session_id: str, content: str):
        case = self.require_case(case_id, session_id)
        if case["status"] not in {"Needs Information", "Staff Reviewing"}:
            raise StoreError("INVALID_TRANSITION", "Case is not accepting customer updates")
        with self.lock, self.connection:
            self._message(session_id, case_id, "CUSTOMER", content)
            self._audit(case_id, f"CUSTOMER:{session_id}", "ADD_MESSAGE", case["status"], case["status"])
        if case["status"] == "Needs Information":
            return self.transition(case_id, {"Needs Information"}, "Staff Reviewing",
                                   f"CUSTOMER:{session_id}", "PROVIDE_INFO")
        return self.get_case(case_id), None

    def transition(self, case_id, allowed_from, to_status, actor, action, reason=None, brief=None):
        with self.lock, self.connection:
            case = self.require_case(case_id)
            if case["status"] not in allowed_from:
                raise StoreError("INVALID_TRANSITION", f"{action} is invalid from {case['status']}")
            if brief is not None:
                self.connection.execute(
                    "UPDATE case_briefs SET brief=?, updated_at=? WHERE case_id=?",
                    (json.dumps(brief, ensure_ascii=False), now(), case_id),
                )
            self.connection.execute(
                "UPDATE cases SET status=?, updated_at=? WHERE id=?",
                (to_status, now(), case_id),
            )
            event = self._audit(case_id, actor, action, case["status"], to_status, reason)
            return self.get_case(case_id), event
