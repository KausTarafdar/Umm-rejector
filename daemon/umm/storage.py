"""SQLite persistence: sessions, transcripts, filler events, daily aggregates."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from . import config

DB_PATH: Path = config.DATA_DIR / "umm.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    duration_secs REAL NOT NULL,
    question TEXT NOT NULL,
    transcript TEXT NOT NULL,
    report_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS filler_events (
    session_id TEXT NOT NULL REFERENCES sessions(id),
    label TEXT NOT NULL,
    t_start REAL NOT NULL,
    t_end REAL NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_session(session_id: str, started_at: str, duration_secs: float, question: str, report: dict) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, started_at, duration_secs, question, transcript, report_json) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, started_at, duration_secs, question, report["transcript"], json.dumps(report)),
        )
        conn.executemany(
            "INSERT INTO filler_events (session_id, label, t_start, t_end) VALUES (?, ?, ?, ?)",
            [(session_id, e["label"], e["t_start"], e["t_end"]) for e in report["filler_events"]],
        )


def history(limit: int = 50) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, started_at, duration_secs, question, report_json FROM sessions ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {**dict(r), "report": json.loads(r.pop("report_json"))} for r in rows
    ]


def trends() -> dict:
    with connect() as conn:
        rows = conn.execute(
            "SELECT date(started_at) AS day, AVG(json_extract(report_json, '$.fillers_per_minute')) AS avg_fpm, COUNT(*) AS sessions FROM sessions GROUP BY day ORDER BY day"
        ).fetchall()
    return {"days": [dict(r) for r in rows]}


def heatmap() -> dict:
    with connect() as conn:
        rows = conn.execute(
            "SELECT label, COUNT(*) AS count FROM filler_events GROUP BY label ORDER BY count DESC"
        ).fetchall()
    return {"phrases": [dict(r) for r in rows]}
