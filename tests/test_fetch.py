"""Unit tests for fetcher module (st.fetch).

Owned by Shivang / Shreyash.
Uses mocked HTTP requests (no live network) to test polite crawling, rate limits,
blocklist filtering, and status transitions.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from st.db import get_conn, init_db
from st.fetch import fetch_pending, load_blocklist


def test_load_blocklist(tmp_path: Path):
    blocklist_file = tmp_path / "blocklist.txt"
    blocklist_file.write_text("# Comment\ncsam\nbad-site.com\nchild abuse material\n")

    domains, terms = load_blocklist(blocklist_file)
    assert "bad-site.com" in domains
    assert "csam" in terms
    assert "child abuse material" in terms


def test_fetch_pending_blocked_domain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test_fetch_block.db"
    init_db(db_file)
    monkeypatch.setenv("DATABASE_PATH", str(db_file))

    # Mock blocklist
    monkeypatch.setattr("st.fetch.load_blocklist", lambda *args: ({"bad-domain.com"}, []))

    conn = get_conn(db_file)
    with conn:
        conn.execute(
            "INSERT INTO documents (url, source, status) VALUES ('https://bad-domain.com/page', 'seed', 'new')"
        )
    conn.close()

    fetched = fetch_pending(limit=10)
    assert fetched == 0

    conn = get_conn(db_file)
    cur = conn.cursor()
    cur.execute("SELECT status, error FROM documents WHERE url = 'https://bad-domain.com/page'")
    row = cur.fetchone()
    conn.close()

    assert row["status"] == "blocked"
    assert "Blocked domain" in row["error"]


def test_fetch_pending_successful_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test_fetch_ok.db"
    init_db(db_file)
    monkeypatch.setenv("DATABASE_PATH", str(db_file))

    monkeypatch.setattr("st.fetch.load_blocklist", lambda *args: (set(), ["csam"]))
    monkeypatch.setattr("st.fetch.is_allowed_by_robots", lambda *args: True)

    html_content = (
        b"<html><head><title>Research Article</title></head>"
        b"<body><p>This is a research report analyzing terrorism in India footprints on forums.</p></body></html>"
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_resp.encoding = "utf-8"
    mock_resp.raw.read.return_value = html_content
    mock_resp.raise_for_status = MagicMock()

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: mock_resp)

    conn = get_conn(db_file)
    with conn:
        conn.execute(
            "INSERT INTO documents (url, source, status) VALUES ('https://safe.org/article', 'seed', 'new')"
        )
    conn.close()

    fetched = fetch_pending(limit=10)
    assert fetched == 1

    conn = get_conn(db_file)
    cur = conn.cursor()
    cur.execute("SELECT status, title, text, fetched_at FROM documents WHERE url = 'https://safe.org/article'")
    row = cur.fetchone()
    conn.close()

    assert row["status"] == "fetched"
    assert row["title"] == "Research Article"
    assert "terrorism in India" in row["text"]
    assert row["fetched_at"] is not None

