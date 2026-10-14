"""Preview configured run instants without creating or enabling a scheduler job."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

_WEEKDAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
             "friday": 4, "saturday": 5, "sunday": 6}


def in_dispatch_window(schedule: dict, instant: datetime, grace_minutes: int = 15) -> bool:
    """Only run near the local slot; never backfill an old missed morning."""
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("instant must be timezone-aware")
    if not 1 <= grace_minutes <= 60:
        raise ValueError("grace_minutes must be 1..60")
    local = instant.astimezone(ZoneInfo(schedule["timezone"]))
    if local.weekday() not in {_WEEKDAYS[day] for day in schedule["days"]}:
        return False
    hour, minute = map(int, schedule["time"].split(":"))
    start = datetime.combine(local.date(), time(hour, minute), tzinfo=local.tzinfo)
    return start <= local < start + timedelta(minutes=grace_minutes)


def next_runs(schedule: dict, after: datetime, count: int = 3) -> list[datetime]:
    """Return the next strictly future local run times; this performs no I/O."""
    if after.tzinfo is None or after.utcoffset() is None:
        raise ValueError("after must be timezone-aware")
    if not 1 <= count <= 30:
        raise ValueError("count must be 1..30")
    zone = ZoneInfo(schedule["timezone"])
    hour, minute = map(int, schedule["time"].split(":"))
    days = {_WEEKDAYS[day] for day in schedule["days"]}
    if not days:
        raise ValueError("at least one delivery day required")
    current = after.astimezone(zone)
    result: list[datetime] = []
    for offset in range(count * 7 + 7):
        day = current.date() + timedelta(days=offset)
        if day.weekday() not in days:
            continue
        candidate = datetime.combine(day, time(hour, minute), tzinfo=zone)
        if candidate > after:
            result.append(candidate)
            if len(result) == count:
                break
    return result
