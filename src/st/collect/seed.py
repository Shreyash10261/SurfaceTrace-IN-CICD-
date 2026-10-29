"""Seed collector for SurfaceTrace-IN.

Owned by Shivang.
Reads vetted public URLs from config/seed_urls.txt to guarantee demo data.
"""
from __future__ import annotations

from pathlib import Path

DEFAULT_SEEDS_PATH = Path(__file__).resolve().parents[3] / "config" / "seed_urls.txt"


def search(query: str = "", max_results: int = 10) -> list[dict]:
    """Return hits from seed_urls.txt. Ignores query and returns seed URLs."""
    seeds_path = DEFAULT_SEEDS_PATH
    hits: list[dict] = []

    if not seeds_path.exists():
        return hits

    with open(seeds_path, encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if not url or url.startswith("#"):
                continue
            hits.append(
                {
                    "url": url,
                    "title": f"Seed: {url}",
                    "source": "seed",
                    "query": query or "seed_list",
                }
            )

    return hits

