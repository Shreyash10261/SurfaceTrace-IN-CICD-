"""Unit tests for scoring module (st.score).

Owned by Devanshi / Shreyash.
Tests 10 hand-made cases covering keywords, formula components, bands, and review persistence.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from st.db import get_conn, init_db
from st.score import context_points, determine_band, score_all, score_lead
from tests.helpers import make_valid_v3

TEST_KEYWORDS = {
    "strong": {"weight": 10, "terms": ["terrorism in india", "lashkar-e-taiba", "jaish-e-mohammed"]},
    "medium": {"weight": 5, "terms": ["jihadi", "extremist", "maoist", "radicalization", "recruitment"]},
    "weak": {"weight": 2, "terms": ["india", "kashmir", "dark web", "forum"]},
    "negative": {"weight": -5, "terms": ["movie", "web series", "game", "quiz"]},
}


def test_case_1_empty_context():
    pts = context_points("", TEST_KEYWORDS)
    assert pts == 0


def test_case_2_strong_keyword_single():
    ctx = "Report investigating lashkar-e-taiba footprints."
    pts = context_points(ctx, TEST_KEYWORDS)
    assert pts == 10

    ctx_with_india = "Report investigating terrorism in india footprints."
    # terrorism in india (10) + india (2) = 12
    assert context_points(ctx_with_india, TEST_KEYWORDS) == 12


def test_case_3_multiple_keywords():
    ctx = "Lashkar-e-Taiba jihadi recruitment campaign in kashmir forum."
    # lashkar-e-taiba (10) + jihadi (5) + recruitment (5) + kashmir (2) + forum (2) = 24
    pts = context_points(ctx, TEST_KEYWORDS)
    assert pts == 24


def test_case_4_negative_keywords():
    ctx = "Discussion about india movie and web series."
    # india (2) - movie (5) - web series (5) = -8
    pts = context_points(ctx, TEST_KEYWORDS)
    assert pts == -8


def test_case_5_context_component_clamping():
    # Negative points clamp to 0
    score = score_lead(["India movie review"], doc_count=1, source_count=1, keywords=TEST_KEYWORDS)
    # context=0, doc=min(25, 8), source=min(25, 12) = 0 + 8 + 12 = 20
    assert score == 20


def test_case_6_context_max_50():
    # Massive context with many terms exceeds 50
    ctx = "terrorism in india lashkar-e-taiba jaish-e-mohammed jihadi extremist maoist radicalization recruitment india kashmir dark web forum"
    # Total points > 50, but component caps at 50
    score = score_lead([ctx], doc_count=0, source_count=0, keywords=TEST_KEYWORDS)
    assert score == 50


def test_case_7_multi_context_selects_max():
    ctx_weak = "General india forum mention"  # 2 + 2 = 4
    ctx_strong = "Lashkar-e-Taiba recruitment camp"  # 10 + 5 = 15
    score = score_lead([ctx_weak, ctx_strong], doc_count=1, source_count=1, keywords=TEST_KEYWORDS)
    # Best is 15, doc=8, source=12 -> 15 + 8 + 12 = 35
    assert score == 35


def test_case_8_recurrence_caps_at_25():
    # 8 * 4 = 32, capped at 25
    score = score_lead([], doc_count=4, source_count=0, keywords=TEST_KEYWORDS)
    assert score == 25


def test_case_9_source_diversity_caps_at_25():
    # 12 * 3 = 36, capped at 25
    score = score_lead([], doc_count=0, source_count=3, keywords=TEST_KEYWORDS)
    assert score == 25


def test_case_10_band_classification():
    assert determine_band(60) == "high"
    assert determine_band(100) == "high"
    assert determine_band(59) == "medium"
    assert determine_band(30) == "medium"
    assert determine_band(29) == "low"
    assert determine_band(0) == "low"


def test_score_all_preserves_review_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test_score_preservation.db"
    init_db(db_file)
    monkeypatch.setenv("DATABASE_PATH", str(db_file))

    onion = make_valid_v3()

    conn = get_conn(db_file)
    with conn:
        conn.execute(
            "INSERT INTO documents (id, url, source, status) VALUES (1, 'https://example.com/a', 'seed', 'done')"
        )
        conn.execute(
            "INSERT INTO onion_mentions (onion, doc_id, context) VALUES (?, 1, 'terrorism in india discussion')",
            (onion,),
        )
        # Pre-seed a review
        conn.execute(
            """
            INSERT INTO leads (onion, score, band, doc_count, source_count, review_status, reviewer, note, updated_at)
            VALUES (?, 10, 'low', 1, 1, 'relevant', 'Devanshi', 'Confirmed threat', '2026-10-29T00:00:00Z')
            """,
            (onion,),
        )
    conn.close()

    total_scored = score_all()
    assert total_scored == 1

    conn = get_conn(db_file)
    cur = conn.cursor()
    cur.execute("SELECT * FROM leads WHERE onion = ?", (onion,))
    lead = cur.fetchone()
    conn.close()

    # Score and band updated
    assert lead["score"] > 10
    # Review fields PRESERVED!
    assert lead["review_status"] == "relevant"
    assert lead["reviewer"] == "Devanshi"
    assert lead["note"] == "Confirmed threat"

