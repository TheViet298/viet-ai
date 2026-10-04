"""Transactional SQLite session state, private cases and durable traces."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from langchain_core.messages import messages_from_dict, messages_to_dict

from src.config import get_settings


class SessionConflictError(ValueError):
    pass


def now() -> str:
    return datetime.now(UTC).isoformat()


def encode_state(state: dict) -> str:
    persistent = {k: v for k, v in state.items() if k != "llm_budget"}
    return json.dumps({**persistent, "messages": messages_to_dict(state.get("messages", []))}, ensure_ascii=False)


def decode_state(value: str) -> dict:
    data = json.loads(value)
    data["messages"] = messages_from_dict(data.get("messages", []))
    return data


class SessionStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, role TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT '{}', guest_turns INTEGER NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, customer_id TEXT NOT NULL,
                    intent TEXT NOT NULL, priority TEXT NOT NULL, status TEXT NOT NULL,
                    routing TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS case_briefs (
                    case_id TEXT PRIMARY KEY REFERENCES cases(id), data TEXT NOT NULL, generated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, case_id TEXT,
                    sender_type TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS agent_traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS case_updates (
                    id TEXT PRIMARY KEY, case_id TEXT NOT NULL, actor TEXT NOT NULL,
                    status TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS trace_session_idx ON agent_traces(session_id, id);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def claim(self, session_id: str, owner: str, role: str, emergency: bool = False) -> tuple[dict, int]:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT OR IGNORE INTO agent_sessions(id,owner,role,updated_at) VALUES(?,?,?,?)",
                (session_id, owner, role, now()),
            )
            row = db.execute("SELECT * FROM agent_sessions WHERE id=?", (session_id,)).fetchone()
            if row["owner"] != owner or row["role"] != role:
                raise PermissionError("Session belongs to another principal")
            if role == "guest" and row["guest_turns"] >= 5 and not emergency:
                raise PermissionError("Guest quota reached; sign in to continue")
            count, version = row["guest_turns"] + int(role == "guest"), row["version"] + 1
            db.execute(
                "UPDATE agent_sessions SET guest_turns=?,version=?,updated_at=? WHERE id=?",
                (count, version, now(), session_id),
            )
            state = decode_state(row["state"])
            state.update(session_id=session_id, user_role=role, guest_turn_count=count)
            return state, version

    def save_turn(self, session_id: str, owner: str, version: int, state: dict) -> dict:
        data = dict(state)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM agent_sessions WHERE id=?", (session_id,)).fetchone()
            if not row or row["owner"] != owner or row["version"] != version:
                raise SessionConflictError("Session changed during processing; retry the turn")
            if data.get("case_brief") and data.get("needs_staff_review") and row["role"] == "customer" and not data.get("is_rag_query"):
                cid = data.get("case_id")
                existing = db.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone() if cid else None
                if existing and existing["customer_id"] != owner:
                    raise PermissionError("Case belongs to another customer")
                if existing and existing["status"] in ("Closed", "Resolved"):
                    cid, existing = None, None
                today_str = datetime.now(UTC).strftime("%Y%m%d")
                count = db.execute("SELECT COUNT(*) FROM cases WHERE id LIKE ?", (f"CASE-{today_str}-%",)).fetchone()[0] or 0
                cid = cid or f"CASE-{today_str}-{count + 1:03d}"
                data["case_id"] = cid
                status = data.get("ticket_status", "Staff Reviewing")
                if existing:
                    # Agent updates must not undo staff actions or lower an active case's priority.
                    status = (
                        "Staff Reviewing"
                        if existing["status"] == "Needs Information" and status == "Staff Reviewing"
                        else existing["status"]
                    )
                    levels = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
                    data["priority"] = max(
                        (existing["priority"], data.get("priority", "MEDIUM")), key=levels.__getitem__
                    )
                data["ticket_status"] = status
                if not existing:
                    db.execute(
                        "INSERT INTO cases VALUES(?,?,?,?,?,?,?,?,?)",
                        (
                            cid,
                            session_id,
                            owner,
                            data.get("intent") or "Service/Incident",
                            data.get("priority", "MEDIUM"),
                            "New",
                            data.get("routing", "customer_relations"),
                            now(),
                            now(),
                        ),
                    )
                    db.execute("INSERT INTO case_updates VALUES(?,?,?,?,?)", (uuid4().hex, cid, "SYSTEM", "New", now()))
                db.execute(
                    "UPDATE cases SET status=?,priority=?,routing=?,updated_at=? WHERE id=?",
                    (status, data.get("priority", "MEDIUM"), data.get("routing", "customer_relations"), now(), cid),
                )
                if not existing or existing["status"] != status:
                    db.execute(
                        "INSERT INTO case_updates VALUES(?,?,?,?,?)", (uuid4().hex, cid, "SYSTEM", status, now())
                    )
                db.execute(
                    "INSERT OR REPLACE INTO case_briefs VALUES(?,?,?)",
                    (cid, json.dumps(data["case_brief"], ensure_ascii=False), now()),
                )
                db.execute("UPDATE messages SET case_id=? WHERE session_id=? AND case_id IS NULL", (cid, session_id))
            for sender, content in (
                ("CUSTOMER", data.get("latest_user_message", "")),
                ("AGENT", data.get("response", "")),
            ):
                db.execute(
                    "INSERT INTO messages VALUES(?,?,?,?,?,?)",
                    (uuid4().hex, session_id, data.get("case_id"), sender, content, now()),
                )
            db.execute(
                "UPDATE agent_sessions SET state=?,updated_at=? WHERE id=?", (encode_state(data), now(), session_id)
            )
        return data

    def case(self, case_id: str, owner: str | None = None) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            if not row:
                raise KeyError(case_id)
            if owner is not None and row["customer_id"] != owner:
                raise PermissionError("Case belongs to another customer")
            result = dict(row)
            brief = db.execute("SELECT data FROM case_briefs WHERE case_id=?", (case_id,)).fetchone()
            result["case_brief"] = json.loads(brief["data"]) if brief else None
            result["messages"] = [
                dict(r) for r in db.execute("SELECT * FROM messages WHERE case_id=? ORDER BY created_at,id", (case_id,))
            ]
            return result

    def list_cases(self, owner: str | None = None) -> list[dict]:
        with self.connect() as db:
            rows = (
                db.execute("SELECT * FROM cases WHERE customer_id=? ORDER BY updated_at DESC", (owner,))
                if owner
                else db.execute("SELECT * FROM cases ORDER BY updated_at DESC")
            )
            return [dict(row) for row in rows]

    def change_status(self, case_id: str, status: str, actor: str, owner: str | None = None) -> dict:
        transitions = {
            "New": {"Staff Reviewing", "Needs Information"},
            "Needs Information": {"Staff Reviewing", "In Progress"},
            "Staff Reviewing": {"In Progress", "Needs Information"},
            "In Progress": {"Resolved", "Needs Information"},
            "Resolved": {"Closed", "Reopened"},
            "Reopened": {"Staff Reviewing", "In Progress", "Needs Information"},
            "Closed": set(),
        }
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            if not row:
                raise KeyError(case_id)
            if owner is not None and row["customer_id"] != owner:
                raise PermissionError("Case belongs to another customer")
            if status not in transitions.get(row["status"], set()):
                raise ValueError(f"Invalid transition {row['status']} -> {status}")
            db.execute("UPDATE cases SET status=?,updated_at=? WHERE id=?", (status, now(), case_id))
            db.execute("INSERT INTO case_updates VALUES(?,?,?,?,?)", (uuid4().hex, case_id, actor, status, now()))
            session = db.execute("SELECT state FROM agent_sessions WHERE id=?", (row["session_id"],)).fetchone()
            if session:
                state = decode_state(session["state"])
                if state.get("case_id") == case_id:
                    state["ticket_status"] = status
                    db.execute(
                        "UPDATE agent_sessions SET state=?,version=version+1 WHERE id=?",
                        (encode_state(state), row["session_id"]),
                    )
        return self.case(case_id, owner)

    def record_trace(self, event: dict) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO agent_traces(session_id,data) VALUES(?,?)",
                (event["session_id"], json.dumps(event, ensure_ascii=False, default=str)),
            )
            db.execute(
                "DELETE FROM agent_traces WHERE session_id=? AND id NOT IN (SELECT id FROM agent_traces WHERE session_id=? ORDER BY id DESC LIMIT 1000)",
                (event["session_id"], event["session_id"]),
            )

    def replay(self, session_id: str) -> list[dict]:
        with self.connect() as db:
            return [
                json.loads(row["data"])
                for row in db.execute("SELECT data FROM agent_traces WHERE session_id=? ORDER BY id", (session_id,))
            ]


def get_store() -> SessionStore:
    url = get_settings().database_url
    if not url.startswith("sqlite:///"):
        raise ValueError("Agent store requires sqlite:/// database URL")
    # Backend ORM tables use a different schema for cases/messages.
    backend_path = Path(url.removeprefix("sqlite:///"))
    agent_path = backend_path.with_name(f"{backend_path.stem}.agent{backend_path.suffix}")
    return SessionStore(agent_path)
