"""Scoring module for SurfaceTrace-IN.

Owned by Devanshi.
Scores discovered .onion leads based on keyword context points, document recurrence,
and source diversity.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from st.db import get_conn, log_run

DEFAULT_KEYWORDS_PATH = Path(__file__).resolve().parents[2] / "config" / "keywords.yml"


def load_keywords(path: Path | str | None = None) -> dict:
    """Load keyword weights and terms from YAML."""
    keywords_path = Path(path) if path else DEFAULT_KEYWORDS_PATH
    if not keywords_path.exists():
        # Fallback defaults if file missing
        return {
            "strong": {"weight": 10, "terms": ["terrorism in india"]},
            "medium": {"weight": 5, "terms": ["jihadi", "extremist"]},
            "weak": {"weight": 2, "terms": ["india", "kashmir", "dark web", "forum"]},
            "negative": {"weight": -5, "terms": ["movie", "web series", "game", "quiz"]},
        }
    with open(keywords_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def context_points(context: str, keywords: dict | None = None) -> int:
    """Calculate keyword points for a single context snippet.

    Matches whole words or phrases, lowercase, each distinct keyword counted once.
    """
    if not context:
        return 0
    kws = keywords if keywords is not None else load_keywords()
    ctx_lower = context.lower()
    points = 0

    for group_name, group_data in kws.items():
        weight = group_data.get("weight", 0)
        terms = group_data.get("terms", [])
        for term in terms:
            term_clean = term.strip().lower()
            if not term_clean:
                continue
            pattern = r"\b" + re.escape(term_clean) + r"\b"
            if re.search(pattern, ctx_lower):
                points += weight

    return points


def score_lead(contexts: list[str], doc_count: int, source_count: int, keywords: dict | None = None) -> int:
    """Compute aggregate lead score (0..100).

    score = min(50, points of the best context, minimum 0)
          + min(25, 8  * number of documents mentioning it)
          + min(25, 12 * number of distinct sources mentioning it)
    """
    kws = keywords if keywords is not None else load_keywords()
    best_context_pts = 0
    if contexts:
        pts_list = [context_points(ctx, kws) for ctx in contexts]
        best_context_pts = max(pts_list)

    context_component = min(50, max(0, best_context_pts))
    doc_component = min(25, 8 * doc_count)
    source_component = min(25, 12 * source_count)

    score = context_component + doc_component + source_component
    return max(0, min(100, score))


def determine_band(score: int) -> str:
    """Return 'high' (>=60), 'medium' (>=30), or 'low' (<30)."""
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def score_all() -> int:
    """Rebuild score, band, doc_count, and source_count for all leads.

    Never overwrites review fields (review_status, reviewer, note).
    Returns total leads scored.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    total_leads = 0
    error_msg = None

    try:
        keywords = load_keywords()

        # Get all distinct onion addresses from mentions
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT onion FROM onion_mentions ORDER BY onion")
        onion_rows = cur.fetchall()

        for (onion,) in onion_rows:
            # Fetch all contexts
            cur.execute("SELECT context FROM onion_mentions WHERE onion = ?", (onion,))
            contexts = [r[0] for r in cur.fetchall()]

            # Fetch doc_count
            cur.execute("SELECT COUNT(DISTINCT doc_id) FROM onion_mentions WHERE onion = ?", (onion,))
            doc_count = cur.fetchone()[0]

            # Fetch source_count
            cur.execute(
                """
                SELECT COUNT(DISTINCT d.source)
                FROM onion_mentions om
                JOIN documents d ON om.doc_id = d.id
                WHERE om.onion = ?
                """,
                (onion,),
            )
            source_count = cur.fetchone()[0]

            score = score_lead(contexts, doc_count, source_count, keywords)
            band = determine_band(score)
            now_utc = datetime.now(timezone.utc).isoformat()

            conn.execute(
                """
                INSERT INTO leads (onion, score, band, doc_count, source_count, review_status, updated_at)
                VALUES (?, ?, ?, ?, ?, 'new', ?)
                ON CONFLICT (onion) DO UPDATE SET
                  score = excluded.score,
                  band = excluded.band,
                  doc_count = excluded.doc_count,
                  source_count = excluded.source_count,
                  updated_at = excluded.updated_at
                """,
                (onion, score, band, doc_count, source_count, now_utc),
            )
            total_leads += 1

        conn.commit()
    except Exception as e:
        error_msg = str(e)
        raise
    finally:
        conn.close()
        log_run("score", items=total_leads, error=error_msg, started_at=started_at)

    return total_leads

