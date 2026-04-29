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

CREATE TABLE IF NOT EXISTS run_step_inputs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  step_name TEXT NOT NULL,
  input_json TEXT NOT NULL,
  saved_at TEXT NOT NULL,
  UNIQUE(run_id, step_name),
  FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE INDEX IF NOT EXISTS idx_step_inputs_run ON run_step_inputs(run_id);

CREATE TABLE IF NOT EXISTS seen_sources (
  topic           TEXT NOT NULL,
  url_canonical   TEXT NOT NULL,
  url_original    TEXT NOT NULL,
  title           TEXT,
  source          TEXT,
  first_seen_at   TEXT NOT NULL,
  status          TEXT NOT NULL,
  score           INTEGER,
  notion_page_id  TEXT,
  run_id          INTEGER,
  PRIMARY KEY (topic, url_canonical)
);

CREATE INDEX IF NOT EXISTS idx_seen_topic ON seen_sources(topic);

CREATE TABLE IF NOT EXISTS topic_pages (
  topic                      TEXT PRIMARY KEY,
  notion_page_id             TEXT NOT NULL,
  last_updated_at            TEXT NOT NULL,
  source_count               INTEGER NOT NULL DEFAULT 0,
  draft_eligible_count       INTEGER NOT NULL DEFAULT 0,
  last_drafted_source_count  INTEGER NOT NULL DEFAULT 0
);
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


def save_step_input(run_id: int, step_name: str, data: dict) -> None:
    payload = json.dumps(data, ensure_ascii=False)
    with connect() as c:
        c.execute(
            "INSERT INTO run_step_inputs (run_id, step_name, input_json, saved_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(run_id, step_name) DO UPDATE SET "
            "input_json=excluded.input_json, saved_at=excluded.saved_at",
            (run_id, step_name, payload, now()),
        )


def get_step_input(run_id: int, step_name: str) -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT input_json FROM run_step_inputs WHERE run_id=? AND step_name=?",
            (run_id, step_name),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["input_json"])


def list_step_inputs(run_id: int) -> list[str]:
    with connect() as c:
        rows = c.execute(
            "SELECT step_name FROM run_step_inputs WHERE run_id=? ORDER BY id",
            (run_id,),
        ).fetchall()
        return [r["step_name"] for r in rows]


def get_topic_page(topic: str) -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT * FROM topic_pages WHERE topic=?", (topic,)
        ).fetchone()
        return dict(row) if row else None


def upsert_topic_page(
    topic: str,
    notion_page_id: str,
    source_count: int | None = None,
    draft_eligible_count: int | None = None,
    last_drafted_source_count: int | None = None,
) -> None:
    """Insert or update topic_pages. None fields are left untouched on update."""
    with connect() as c:
        existing = c.execute(
            "SELECT * FROM topic_pages WHERE topic=?", (topic,)
        ).fetchone()
        if existing is None:
            c.execute(
                "INSERT INTO topic_pages "
                "(topic, notion_page_id, last_updated_at, "
                " source_count, draft_eligible_count, last_drafted_source_count) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    topic,
                    notion_page_id,
                    now(),
                    source_count or 0,
                    draft_eligible_count or 0,
                    last_drafted_source_count or 0,
                ),
            )
            return
        merged_source = source_count if source_count is not None else existing["source_count"]
        merged_draft_elig = (
            draft_eligible_count
            if draft_eligible_count is not None
            else existing["draft_eligible_count"]
        )
        merged_last_drafted = (
            last_drafted_source_count
            if last_drafted_source_count is not None
            else existing["last_drafted_source_count"]
        )
        c.execute(
            "UPDATE topic_pages SET "
            "notion_page_id=?, last_updated_at=?, "
            "source_count=?, draft_eligible_count=?, last_drafted_source_count=? "
            "WHERE topic=?",
            (
                notion_page_id,
                now(),
                merged_source,
                merged_draft_elig,
                merged_last_drafted,
                topic,
            ),
        )


def get_active_run() -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT * FROM runs WHERE status='running' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
