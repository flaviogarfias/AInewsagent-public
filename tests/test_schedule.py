from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from ai_daily_briefing.schedule import next_runs, in_dispatch_window


SCHEDULE = {"timezone": "America/Mexico_City", "time": "07:00",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]}


def test_next_runs_skip_sunday_after_saturday_execution():
    after = datetime(2026, 10, 3, 7, 1, tzinfo=ZoneInfo("America/Mexico_City"))
    result = next_runs(SCHEDULE, after, count=3)
    assert [value.isoformat() for value in result] == [
        "2026-10-05T07:00:00-06:00", "2026-10-06T07:00:00-06:00",
        "2026-10-07T07:00:00-06:00"]


def test_next_runs_are_strictly_after_instant():
    after = datetime(2026, 10, 3, 13, 0, tzinfo=ZoneInfo("UTC"))
    assert next_runs(SCHEDULE, after, count=1)[0].isoformat() == "2026-10-05T07:00:00-06:00"


def test_next_runs_reject_naive_time():
    with pytest.raises(ValueError, match="timezone-aware"):
        next_runs(SCHEDULE, datetime(2026, 10, 3), count=1)

def test_before_and_at_seven_am_on_a_delivery_day():
    zone = ZoneInfo("America/Mexico_City")
    before = datetime(2026, 10, 6, 6, 59, 59, tzinfo=zone)
    at = datetime(2026, 10, 6, 7, 0, tzinfo=zone)
    assert next_runs(SCHEDULE, before, 1)[0].isoformat() == "2026-10-06T07:00:00-06:00"
    assert next_runs(SCHEDULE, at, 1)[0].isoformat() == "2026-10-07T07:00:00-06:00"

def test_sunday_and_month_boundary_remain_local():
    zone = ZoneInfo("America/Mexico_City")
    after = datetime(2026, 11, 1, 6, 0, tzinfo=zone)  # Sunday
    assert [value.isoformat() for value in next_runs(SCHEDULE, after, 2)] == [
        "2026-11-02T07:00:00-06:00", "2026-11-03T07:00:00-06:00"]

def test_utc_instant_on_prior_calendar_day_is_interpreted_in_mexico_city():
    instant = datetime(2026, 10, 6, 12, 59, tzinfo=ZoneInfo("UTC"))
    assert next_runs(SCHEDULE, instant, 1)[0].isoformat() == "2026-10-06T07:00:00-06:00"


def test_scheduled_dispatch_accepts_only_first_fifteen_minutes():
    zone = ZoneInfo("America/Mexico_City")
    assert not in_dispatch_window(SCHEDULE, datetime(2026, 10, 6, 6, 59, tzinfo=zone))
    assert in_dispatch_window(SCHEDULE, datetime(2026, 10, 6, 7, 0, tzinfo=zone))
    assert in_dispatch_window(SCHEDULE, datetime(2026, 10, 6, 7, 14, 59, tzinfo=zone))
    assert not in_dispatch_window(SCHEDULE, datetime(2026, 10, 6, 7, 15, tzinfo=zone))
    assert not in_dispatch_window(SCHEDULE, datetime(2026, 10, 11, 7, 0, tzinfo=zone))
