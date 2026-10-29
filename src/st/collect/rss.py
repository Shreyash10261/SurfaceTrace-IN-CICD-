"""RSS feed collector for SurfaceTrace-IN.

Owned by Shivang.
Parses RSS feeds for Indian news and cybersecurity disclosures matching query terms.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import requests

USER_AGENT = "SurfaceTrace-ClassProject/1.0 (academic-research; contact: researcher@institution.edu)"

DEFAULT_FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://krebsonsecurity.com/feed/",
    "https://www.darkreading.com/rss.xml",
]


def search(query: str, max_results: int = 10) -> list[dict]:
    """Fetch RSS feeds and return items matching query terms."""
    hits: list[dict] = []
    headers = {"User-Agent": USER_AGENT}
    query_terms = [t.strip().lower() for t in query.replace('"', "").split() if t.strip()]

    for feed_url in DEFAULT_FEEDS:
        try:
            resp = requests.get(feed_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content)
            for item in root.iter("item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")

                title = title_elem.text if title_elem is not None else ""
                link = link_elem.text if link_elem is not None else ""
                desc = desc_elem.text if desc_elem is not None else ""

                if not link:
                    continue

                combined = f"{title} {desc}".lower()
                # Check if any query term is in the combined text
                if not query_terms or any(term in combined for term in query_terms):
                    hits.append(
                        {
                            "url": link.strip(),
                            "title": title.strip() or "RSS Feed Item",
                            "source": "rss",
                            "query": query,
                        }
                    )
                    if len(hits) >= max_results:
                        return hits
        except Exception:
            continue

    return hits

