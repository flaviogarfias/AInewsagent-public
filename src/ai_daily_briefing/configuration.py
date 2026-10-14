"""Validation for portable briefing-agent configuration."""

from __future__ import annotations

from datetime import datetime
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .identity import canonical_url

ALLOWED_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday"}


def validate_delivery_targets(delivery: dict) -> list[str]:
    """Fail closed on unconfigured outbound destinations; leave secrets elsewhere."""
    errors = []
    for field in ("sender", "recipient"):
        value = delivery.get(field)
        if (not isinstance(value, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value)
                or value.lower().endswith("@example.org")):
            errors.append(f"delivery.{field} must be a configured email address")
    channel = delivery.get("slack_channel_id")
    if not isinstance(channel, str) or not re.fullmatch(r"[CG][A-Z0-9]{8,}", channel):
        errors.append("delivery.slack_channel_id must be a configured channel ID")
    name = delivery.get("slack_channel_name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", name) or name.startswith("replace-"):
        errors.append("delivery.slack_channel_name must be a configured channel name")
    return errors


def validate_configuration(configuration: dict) -> list[str]:
    """Return human-readable configuration errors without performing I/O."""
    errors: list[str] = []
    schedule = configuration.get("schedule", {})
    days = schedule.get("days", [])
    if not days:
        errors.append("schedule.days must not be empty")
    for day in days:
        if day not in ALLOWED_DAYS:
            errors.append(f"{day} is not an allowed delivery day")
    try:
        ZoneInfo(schedule.get("timezone", ""))
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        errors.append("schedule.timezone must be an IANA zone")
    try:
        datetime.strptime(schedule.get("time", ""), "%H:%M")
        hour, minute = map(int, schedule["time"].split(":"))
        if hour > 23 or minute > 59 or len(schedule["time"]) != 5:
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        errors.append("schedule.time must be HH:MM")
    model = configuration.get("model", {})
    if not model.get("name"):
        errors.append("model.name is required")
    base_url = model.get("base_url", "http://127.0.0.1:11434")
    try:
        parts = urlsplit(base_url)
        safe_local = (parts.scheme == "http" and parts.hostname in {"127.0.0.1", "::1"}
                      and parts.port is not None and parts.port > 0 and not parts.username
                      and not parts.password and not parts.path and not parts.query and not parts.fragment)
    except (ValueError, TypeError, AttributeError):
        safe_local = False
    if not safe_local:
        errors.append("model.base_url must be a plain local Ollama HTTP endpoint")
    feeds = configuration.get("feeds", [])
    if not feeds:
        errors.append("at least one feed is required")
    for feed in feeds:
        try:
            if not feed.get("name") or feed.get("kind") not in {"paper", "news"}:
                raise ValueError()
            canonical_url(feed.get("url", ""))
        except (ValueError, AttributeError):
            errors.append("invalid feed configuration")
    sources = configuration.get("sources", {})
    if configuration.get("delivery", {}).get("send_enabled") is True:
        errors.extend(validate_delivery_targets(configuration["delivery"]))
    if sources.get("brave_enabled"):
        errors.append("Brave not implemented; cannot enable paid source")
    if sources.get("exa_enabled"):
        errors.append("Exa not implemented; cannot enable paid source")
    if sources.get("tavily_enabled"):
        queries = sources.get("tavily_queries", [])
        if (not isinstance(queries, list) or not 1 <= len(queries) <= 4 or
                any(not isinstance(query, str) or not query.strip() for query in queries)):
            errors.append("sources.tavily_queries must contain 1..4 nonempty strings")
        calls = sources.get("tavily_max_calls", 2)
        if not isinstance(calls, int) or not 1 <= calls <= 4:
            errors.append("sources.tavily_max_calls must be 1..4")
    if sources.get("hacker_news") and not 1 <= sources.get("hn_max_calls", 2) <= 20:
        errors.append("sources.hn_max_calls must be 1..20")
    if sources.get("huggingface") and not 1 <= sources.get("hf_limit", 20) <= 100:
        errors.append("sources.hf_limit must be 1..100")
    if not 1 <= sources.get("max_per_feed", 20) <= 100:
        errors.append("sources.max_per_feed must be 1..100")
    return errors
