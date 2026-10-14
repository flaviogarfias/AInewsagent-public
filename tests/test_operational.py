import pytest
from ai_daily_briefing.arxiv_dates import original_arxiv_dates
from ai_daily_briefing.operational import run_once


def test_malformed_arxiv_atom_blocks_delivery_and_notifies_failure(tmp_path, monkeypatch):
    paper = {"kind": "paper", "title": "LLM inference research",
             "url": "https://arxiv.org/abs/2610.12582", "source": "arXiv cs.CL",
             "published": "2026-10-13T04:00:00Z",
             "abstract": "Extensive LLM inference benchmarks with reproducible performance measurements."}
    monkeypatch.setattr("ai_daily_briefing.runtime.original_arxiv_dates",
                        lambda urls: original_arxiv_dates(urls, fetch=lambda url, limit: (b"<feed/>", "application/atom+xml")))
    monkeypatch.setattr("ai_daily_briefing.operational.deliver_with_stable_connections",
                        lambda *args, **kwargs: pytest.fail("email delivery reached"))
    statuses = []
    config = {"model": {"name": "qwen3:4b"},
              "delivery": {"send_enabled": True, "sender": "sender@example.net",
                           "recipient": "recipient@example.net", "slack_channel_id": "C123456789",
                           "slack_channel_name": "briefing-updates"}}
    result = run_once(config, tmp_path, deliver=True,
        collect=lambda config: {"candidates": [paper], "source_errors": 0, "source_counts": {}},
        evaluate=lambda item: pytest.fail("paper evaluation reached"),
        connect=lambda: {"client": "stable-client", "channel_name": "briefing-updates"},
        notify=lambda client, channel, name, run_id, status, selected, errors, workdir:
            statuses.append((status, selected, errors)) or "1234.5678",
        now="2026-10-13T09:30:00-06:00")
    assert result["status"] == "failed"
    assert result["source_errors"] == 1
    assert result["items"] == []
    assert statuses == [("failed", 0, 1)]


def test_operational_run_rejects_delivery_before_collection_or_connection(tmp_path):
    with pytest.raises(ValueError, match="disabled"):
        run_once({"delivery": {"send_enabled": False}}, tmp_path, deliver=True,
                 collect=lambda *args: pytest.fail("collection called"),
                 connect=lambda *args: pytest.fail("connection called"))


def test_operational_no_news_notifies_once_without_email(tmp_path):
    calls = []
    config = {"model": {"name": "qwen3-hermes:8b"},
              "delivery": {"send_enabled": True, "sender": "sender@example.net",
                           "recipient": "recipient@example.net", "slack_channel_id": "C123456789", "slack_channel_name": "briefing-updates"}}
    result = run_once(config, tmp_path, deliver=True,
        collect=lambda config: {"candidates": [], "source_errors": 0, "source_counts": {}},
        evaluate=lambda item: pytest.fail("model called"),
        connect=lambda: {"client": "stable-client", "channel_name": "briefing-updates"},
        notify=lambda client, channel, name, run_id, status, selected, errors, workdir:
            calls.append((client, channel, status, selected, errors)) or "1234.5678",
        now="2026-10-06T07:00:00-06:00")
    assert result["status"] == "no-news"
    assert calls == [("stable-client", "C123456789", "no-news", 0, 0)]


def test_delivery_rejects_example_targets_without_collecting_or_connecting(tmp_path):
    config = {"delivery": {"send_enabled": True, "sender": "replace@example.org",
                           "recipient": "recipient@example.net", "slack_channel_id": "REPLACE"}}
    with pytest.raises(ValueError, match="delivery.sender"):
        run_once(config, tmp_path, deliver=True,
                 collect=lambda *args: pytest.fail("collection called"),
                 connect=lambda *args: pytest.fail("connection called"))


def test_operational_run_generates_no_send_report_without_connections(tmp_path):
    config = {"model": {"name": "qwen3-hermes:8b"}, "delivery": {"send_enabled": False}}
    result = run_once(config, tmp_path, deliver=False,
                      collect=lambda config: {"candidates": [], "source_errors": 0,
                                               "source_counts": {}},
                      evaluate=lambda item: pytest.fail("model called"),
                      connect=lambda *args: pytest.fail("connection called"),
                      now="2026-10-06T07:00:00-06:00")
    assert result["status"] == "no-news"
    assert result["items"] == []
