"""Web search collector for SurfaceTrace-IN.

Owned by Shivang.
Queries a surface-web search API (e.g. Google Programmable Search, SearXNG, or Brave)
using credentials from environment variables.
"""
from __future__ import annotations

import os

import requests

SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY")
SEARCH_ENGINE_ID = os.environ.get("SEARCH_ENGINE_ID")
SEARXNG_URL = os.environ.get("SEARXNG_BASE_URL", "http://localhost:8080")


def search(query: str, max_results: int = 10) -> list[dict]:
    """Search the web for query and return list of hit dicts."""
    hits: list[dict] = []
    if not query:
        return hits

    # 1. Try Google Programmable Search if credentials provided
    if SEARCH_API_KEY and SEARCH_ENGINE_ID:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": SEARCH_API_KEY,
                "cx": SEARCH_ENGINE_ID,
                "q": query,
                "num": min(max_results, 10),
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("items", []):
                    hits.append(
                        {
                            "url": item.get("link"),
                            "title": item.get("title"),
                            "source": "web_search",
                            "query": query,
                        }
                    )
                return hits
        except Exception:
            pass

    # 2. Try SearXNG if available
    try:
        url = f"{SEARXNG_URL}/search"
        params = {"q": query, "format": "json"}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for r in data.get("results", [])[:max_results]:
                hits.append(
                    {
                        "url": r.get("url"),
                        "title": r.get("title"),
                        "source": "web_search",
                        "query": query,
                    }
                )
    except Exception:
        pass

    return hits

