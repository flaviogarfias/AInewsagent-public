"""Cheap deterministic pre-ranking to bound external verification and inference."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta, timezone

import re

from .identity import unique_candidates
from .selection import parse_date
from .topics import topic_priority

_PAPER_CORE_TITLE = re.compile(
    r"\b(?:llms?|language models?|agentic|multi.agent|ai agents?|"
    r"foundation models?|transformers?|generative ai|neural networks?|"
    r"model serving|inference engine|ai infrastructure)\b", re.I)


_ARXIV_MONTH = re.compile(r"^https://arxiv\.org/abs/(\d{2})(\d{2})\.\d{4,5}$")


def _definitely_old_arxiv(item: dict, earliest: datetime) -> bool:
    if item.get("kind") != "paper":
        return False
    match = _ARXIV_MONTH.match(item.get("url", ""))
    if not match:
        return False
    year, month = 2000 + int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        return False
    last_possible_day = datetime(year, month, monthrange(year, month)[1],
                                 23, 59, 59, tzinfo=timezone.utc)
    return last_possible_day < earliest


def shortlist_candidates(items: list[dict], now: str, per_kind: int = 6,
                         window_hours: int = 48) -> list[dict]:
    """Bound per-category work; never treat votes or points as truth."""
    if not 1 <= per_kind <= 20 or not 1 <= window_hours <= 168:
        raise ValueError("invalid shortlist limits")
    current = parse_date(now)
    if current is None:
        raise ValueError("now must be timezone-aware")
    eligible = []
    for item in unique_candidates(items):
        published = parse_date(item.get("published", ""))
        if (item.get("kind") in {"paper", "news"} and published is not None and
                current - timedelta(hours=window_hours) <= published <= current and
                not _definitely_old_arxiv(item, current - timedelta(hours=window_hours))):
            eligible.append({**item, "topic_priority": (
                "peripheral" if item["kind"] == "paper" and
                not _PAPER_CORE_TITLE.search(item.get("title", "")) else
                topic_priority(item.get("title", ""), item.get("abstract", "")))})
    selected = []
    for kind in ("paper", "news"):
        matches = [item for item in eligible if item["kind"] == kind]
        matches.sort(key=lambda item: (kind == "news" and (
                                           item.get("evidence_level") == "discovery-only" or
                                           item.get("source") == "Hacker News discovery"),
                                       item["topic_priority"] != "core",
                                       -int(item.get("votes") or item.get("hn_points") or 0),
                                       -parse_date(item["published"]).timestamp(), item["url"]))
        selected.extend(matches[:per_kind])
    return selected
