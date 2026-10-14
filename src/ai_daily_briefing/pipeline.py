"""Pure-ish orchestration of candidate validation, scoring and dry-run report."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta


from .identity import unique_candidates
from .report import render_html
from .scoring import score_candidate
from .selection import parse_date, select_daily
from .shortlist import shortlist_candidates
from .state import DeliveryState
from .topics import has_enough_evidence, topic_priority


def prepare_briefing(candidates: list[dict], state: DeliveryState, now: str,
                     evaluate: Callable[[dict], dict], verify: Callable[[str], bool],
                     window_hours: int = 48,
                     fetch_text: Callable[[str], str] | None = None,
                     max_evaluations_per_kind: int = 6,
                     paper_date_lookup: Callable[[str], str | None] | None = None,
                     paper_dates_lookup: Callable[[list[str]], dict[str, str]] | None = None) -> dict:
    """Prepare, never send; only verified links enter the ranking pool."""
    prepared = []
    source_errors = 0
    current = parse_date(now)
    if current is None:
        raise ValueError("now must be timezone-aware")
    unseen = [item for item in unique_candidates(candidates) if not state.is_sent(item["url"])]
    def needs_original_date(item: dict) -> bool:
        feed_date = parse_date(item.get("published", ""))
        return (item.get("kind") == "paper" and
                item["url"].startswith("https://arxiv.org/abs/") and feed_date is not None and
                current - timedelta(hours=window_hours) <= feed_date <= current)

    arxiv_urls = [item["url"] for item in unseen if needs_original_date(item)]
    batch_dates: dict[str, str] = {}
    batch_failed = False
    if paper_dates_lookup is not None and arxiv_urls:
        try:
            batch_dates = paper_dates_lookup(arxiv_urls)
        except (OSError, ValueError):
            source_errors += len(arxiv_urls)
            batch_failed = True
    dated = []
    for item in unseen:
        if needs_original_date(item):
            if batch_failed:
                continue
            if paper_date_lookup is None and paper_dates_lookup is None:
                source_errors += 1
                continue
            try:
                if paper_dates_lookup is not None:
                    original = batch_dates.get(item["url"])
                elif paper_date_lookup is not None:
                    original = paper_date_lookup(item["url"])
                else:
                    continue
                original_date = parse_date(original or "")
            except (OSError, ValueError):
                source_errors += 1
                continue
            if original_date is None:
                source_errors += 1
                continue
            if not current - timedelta(hours=window_hours) <= original_date <= current:
                continue
            item = {**item, "feed_published": item["published"], "published": original}
        dated.append(item)
    for item in shortlist_candidates(dated, now, per_kind=max_evaluations_per_kind,
                                     window_hours=window_hours):
        try:
            verified = verify(item["url"])
        except (OSError, ValueError):
            source_errors += 1
            continue
        if not verified:
            source_errors += 1
            continue
        if not has_enough_evidence(item):
            if item["kind"] != "news":
                continue
            if fetch_text is None:
                source_errors += 1
                continue
            try:
                text = fetch_text(item["url"])
            except (OSError, ValueError):
                source_errors += 1
                continue
            item = {**item, "abstract": text}
            if not has_enough_evidence(item):
                source_errors += 1
                continue
        assessment = evaluate(item)
        if assessment.get("central_ai") is False:
            item = {**item, "topic_priority": "peripheral"}
        scored = {**item, "criteria": assessment["criteria"], "summary": assessment["summary"],
                  "source_verified": True,
                  "topic_priority": (item["topic_priority"] if item["kind"] == "paper" else
                                     "peripheral" if assessment.get("central_ai") is False else
                                     topic_priority(item["title"], item.get("abstract", "")))}
        if not scored["summary"].strip():
            continue
        scored["score"], scored["traffic_light"] = score_candidate(scored)
        prepared.append(scored)
    selected = select_daily(prepared, now, window_hours=window_hours)
    stamp = current.strftime("%Y-%m-%d %H:%M %Z")
    return {"items": selected, "html": render_html(selected, stamp),
            "generated_at": now, "source_errors": source_errors}
