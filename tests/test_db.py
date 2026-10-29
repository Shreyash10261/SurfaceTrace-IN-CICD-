"""Unit tests for SQLite database layer (st.db).

Owned by Shreyash.
Tests table creation, WAL mode, save_hits deduplication, and run logging.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from st.db import get_conn, init_db, log_run, save_hits


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "test.db"
    init_db(db_file)
    return db_file


def test_init_db_creates_tables(temp_db: Path):
    conn = get_conn(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    conn.close()

    assert "documents" in tables
    assert "onion_mentions" in tables
    assert "leads" in tables
    assert "runs" in tables


def test_wal_mode_enabled(temp_db: Path):
    conn = get_conn(temp_db)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode")
    mode = cur.fetchone()[0]
    conn.close()
    assert mode.upper() == "WAL"


def test_save_hits_inserts_and_deduplicates(temp_db: Path):
    hits = [
        {"url": "https://example.com/page1", "title": "Page 1", "source": "seed", "query": "q1"},
        {"url": "https://example.com/page2", "title": "Page 2", "source": "web_search", "query": "q2"},
    ]
    inserted = save_hits(hits, db_path=temp_db)
    assert inserted == 2

    # Second insert with duplicate URLs
    duplicate_hits = [
        {"url": "https://example.com/page1", "title": "Page 1 Duplicate", "source": "seed", "query": "q1"},
        {"url": "https://example.com/page3", "title": "Page 3", "source": "rss", "query": "q3"},
    ]
    inserted_again = save_hits(duplicate_hits, db_path=temp_db)
    assert inserted_again == 1  # only page3 should be inserted

    conn = get_conn(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM documents")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 3


def test_log_run(temp_db: Path):
    log_run("collect", items=15, error=None, db_path=temp_db)
    conn = get_conn(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT stage, items, error FROM runs WHERE stage = 'collect'")
    row = cur.fetchone()
    conn.close()

    assert row["stage"] == "collect"
    assert row["items"] == 15
    assert row["error"] is None

