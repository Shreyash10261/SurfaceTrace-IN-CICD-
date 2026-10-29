"""Unit tests for export and evaluate modules (st.export, st.evaluate).

Owned by Shreyash.
Tests masked CSV generation, metric calculation, and baseline comparison.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from st.db import get_conn, init_db
from st.evaluate import evaluate
from st.export import export_csv, mask_onion
from tests.helpers import make_valid_v3


def test_mask_onion():
    addr = "abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqrstuv.onion"
    masked = mask_onion(addr)
    assert masked == "abcdefgh..."
    assert mask_onion("") == "..."


def test_export_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test_export.db"
    init_db(db_file)
    monkeypatch.setenv("DATABASE_PATH", str(db_file))

    onion = make_valid_v3()
    conn = get_conn(db_file)
    with conn:
        conn.execute(
            """
            INSERT INTO leads (onion, score, band, doc_count, source_count, review_status, reviewer, note, updated_at)
            VALUES (?, 75, 'high', 2, 2, 'relevant', 'Shreyash', 'Strong link', '2026-10-29T05:00:00Z')
            """,
            (onion,),
        )
    conn.close()

    # Masked export
    masked_csv = tmp_path / "leads_masked.csv"
    export_csv(str(masked_csv), masked=True)

    with open(masked_csv, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        assert reader[0]["onion"] == mask_onion(onion)
        assert reader[0]["score"] == "75"
        assert reader[0]["band"] == "high"

    # Unmasked export
    unmasked_csv = tmp_path / "leads_unmasked.csv"
    export_csv(str(unmasked_csv), masked=False)

    with open(unmasked_csv, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        assert reader[0]["onion"] == onion


def test_evaluate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test_eval.db"
    init_db(db_file)
    monkeypatch.setenv("DATABASE_PATH", str(db_file))

    addr1 = make_valid_v3()
    addr2 = make_valid_v3()
    addr3 = make_valid_v3()

    conn = get_conn(db_file)
    with conn:
        conn.execute("INSERT INTO documents (id, url, source, status) VALUES (1, 'https://example.com/1', 'seed', 'done')")
        conn.execute("INSERT INTO documents (id, url, source, status) VALUES (2, 'https://example.com/2', 'ahmia', 'done')")

        conn.execute("INSERT INTO onion_mentions (onion, doc_id, context) VALUES (?, 1, 'ctx1')", (addr1,))
        conn.execute("INSERT INTO onion_mentions (onion, doc_id, context) VALUES (?, 2, 'ctx2')", (addr2,))

        # High band: 1 relevant, 0 irrelevant -> 100% precision
        conn.execute(
            "INSERT INTO leads (onion, score, band, doc_count, source_count, review_status) VALUES (?, 80, 'high', 2, 2, 'relevant')",
            (addr1,),
        )
        # Medium band: 1 irrelevant -> 0% precision
        conn.execute(
            "INSERT INTO leads (onion, score, band, doc_count, source_count, review_status) VALUES (?, 45, 'medium', 1, 1, 'irrelevant')",
            (addr2,),
        )
        # Low band: new
        conn.execute(
            "INSERT INTO leads (onion, score, band, doc_count, source_count, review_status) VALUES (?, 15, 'low', 1, 1, 'new')",
            (addr3,),
        )
    conn.close()

    metrics = evaluate()

    assert metrics["total_documents"] == 2
    assert metrics["total_leads"] == 3
    assert metrics["reviewed_leads"] == 2
    assert metrics["counts_per_label"]["relevant"] == 1
    assert metrics["counts_per_label"]["irrelevant"] == 1
    assert metrics["counts_per_label"]["new"] == 1

    high_band_prec = metrics["precision_per_band"]["high"]["precision"]
    assert high_band_prec == 1.0

    med_band_prec = metrics["precision_per_band"]["medium"]["precision"]
    assert med_band_prec == 0.0

    assert "seed" in metrics["documents_per_source"]
    assert "ahmia" in metrics["documents_per_source"]

