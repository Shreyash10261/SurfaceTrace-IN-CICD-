"""Extraction module for SurfaceTrace-IN.

Owned by Devanshi.
Extracts and validates Tor v3 .onion addresses from fetched documents and cuts contexts.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
from datetime import datetime, timezone

from st.db import get_conn, log_run

ONION = re.compile(r"(?<![a-z0-9])([a-z2-7]{56})\.onion(?![a-z0-9])", re.I)
DEFANG = re.compile(r"\s*[\[\(]\s*(?:\.|dot)\s*[\]\)]\s*onion", re.I)


def clean_text(text: str) -> str:
    """Turn 'abc[.]onion' or 'abc(dot)onion' into 'abc.onion'."""
    if not text:
        return ""
    return DEFANG.sub(".onion", text)


def is_valid_v3(address: str) -> bool:
    """Validate a Tor v3 onion address checksum."""
    name = address.lower().removesuffix(".onion")
    if len(name) != 56:
        return False
    try:
        raw = base64.b32decode(name.upper())
    except Exception:
        return False
    key, checksum, version = raw[:32], raw[32:34], raw[34:35]
    if version != b"\x03":
        return False
    expected = hashlib.sha3_256(b".onion checksum" + key + version).digest()[:2]
    return checksum == expected


def find_onions(text: str) -> list[tuple[str, int, int]]:
    """Find valid Tor v3 addresses in text, returning (address, start, end)."""
    text = clean_text(text)
    found, seen = [], set()
    for m in ONION.finditer(text):
        addr = m.group(0).lower()
        if addr not in seen and is_valid_v3(addr):
            seen.add(addr)
            found.append((addr, m.start(), m.end()))
    return found


def make_valid_v3() -> str:
    """Generate a random cryptographically valid Tor v3 onion address for testing."""
    key, version = os.urandom(32), b"\x03"
    checksum = hashlib.sha3_256(b".onion checksum" + key + version).digest()[:2]
    return base64.b32encode(key + checksum + version).decode().lower() + ".onion"


def cut_context(text: str, start: int, end: int, window: int = 150) -> str:
    """Extract up to 150 chars before and after match, capped at 300 chars."""
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    return text[ctx_start:ctx_end][:300]


def extract_pending() -> int:
    """Extract onion mentions from all fetched documents.

    Updates document status from 'fetched' to 'done'.
    Returns total new onion mentions inserted.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    total_mentions = 0
    error_msg = None

    try:
        cur = conn.cursor()
        cur.execute("SELECT id, text FROM documents WHERE status = 'fetched' ORDER BY id")
        rows = cur.fetchall()

        for doc_id, raw_text in rows:
            text = clean_text(raw_text or "")
            matches = find_onions(text)

            for addr, start, end in matches:
                context = cut_context(text, start, end, window=150)
                ins_cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO onion_mentions (onion, doc_id, context)
                    VALUES (?, ?, ?)
                    """,
                    (addr, doc_id, context),
                )
                if ins_cur.rowcount > 0:
                    total_mentions += 1

            conn.execute("UPDATE documents SET status = 'done' WHERE id = ?", (doc_id,))
        conn.commit()
    except Exception as e:
        error_msg = str(e)
        raise
    finally:
        conn.close()
        log_run("extract", items=total_mentions, error=error_msg, started_at=started_at)

    return total_mentions

