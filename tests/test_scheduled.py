from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from ai_daily_briefing.scheduled import run_scheduled


SCHEDULE = {"timezone": "America/Mexico_City", "time": "07:00",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]}
ZONE = ZoneInfo("America/Mexico_City")


def test_disabled_or_late_job_never_starts_collection(tmp_path):
    calls = []
    execute = lambda *args, **kwargs: calls.append(1)
    config = {"schedule": SCHEDULE, "delivery": {"send_enabled": False,
              "sender": "sender@example.net", "recipient": "recipient@example.net",
              "slack_channel_id": "C123456789", "slack_channel_name": "briefing-updates"}}
    assert run_scheduled(config, tmp_path, at=datetime(2026, 10, 7, 7, tzinfo=ZONE),
                         execute=execute)["status"] == "disabled"
    config["delivery"]["send_enabled"] = True
    assert run_scheduled(config, tmp_path, at=datetime(2026, 10, 7, 8, tzinfo=ZONE),
                         execute=execute)["status"] == "outside-window"
    assert calls == []
    assert not list(tmp_path.iterdir())


def test_one_attempt_per_calendar_day_even_after_uncertain_failure(tmp_path):
    config = {"schedule": SCHEDULE, "delivery": {"send_enabled": True,
              "sender": "sender@example.net", "recipient": "recipient@example.net",
              "slack_channel_id": "C123456789", "slack_channel_name": "briefing-updates"}}
    when = datetime(2026, 10, 7, 7, 1, tzinfo=ZONE)
    calls = []
    def uncertain(*args, **kwargs):
        calls.append((args, kwargs))
        raise TimeoutError("acceptance uncertain")
    with pytest.raises(TimeoutError):
        run_scheduled(config, tmp_path, at=when, execute=uncertain)
    assert len(calls) == 1
    assert calls[0][1] == {"deliver": True}
    assert run_scheduled(config, tmp_path, at=when, execute=uncertain)["status"] == "already-attempted"
    assert len(calls) == 1
    marker = tmp_path / "scheduled-attempts" / "2026-10-07.json"
    assert marker.exists()
    assert marker.stat().st_mode & 0o777 == 0o600


def test_invalid_destination_does_not_consume_daily_attempt(tmp_path):
    config = {"schedule": SCHEDULE, "delivery": {"send_enabled": True,
               "sender": "replace@example.org", "recipient": "recipient@example.net",
               "slack_channel_id": "C123456789", "slack_channel_name": "briefing-updates"}}
    with pytest.raises(ValueError, match="delivery.sender"):
        run_scheduled(config, tmp_path, at=datetime(2026, 10, 7, 7, tzinfo=ZONE),
                      execute=lambda *args, **kwargs: pytest.fail("should not execute"))
    assert not (tmp_path / "scheduled-attempts").exists()


def test_verified_result_updates_daily_marker_without_repeating(tmp_path):
    import json
    config = {"schedule": SCHEDULE, "delivery": {"send_enabled": True,
              "sender": "sender@example.net", "recipient": "recipient@example.net",
              "slack_channel_id": "C123456789", "slack_channel_name": "briefing-updates"}}
    when = datetime(2026, 10, 7, 7, 2, tzinfo=ZONE)
    execute = lambda *args, **kwargs: {"status": "sent", "run_id": "run-1"}
    result = run_scheduled(config, tmp_path, at=when, execute=execute)
    assert result == {"status": "sent", "run_id": "run-1"}
    marker = tmp_path / "scheduled-attempts" / "2026-10-07.json"
    assert json.loads(marker.read_text()) == {"date": "2026-10-07", "status": "sent", "run_id": "run-1"}
    assert marker.stat().st_mode & 0o777 == 0o600
    assert run_scheduled(config, tmp_path, at=when, execute=execute)["status"] == "already-attempted"
