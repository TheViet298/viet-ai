"""SQLite knowledge retrieval, conversations and local technical queue."""
import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def normalize(text):
    text = unicodedata.normalize("NFD", text.lower()).replace("đ", "d")
    return "".join(c for c in text if not unicodedata.combining(c))


def tokens(text):
    stop = {"toi", "em", "anh", "chi", "cua", "va", "la", "co", "cho", "mot", "muon", "can", "the", "nao", "ve", "gi", "tren", "tai", "thoi", "sao", "duoc", "den", "khi", "neu", "nhu", "thong", "tin", "lam", "su", "cach", "theo"}
    return set(re.findall(r"[a-z0-9]+", normalize(text))) - stop


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path, knowledge_path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, context TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, session_id TEXT, sender TEXT, text TEXT, created_at TEXT);
                CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, session_id TEXT, priority TEXT, summary TEXT, context TEXT, status TEXT, created_at TEXT, updated_at TEXT);
                CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, case_id TEXT, action TEXT, created_at TEXT);
            """)
            for item in json.loads(Path(knowledge_path).read_text()):
                db.execute("INSERT OR IGNORE INTO knowledge VALUES (?, ?)", (item["id"], json.dumps(item, ensure_ascii=False)))

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def context(self, session_id):
        with self.connect() as db:
            row = db.execute("SELECT context FROM sessions WHERE id=?", (session_id,)).fetchone()
        return json.loads(row[0]) if row else {}

    def save(self, session_id, context, user_message, assistant_message):
        with self.connect() as db:
            db.execute("INSERT INTO sessions VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET context=excluded.context", (session_id, json.dumps(context, ensure_ascii=False)))
            for sender, text in [("CUSTOMER", user_message), ("ASSISTANT", assistant_message)]:
                db.execute("INSERT INTO messages(session_id,sender,text,created_at) VALUES(?,?,?,?)", (session_id, sender, text, timestamp()))

    def retrieve(self, query, category, model=None, seats=None):
        query_tokens = tokens(query)
        with self.connect() as db:
            records = [json.loads(row[0]) for row in db.execute("SELECT payload FROM knowledge")]
        ranked = []
        for item in records:
            if item["category"] != category:
                continue
            if model and item.get("model") != model and category == "product":
                continue
            if seats and category == "product" and (item.get("seats") or 0) < seats:
                continue
            score = len(query_tokens & tokens(item["question"] + " " + item["text"]))
            if model and item.get("model") == model:
                score += 8
            if seats and item.get("seats") and item["seats"] >= seats:
                score += 5
                if item["seats"] == seats:
                    score += 2
            if score >= 2:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
        return [dict(item, score=score) for score, item in ranked[:2]]

    def create_case(self, session_id, priority, summary, context):
        case_id = "DEMO-" + uuid4().hex[:8].upper()
        now = timestamp()
        with self.connect() as db:
            db.execute("INSERT INTO cases VALUES (?,?,?,?,?,'WAITING',?,?)", (case_id, session_id, priority, summary[:5000], json.dumps(context, ensure_ascii=False), now, now))
            db.execute("INSERT INTO audit(case_id,action,created_at) VALUES(?,?,?)", (case_id, "CREATED", now))
        return case_id

    def cases(self):
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT * FROM cases ORDER BY CASE priority WHEN 'URGENT' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, created_at DESC")]

    def update_case(self, case_id, action):
        transitions = {"ACCEPT": ("WAITING", "IN_PROGRESS"), "RESOLVE": ("IN_PROGRESS", "RESOLVED")}
        if action not in transitions:
            raise ValueError("Hành động không hợp lệ")
        old, new = transitions[action]
        with self.connect() as db:
            count = db.execute("UPDATE cases SET status=?,updated_at=? WHERE id=? AND status=?", (new, timestamp(), case_id, old)).rowcount
            if not count:
                raise ValueError("Trạng thái hồ sơ đã thay đổi hoặc không tồn tại")
            db.execute("INSERT INTO audit(case_id,action,created_at) VALUES(?,?,?)", (case_id, action, timestamp()))
        return new
