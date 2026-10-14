"""Bounded category selection over dated, unseen candidates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from .identity import unique_candidates


def parse_date(value: str) -> datetime | None:
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        try:
            date = parsedate_to_datetime(value)
        except (ValueError, TypeError):
            return None
    return date.astimezone(timezone.utc) if date.tzinfo else None


def select_daily(candidates: list[dict], now: str, sent: set[str] | None = None,
                 window_hours: int = 48) -> list[dict]:
    """Choose highest-scored recent unseen item per category, deterministic ties."""
    if window_hours < 1:
        raise ValueError("window_hours must be positive")
    current = parse_date(now)
    if current is None:
        raise ValueError("now must be timezone-aware")
    sent = sent or set()
    eligible = []
    for item in unique_candidates(candidates):
        published = parse_date(item.get("published", ""))
        if (item.get("kind") not in {"paper", "news"} or item["url"] in sent or
                published is None or not current - timedelta(hours=window_hours) <= published <= current):
            continue
        eligible.append(item)
    result = []
    for kind in ("paper", "news"):
        matches = [item for item in eligible if item["kind"] == kind]
        if matches:
            matches.sort(key=lambda item: (item.get("topic_priority") == "peripheral",
                                           -int(item.get("score", 0)),
                                           kind == "news" and item.get("source") == "Hacker News discovery",
                                           -parse_date(item["published"]).timestamp(), item["url"]))
            result.append(matches[0])
    return result
