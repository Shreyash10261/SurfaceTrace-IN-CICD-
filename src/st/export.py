"""Export module for SurfaceTrace-IN.

Owned by Shreyash.
Exports discovered leads to CSV with optional address masking for safety and privacy.
"""
from __future__ import annotations

import csv
from pathlib import Path

from st.db import get_conn


def mask_onion(address: str) -> str:
    """Mask onion address to first 8 characters + '...'."""
    if not address:
        return "..."
    addr_clean = address.strip()
    prefix = addr_clean[:8]
    return f"{prefix}..."


def export_csv(path: str, masked: bool = True) -> None:
    """Export all leads to a CSV file.

    If masked is True, onion addresses are exported as first 8 chars + '...'.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT onion, score, band, doc_count, source_count, review_status, reviewer, note, updated_at
            FROM leads
            ORDER BY score DESC
            """
        )
        rows = cur.fetchall()

        fieldnames = [
            "onion",
            "score",
            "band",
            "doc_count",
            "source_count",
            "review_status",
            "reviewer",
            "note",
            "updated_at",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fieldnames)
            for row in rows:
                row_dict = dict(row)
                onion_val = row_dict["onion"]
                if masked:
                    onion_val = mask_onion(onion_val)
                writer.writerow(
                    [
                        onion_val,
                        row_dict["score"],
                        row_dict["band"],
                        row_dict["doc_count"],
                        row_dict["source_count"],
                        row_dict["review_status"],
                        row_dict["reviewer"] or "",
                        row_dict["note"] or "",
                        row_dict["updated_at"] or "",
                    ]
                )
    finally:
        conn.close()

