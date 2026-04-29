"""SQLite store for run history and phase tracking."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "kms.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic TEXT NOT NULL,
  status TEXT NOT NULL,
  current_phase INTEGER,
  notion_url TEXT,
  error TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS run_phases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  phase_num INTEGER NOT NULL,
  phase_name TEXT NOT NULL,
  status TEXT NOT NULL,
  sub_progress TEXT,
  payload_json TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE INDEX IF NOT EXISTS idx_phases_run ON run_phases(run_id);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def start_run(topic: str) -> int:
    with connect() as c:
        cur = c.execute(
            "INSERT INTO runs (topic, status, started_at) VALUES (?, 'running', ?)",
            (topic, now()),
        )
        return cur.lastrowid


def finish_run(
    run_id: int,
    status: str,
    notion_url: str | None = None,
    error: str | None = None,
) -> None:
    with connect() as c:
        c.execute(
            "UPDATE runs SET status=?, finished_at=?, notion_url=?, error=? WHERE id=?",
            (status, now(), notion_url, error, run_id),
        )


def start_phase(run_id: int, num: int, name: str) -> int:
    with connect() as c:
        cur = c.execute(
            "INSERT INTO run_phases (run_id, phase_num, phase_name, status, started_at) "
            "VALUES (?, ?, ?, 'running', ?)",
            (run_id, num, name, now()),
        )
        c.execute("UPDATE runs SET current_phase=? WHERE id=?", (num, run_id))
        return cur.lastrowid


def finish_phase(
    phase_id: int,
    status: str,
    payload: dict | None = None,
) -> None:
    with connect() as c:
        c.execute(
            "UPDATE run_phases SET status=?, finished_at=?, payload_json=? WHERE id=?",
            (
                status,
                now(),
                json.dumps(payload, ensure_ascii=False) if payload else None,
                phase_id,
            ),
        )


def update_sub_progress(phase_id: int, text: str) -> None:
    with connect() as c:
        c.execute("UPDATE run_phases SET sub_progress=? WHERE id=?", (text, phase_id))


def list_runs(limit: int = 50) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_run(run_id: int) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            return None
        run = dict(row)
        phases = c.execute(
            "SELECT * FROM run_phases WHERE run_id=? ORDER BY phase_num", (run_id,)
        ).fetchall()
        run["phases"] = [
            {**dict(p), "payload": json.loads(p["payload_json"]) if p["payload_json"] else None}
            for p in phases
        ]
        return run


def get_active_run() -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT * FROM runs WHERE status='running' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
