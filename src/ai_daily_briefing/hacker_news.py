"""Hacker News via Algolia, discovery signals only; never cite comments as facts."""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .identity import unique_candidates


def _get(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "ai-daily-briefing/0.1"})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def parse_hits(payload: dict, min_points: int = 50) -> list[dict]:
    """Discard HN discussions and only keep externally linked stories."""
    items = []
    for hit in payload.get("hits", []):
        if not hit.get("url") or not hit.get("title") or int(hit.get("points") or 0) < min_points:
            continue
        items.append({"kind": "news", "source": "Hacker News discovery", "title": hit["title"],
                      "url": hit["url"], "abstract": "", "published": hit.get("created_at", ""),
                      "hn_points": hit.get("points", 0), "evidence_level": "discovery-only"})
    return unique_candidates(items)


def fetch_stories(queries: list[str], fetch: Callable[[str], dict] = _get,
                  max_calls: int = 3, per_call: int = 50, min_points: int = 50) -> list[dict]:
    """Spend at most max_calls free Algolia lookups, no automatic pagination."""
    if not 1 <= max_calls <= 20 or not 1 <= per_call <= 100:
        raise ValueError("invalid HN request budget")
    items = []
    for query in queries[:max_calls]:
        params = urlencode({"query": query, "tags": "story", "hitsPerPage": per_call,
                            "numericFilters": f"points>={min_points}"})
        items.extend(parse_hits(fetch("https://hn.algolia.com/api/v1/search_by_date?" + params), min_points))
    return unique_candidates(items)
