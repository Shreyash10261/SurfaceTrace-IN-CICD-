"""Fetching module for SurfaceTrace-IN.

Owned by Shivang.
Downloads pending documents with rate limits, robots.txt compliance, retries,
trafilatura text extraction, and blocklist filtering.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
import trafilatura

from st.db import get_conn, log_run

DEFAULT_BLOCKLIST_PATH = Path(__file__).resolve().parents[2] / "config" / "blocklist.txt"
USER_AGENT = "SurfaceTrace-ClassProject/1.0 (academic-research; contact: researcher@institution.edu)"

# Per-domain rate limit tracker and robots cache
_DOMAIN_LAST_REQUEST: dict[str, float] = {}
_ROBOTS_CACHE: dict[str, RobotFileParser] = {}


def load_blocklist(path: Path | str | None = None) -> tuple[set[str], list[str]]:
    """Load blocked domains and prohibited keywords from blocklist.txt."""
    b_path = Path(path) if path else DEFAULT_BLOCKLIST_PATH
    blocked_domains = set()
    blocked_terms = []

    if b_path.exists():
        with open(b_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "." in line and " " not in line:
                    blocked_domains.add(line.lower())
                else:
                    blocked_terms.append(line.lower())

    return blocked_domains, blocked_terms


def is_allowed_by_robots(url: str, user_agent: str = USER_AGENT) -> bool:
    """Check if URL is permitted by target domain's robots.txt."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if not domain:
        return True

    if domain not in _ROBOTS_CACHE:
        rp = RobotFileParser()
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            rp.set_url(robots_url)
            rp.read()
        except Exception:
            # If robots.txt cannot be fetched or parsed, assume allowed
            pass
        _ROBOTS_CACHE[domain] = rp

    rp = _ROBOTS_CACHE[domain]
    try:
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True


def rate_limit_domain(domain: str, min_interval: float = 1.0) -> None:
    """Ensure at least min_interval seconds between requests to the same domain."""
    now = time.time()
    last = _DOMAIN_LAST_REQUEST.get(domain, 0.0)
    elapsed = now - last
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _DOMAIN_LAST_REQUEST[domain] = time.time()


def fetch_url(url: str) -> tuple[str, str | None]:
    """Fetch URL with retries on timeout, 429, or 5xx. Returns (cleaned_text, title)."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    rate_limit_domain(domain, min_interval=1.0)

    headers = {"User-Agent": USER_AGENT}
    max_retries = 2
    delays = [1.0, 2.0]
    response = None

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=20, stream=True)
            # Skip non-HTML responses
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "text/plain" not in content_type:
                raise ValueError(f"Unsupported Content-Type: {content_type}")

            # Skip bodies over 2 MB (2,097,152 bytes)
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > 2_097_152:
                raise ValueError("Response body exceeds 2MB limit")

            if response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(delays[attempt])
                continue

            response.raise_for_status()
            break
        except (requests.Timeout, requests.HTTPError) as e:
            if attempt < max_retries:
                time.sleep(delays[attempt])
                continue
            raise e

    if response is None:
        raise RuntimeError("No response received")

    # Limit raw read size to 2MB
    raw_content = response.raw.read(2_097_152, decode_content=True)
    try:
        html_str = raw_content.decode(response.encoding or "utf-8", errors="replace")
    except Exception:
        html_str = raw_content.decode("utf-8", errors="replace")

    # Extract clean text using trafilatura
    extracted = trafilatura.extract(
        html_str,
        include_comments=False,
        include_tables=False,
        no_fallback=False,
    )

    clean_text = extracted or ""
    # Truncate to max 20,000 characters
    clean_text = clean_text[:20000]

    # Simple title extraction
    title = None
    if "<title>" in html_str.lower():
        start = html_str.lower().find("<title>") + 7
        end = html_str.lower().find("</title>", start)
        if end != -1:
            title = html_str[start:end].strip()[:500]

    return clean_text, title


def fetch_pending(limit: int = 200) -> int:
    """Fetch pending documents from documents table where status = 'new'.

    Transitions status from 'new' to 'fetched', 'failed', or 'blocked'.
    Returns number of documents successfully fetched.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    blocked_domains, blocked_terms = load_blocklist()
    fetched_count = 0
    error_msg = None

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, url FROM documents
            WHERE status = 'new'
            ORDER BY id
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()

        for doc_id, url in rows:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Domain blocklist check
            if any(blocked in domain for blocked in blocked_domains):
                conn.execute(
                    "UPDATE documents SET status = 'blocked', error = 'Blocked domain' WHERE id = ?",
                    (doc_id,),
                )
                continue

            # Robots.txt check
            if not is_allowed_by_robots(url):
                conn.execute(
                    "UPDATE documents SET status = 'failed', error = 'Disallowed by robots.txt' WHERE id = ?",
                    (doc_id,),
                )
                continue

            try:
                text, title = fetch_url(url)

                # Term blocklist check
                text_lower = text.lower()
                if any(term in text_lower for term in blocked_terms):
                    conn.execute(
                        "UPDATE documents SET status = 'blocked', error = 'Prohibited content' WHERE id = ?",
                        (doc_id,),
                    )
                    continue

                now_utc = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    """
                    UPDATE documents
                    SET status = 'fetched', text = ?, title = COALESCE(title, ?), fetched_at = ?, error = NULL
                    WHERE id = ?
                    """,
                    (text, title, now_utc, doc_id),
                )
                fetched_count += 1
            except Exception as e:
                conn.execute(
                    "UPDATE documents SET status = 'failed', error = ? WHERE id = ?",
                    (str(e)[:500], doc_id),
                )

        conn.commit()
    except Exception as e:
        error_msg = str(e)
        raise
    finally:
        conn.close()
        log_run("fetch", items=fetched_count, error=error_msg, started_at=started_at)

    return fetched_count

