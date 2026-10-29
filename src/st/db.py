"""Database module for SurfaceTrace-IN.

Owned by Shreyash.
Uses SQLite in WAL mode with plain SQL. All timestamps stored in UTC ISO format.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Default path to database file
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "st.db"


def get_db_path() -> Path:
    """Resolve database path from environment or default."""
    custom = os.environ.get("DATABASE_PATH")
    if custom:
        return Path(custom)
    data_dir = os.environ.get("DATA_DIR")
    if data_dir:
        return Path(data_dir) / "st.db"
    return DEFAULT_DB_PATH


def get_conn(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Return a connection to the SQLite database in WAL mode.

    Sets row_factory to sqlite3.Row and turns on foreign keys.
    """
    path = Path(db_path) if db_path else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    """Initialize the database schema."""
    conn = get_conn(db_path)
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
              id INTEGER PRIMARY KEY,
              url TEXT UNIQUE NOT NULL,
              title TEXT,
              source TEXT NOT NULL,         -- 'seed' | 'web_search' | 'ahmia' | 'github' | 'rss'
              query TEXT,
              text TEXT,                    -- cleaned page text, max 20000 chars
              status TEXT NOT NULL DEFAULT 'new',  -- new | fetched | done | failed | blocked
              error TEXT,
              fetched_at TEXT               -- UTC ISO
            );

            CREATE TABLE IF NOT EXISTS onion_mentions (
              id INTEGER PRIMARY KEY,
              onion TEXT NOT NULL,          -- lowercase, ends with .onion, passed v3 checksum
              doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
              context TEXT NOT NULL,        -- max 300 chars
              UNIQUE (onion, doc_id)
            );

            CREATE TABLE IF NOT EXISTS leads (
              onion TEXT PRIMARY KEY,
              score INTEGER NOT NULL DEFAULT 0,          -- 0..100
              band TEXT NOT NULL DEFAULT 'low',          -- low | medium | high
              doc_count INTEGER NOT NULL DEFAULT 0,
              source_count INTEGER NOT NULL DEFAULT 0,
              review_status TEXT NOT NULL DEFAULT 'new', -- new | relevant | irrelevant | escalate
              reviewer TEXT,
              note TEXT,
              updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS runs (
              id INTEGER PRIMARY KEY,
              stage TEXT NOT NULL,          -- collect | fetch | extract | score
              started_at TEXT NOT NULL,
              finished_at TEXT,
              items INTEGER DEFAULT 0,
              error TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
            CREATE INDEX IF NOT EXISTS idx_mentions_onion ON onion_mentions(onion);
            CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
            """
        )
    conn.close()


def save_hits(hits: list[dict], db_path: Path | str | None = None) -> int:
    """Save collector search hits into documents table.

    hit = {"url": str, "title": str | None, "source": str, "query": str | None}
    Ignores duplicate URLs. Returns the number of newly inserted rows.
    """
    if not hits:
        return 0

    conn = get_conn(db_path)
    inserted = 0
    with conn:
        for hit in hits:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO documents (url, title, source, query, status)
                VALUES (?, ?, ?, ?, 'new')
                """,
                (
                    hit.get("url"),
                    hit.get("title"),
                    hit.get("source", "unknown"),
                    hit.get("query"),
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
    conn.close()
    return inserted


def log_run(
    stage: str,
    items: int,
    error: str | None = None,
    started_at: str | None = None,
    db_path: Path | str | None = None,
) -> None:
    """Record a pipeline stage execution in the runs table."""
    now_utc = datetime.now(timezone.utc).isoformat()
    start_time = started_at or now_utc

    conn = get_conn(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO runs (stage, started_at, finished_at, items, error)
            VALUES (?, ?, ?, ?, ?)
            """,
            (stage, start_time, now_utc, items, error),
        )
    conn.close()

