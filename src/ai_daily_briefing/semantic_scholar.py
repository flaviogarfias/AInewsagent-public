"""Opt-in Semantic Scholar enrichment for arXiv candidates."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

_ARXIV = re.compile(r"^https://arxiv\.org/abs/(\d{4}\.\d{4,5})$")
_FIELDS = "paperId,title,abstract,citationCount,influentialCitationCount,externalIds"


def _get(url: str, headers: dict) -> dict:
    with urlopen(Request(url, headers=headers), timeout=15) as response:
        return json.load(response)


def enrich_papers(items: list[dict], api_key: str, fetch: Callable[[str, dict], dict] = _get,
                  max_calls: int = 5) -> list[dict]:
    """Enrich only recognized arXiv IDs; never replace their canonical identity."""
    if not api_key.strip():
        raise ValueError("Semantic Scholar API key required")
    if not 0 <= max_calls <= 20:
        raise ValueError("invalid Semantic Scholar call budget")
    used = 0
    enriched = []
    for item in items:
        match = _ARXIV.match(item.get("url", "")) if item.get("kind") == "paper" else None
        if not match or used >= max_calls:
            enriched.append(item)
            continue
        used += 1
        url = "https://api.semanticscholar.org/graph/v1/paper/" + quote("ARXIV:" + match.group(1)) + "?fields=" + _FIELDS
        data = fetch(url, {"x-api-key": api_key, "User-Agent": "ai-daily-briefing/0.1"})
        if data.get("externalIds", {}).get("ArXiv", "").lower() != match.group(1).lower():
            raise ValueError("Semantic Scholar arXiv identifier mismatch")
        enriched.append({**item, "abstract": data.get("abstract") or item.get("abstract", ""),
                         "citation_count": data.get("citationCount"),
                         "influential_citation_count": data.get("influentialCitationCount"),
                         "semantic_scholar_id": data.get("paperId")})
    return enriched
