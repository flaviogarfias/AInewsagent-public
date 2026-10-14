"""Hugging Face daily-papers metadata adapter (not a final authority)."""

from __future__ import annotations

import json
from urllib.request import Request, urlopen

from .identity import unique_candidates


def parse_daily_papers(payload: list[dict]) -> list[dict]:
    items = []
    for entry in payload:
        paper = entry.get("paper") or {}
        identifier = paper.get("id", "")
        if not identifier or not paper.get("title"):
            continue
        items.append({"kind": "paper", "source": "Hugging Face Daily Papers",
                      "title": paper["title"], "url": f"https://arxiv.org/abs/{identifier}",
                      "abstract": paper.get("summary", ""),
                      "published": paper.get("publishedAt") or entry.get("publishedAt", ""),
                      "votes": entry.get("numUpvotes", 0), "evidence_level": "api-metadata"})
    return unique_candidates(items)


def fetch_daily_papers(limit: int = 20) -> list[dict]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be 1..100")
    url = f"https://huggingface.co/api/daily_papers?limit={limit}"
    request = Request(url, headers={"User-Agent": "ai-daily-briefing/0.1"})
    with urlopen(request, timeout=15) as response:
        return parse_daily_papers(json.load(response))
