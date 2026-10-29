"""Ahmia collector for SurfaceTrace-IN.

Owned by Shivang.
Queries Ahmia's public clearnet search interface and extracts surface search results.
"""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup

USER_AGENT = "SurfaceTrace-ClassProject/1.0 (academic-research; contact: researcher@institution.edu)"


def search(query: str, max_results: int = 10) -> list[dict]:
    """Query Ahmia clearnet search and return result hits."""
    hits: list[dict] = []
    if not query:
        return hits

    url = "https://ahmia.fi/search/"
    params = {"q": query}
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code != 200:
            return hits

        soup = BeautifulSoup(resp.text, "lxml")
        results = soup.select("li.result") or soup.select(".search-result")

        for item in results[:max_results]:
            a_tag = item.find("a")
            if not a_tag or not a_tag.get("href"):
                continue
            link = a_tag["href"]
            title = a_tag.get_text(strip=True)
            hits.append(
                {
                    "url": link,
                    "title": title or "Ahmia search result",
                    "source": "ahmia",
                    "query": query,
                }
            )
    except Exception:
        pass

    return hits

