"""GitHub collector for SurfaceTrace-IN.

Owned by Shivang.
Queries GitHub REST API for public repositories and issues mentioning query terms.
"""
from __future__ import annotations

import os

import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
USER_AGENT = "SurfaceTrace-ClassProject/1.0 (academic-research; contact: researcher@institution.edu)"


def search(query: str, max_results: int = 10) -> list[dict]:
    """Search public GitHub repositories for the query."""
    hits: list[dict] = []
    if not query:
        return hits

    url = "https://api.github.com/search/repositories"
    params = {"q": query, "per_page": min(max_results, 30)}
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github.v3+json",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("items", [])[:max_results]:
                hits.append(
                    {
                        "url": item.get("html_url"),
                        "title": item.get("full_name") or item.get("description"),
                        "source": "github",
                        "query": query,
                    }
                )
    except Exception:
        pass

    return hits

