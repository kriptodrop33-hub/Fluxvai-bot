"""SQLite-backed persistence: conversation sessions, message dedupe, pending generations.

Why sqlite (stdlib) over a JSON file: the webhook handler, the polling task, and the
/internal/notify endpoint all write concurrently. A JSON read-modify-write races and
loses data; sqlite gives atomic transactions and a one-line UNIQUE dedupe. A fresh
connection is opened per call (cheap, thread-safe) with WAL for concurrent readers.
"""
import json
import os
import sqlite3
import time
from contextlib import contextmanager

_DB_PATH: str | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
  phone           TEXT PRIMARY KEY,
  state           TEXT NOT NULL DEFAULT 'UNLINKED',
  context         TEXT NOT NULL DEFAULT '{}',
  last_inbound_ts REAL NOT NULL DEFAULT 0,
  updated_at      REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS seen_messages(
  wamid   TEXT PRIMARY KEY,
  seen_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS pending_generations(
  gen_id     TEXT PRIMARY KEY,
  phone      TEXT NOT NULL,
  jwt        TEXT NOT NULL,
  started_at REAL NOT NULL,
  done       INTEGER NOT NULL DEFAULT 0
);
"""


def init(db_path: str) -> None:
    global _DB_PATH
    _DB_PATH = db_path
    parent = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(parent, exist_ok=True)
    with _connect() as c:
        c.executescript(_SCHEMA)


@contextmanager
def _connect():
    assert _DB_PATH, "store.init() must be called first"
    conn = sqlite3.connect(_DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        yield conn
        conn.commit()
    finally:
        conn.close()


# ── sessions ──────────────────────────────────────────────────────────
def get_session(phone: str) -> dict:
    with _connect() as c:
        row = c.execute(
            "SELECT state, context, last_inbound_ts FROM sessions WHERE phone=?", (phone,)
        ).fetchone()
    if not row:
        return {"state": "UNLINKED", "context": {}, "last_inbound_ts": 0.0}
    return {
        "state": row["state"],
        "context": json.loads(row["context"] or "{}"),
        "last_inbound_ts": row["last_inbound_ts"],
    }


def set_session(phone: str, state: str, context: dict) -> None:
    now = time.time()
    with _connect() as c:
        c.execute(
            """INSERT INTO sessions(phone, state, context, updated_at)
               VALUES(?,?,?,?)
               ON CONFLICT(phone) DO UPDATE SET
                 state=excluded.state, context=excluded.context, updated_at=excluded.updated_at""",
            (phone, state, json.dumps(context, ensure_ascii=False), now),
        )


def touch_last_inbound(phone: str) -> None:
    now = time.time()
    with _connect() as c:
        c.execute(
            """INSERT INTO sessions(phone, last_inbound_ts, updated_at)
               VALUES(?,?,?)
               ON CONFLICT(phone) DO UPDATE SET last_inbound_ts=excluded.last_inbound_ts""",
            (phone, now, now),
        )


def get_last_inbound(phone: str) -> float:
    with _connect() as c:
        row = c.execute("SELECT last_inbound_ts FROM sessions WHERE phone=?", (phone,)).fetchone()
    return row["last_inbound_ts"] if row else 0.0


# ── inbound message dedupe ────────────────────────────────────────────
def mark_seen(wamid: str) -> bool:
    """Return True if this wamid is new (first time seen), False if a duplicate."""
    if not wamid:
        return True
    with _connect() as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO seen_messages(wamid, seen_at) VALUES(?,?)", (wamid, time.time())
        )
        return cur.rowcount == 1


# ── pending generations (survive restarts) ───────────────────────────
def add_pending(gen_id: str, phone: str, jwt: str) -> None:
    with _connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO pending_generations(gen_id, phone, jwt, started_at, done) VALUES(?,?,?,?,0)",
            (gen_id, phone, jwt, time.time()),
        )


def complete_pending(gen_id: str) -> None:
    with _connect() as c:
        c.execute("UPDATE pending_generations SET done=1 WHERE gen_id=?", (gen_id,))


def list_pending() -> list[dict]:
    with _connect() as c:
        rows = c.execute(
            "SELECT gen_id, phone, jwt, started_at FROM pending_generations WHERE done=0"
        ).fetchall()
    return [dict(r) for r in rows]
