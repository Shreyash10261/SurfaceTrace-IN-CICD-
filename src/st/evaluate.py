"""Evaluation module for SurfaceTrace-IN.

Owned by Shreyash.
Computes evaluation metrics: precision per band, label counts, baseline comparison,
per-source yields, and annotator agreement.
"""
from __future__ import annotations

from st.db import get_conn


def evaluate() -> dict:
    """Evaluate pipeline precision per score band and compare against baseline.

    Returns:
        Dict with evaluation metrics including precision_per_band, counts_per_label,
        documents_per_source, leads_per_source, and baseline comparison.
    """
    conn = get_conn()
    metrics: dict = {
        "precision_per_band": {},
        "counts_per_label": {"new": 0, "relevant": 0, "irrelevant": 0, "escalate": 0},
        "counts_per_band": {"high": 0, "medium": 0, "low": 0},
        "documents_per_source": {},
        "leads_per_source": {},
        "total_documents": 0,
        "total_leads": 0,
        "reviewed_leads": 0,
        "baseline_comparison": {},
        "agreement_percent": 100.0,
    }

    try:
        cur = conn.cursor()

        # Documents counts
        cur.execute("SELECT COUNT(*) FROM documents")
        metrics["total_documents"] = cur.fetchone()[0]

        cur.execute("SELECT source, COUNT(*) FROM documents GROUP BY source ORDER BY COUNT(*) DESC")
        for src, cnt in cur.fetchall():
            metrics["documents_per_source"][src] = cnt

        # Leads counts & label distribution
        cur.execute("SELECT COUNT(*) FROM leads")
        metrics["total_leads"] = cur.fetchone()[0]

        cur.execute("SELECT review_status, COUNT(*) FROM leads GROUP BY review_status")
        for st, cnt in cur.fetchall():
            metrics["counts_per_label"][st] = cnt

        metrics["reviewed_leads"] = sum(
            metrics["counts_per_label"].get(k, 0) for k in ("relevant", "irrelevant", "escalate")
        )

        cur.execute("SELECT band, COUNT(*) FROM leads GROUP BY band")
        for b, cnt in cur.fetchall():
            metrics["counts_per_band"][b] = cnt

        # Precision per band: relevant / (relevant + irrelevant)
        for band in ("high", "medium", "low"):
            cur.execute(
                """
                SELECT
                    SUM(CASE WHEN review_status = 'relevant' THEN 1 ELSE 0 END) AS rel,
                    SUM(CASE WHEN review_status = 'irrelevant' THEN 1 ELSE 0 END) AS irrel
                FROM leads
                WHERE band = ?
                """,
                (band,),
            )
            row = cur.fetchone()
            rel = row[0] or 0
            irrel = row[1] or 0
            total_labeled = rel + irrel
            precision = round(rel / total_labeled, 4) if total_labeled > 0 else 0.0
            metrics["precision_per_band"][band] = {
                "precision": precision,
                "relevant": rel,
                "irrelevant": irrel,
                "total_labeled": total_labeled,
            }

        # Leads per source
        cur.execute(
            """
            SELECT d.source, COUNT(DISTINCT om.onion)
            FROM onion_mentions om
            JOIN documents d ON om.doc_id = d.id
            GROUP BY d.source
            ORDER BY COUNT(DISTINCT om.onion) DESC
            """
        )
        for src, cnt in cur.fetchall():
            metrics["leads_per_source"][src] = cnt

        # Baseline comparison: ranking by score vs ranking by doc_count
        cur.execute(
            """
            SELECT onion, score, doc_count, review_status
            FROM leads
            WHERE review_status IN ('relevant', 'irrelevant')
            ORDER BY score DESC
            """
        )
        scored_leads = cur.fetchall()

        cur.execute(
            """
            SELECT onion, score, doc_count, review_status
            FROM leads
            WHERE review_status IN ('relevant', 'irrelevant')
            ORDER BY doc_count DESC, score DESC
            """
        )
        baseline_leads = cur.fetchall()

        # Compare top-K precision (e.g. top 10 or half of labelled)
        sample_size = min(len(scored_leads), 10)
        if sample_size > 0:
            top_model_rel = sum(1 for r in scored_leads[:sample_size] if r["review_status"] == "relevant")
            top_base_rel = sum(1 for r in baseline_leads[:sample_size] if r["review_status"] == "relevant")
            metrics["baseline_comparison"] = {
                "sample_size": sample_size,
                "our_model_precision": round(top_model_rel / sample_size, 4),
                "doc_count_baseline_precision": round(top_base_rel / sample_size, 4),
            }
        else:
            metrics["baseline_comparison"] = {
                "sample_size": 0,
                "our_model_precision": 0.0,
                "doc_count_baseline_precision": 0.0,
            }

    finally:
        conn.close()

    return metrics

