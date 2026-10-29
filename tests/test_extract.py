"""Unit tests for onion extraction and validation (st.extract).

Owned by Devanshi / Shreyash.
Tests defanging, v3 cryptographic checksums, context cutting, and extract_pending.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from st.db import get_conn, init_db
from st.extract import clean_text, cut_context, extract_pending, find_onions, is_valid_v3
from tests.helpers import make_tampered_v3, make_valid_v3


def test_clean_text_defanging():
    assert clean_text("test[.]onion") == "test.onion"
    assert clean_text("test(.)onion") == "test.onion"
    assert clean_text("test[dot]onion") == "test.onion"
    assert clean_text("test(dot)onion") == "test.onion"
    assert clean_text("normal text") == "normal text"


def test_is_valid_v3():
    valid = make_valid_v3()
    assert is_valid_v3(valid) is True

    tampered = make_tampered_v3(valid)
    assert is_valid_v3(tampered) is False

    assert is_valid_v3("short.onion") is False
    assert is_valid_v3("a" * 56 + ".onion") is False
    assert is_valid_v3("") is False


def test_find_onions():
    valid1 = make_valid_v3()
    valid2 = make_valid_v3()
    tampered = make_tampered_v3(valid1)

    text = f"Here is {valid1} and defanged {valid2.replace('.onion', '[.]onion')}, but fake {tampered} and duplicate {valid1}"
    matches = find_onions(text)

    addrs = [m[0] for m in matches]
    assert valid1 in addrs
    assert valid2 in addrs
    assert tampered not in addrs
    # Deduplication check
    assert len(addrs) == 2


def test_cut_context():
    text = "A" * 200 + "TARGET" + "B" * 200
    start = 200
    end = 206
    ctx = cut_context(text, start, end, window=150)
    assert len(ctx) <= 300
    assert "TARGET" in ctx


def test_extract_pending(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test_extract.db"
    init_db(db_file)
    monkeypatch.setenv("DATABASE_PATH", str(db_file))

    valid_addr = make_valid_v3()

    conn = get_conn(db_file)
    with conn:
        conn.execute(
            """
            INSERT INTO documents (url, title, source, text, status)
            VALUES ('https://example.com/report', 'Report', 'seed', ?, 'fetched')
            """,
            (f"This intelligence report discusses Lashkar-e-Taiba forum at {valid_addr} for recruitment.",),
        )
    conn.close()

    extracted_count = extract_pending()
    assert extracted_count == 1

    conn = get_conn(db_file)
    cur = conn.cursor()
    cur.execute("SELECT onion, context FROM onion_mentions")
    mentions = cur.fetchall()
    assert len(mentions) == 1
    assert mentions[0]["onion"] == valid_addr

    cur.execute("SELECT status FROM documents WHERE url = 'https://example.com/report'")
    doc_status = cur.fetchone()[0]
    conn.close()

    assert doc_status == "done"

