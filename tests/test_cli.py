from ai_daily_briefing.cli import collect_configured, collect_configured_diagnostics


def test_collector_combines_public_feeds_and_hf_without_paid_calls():
    config = {"feeds": [{"url": "https://example.org/feed", "kind": "news", "name": "Official"}],
              "sources": {"huggingface": True, "hf_limit": 5, "max_per_feed": 5}}
    seen = []
    result = collect_configured(config,
        hf=lambda limit: [{"url": "https://arxiv.org/abs/2510.12345", "kind": "paper", "title": "A"}],
        feeds=lambda feeds, max_per_feed: seen.extend(feeds) or [{"url": "https://example.org/a", "kind": "news", "title": "B"}])
    assert [item["kind"] for item in result] == ["paper", "news"]
    assert len(seen) == 1


def test_diagnostic_collector_keeps_healthy_feeds_and_records_source_failure():
    config = {"feeds": [
        {"url": "https://example.org/bad", "kind": "news", "name": "Bad"},
        {"url": "https://example.org/ok", "kind": "news", "name": "Good"}],
        "sources": {"huggingface": False, "hacker_news": False}}
    def fetch(feeds, max_per_feed):
        if feeds[0]["name"] == "Bad":
            raise OSError("request with sensitive URL failed")
        return [{"kind": "news", "title": "LLM infrastructure", "url": "https://example.org/story",
                 "published": "2026-10-03T00:00:00Z", "source": "Good"}]
    result = collect_configured_diagnostics(config, feeds=fetch)
    assert [item["source"] for item in result["candidates"]] == ["Good"]
    assert result["source_errors"] == 1
    assert result["source_counts"] == {"Bad": 0, "Good": 1}
    assert "request with sensitive URL" not in str(result)


def test_collector_adds_hn_only_when_enabled_and_bounded():
    config = {"feeds": [], "sources": {"huggingface": False, "hacker_news": True,
                                         "hn_queries": ["AI agents"], "hn_max_calls": 1}}
    result = collect_configured(config, hf=lambda limit: [], feeds=lambda feeds, max_per_feed: [],
                                hn=lambda queries, max_calls: [{"kind": "news", "title": "HN",
                                         "url": "https://example.org/story"}])
    assert result == [{"kind": "news", "title": "HN", "url": "https://example.org/story"}]


def test_semantic_scholar_requires_key_before_any_source_call():
    import pytest
    config = {"feeds": [], "sources": {"semantic_scholar": True}}
    with pytest.raises(ValueError, match="SEMANTIC_SCHOLAR_API_KEY"):
        collect_configured(config, hf=lambda limit: [], feeds=lambda feeds, max_per_feed: [],
                           semantic_key="")


def test_tavily_is_off_by_default_and_requires_a_key_before_collection():
    import pytest
    config = {"feeds": [], "sources": {"tavily_enabled": True,
              "tavily_queries": ["LLM inference"], "tavily_max_calls": 1}}
    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        collect_configured_diagnostics(config, feeds=lambda *args, **kwargs: [],
            tavily=lambda *args, **kwargs: pytest.fail("network called"), tavily_key="")
    seen = []
    result = collect_configured_diagnostics(config, feeds=lambda *args, **kwargs: [],
        tavily=lambda queries, key, max_calls: seen.append((queries, key, max_calls)) or [
            {"kind": "news", "title": "AI news", "url": "https://example.org/news"}],
        tavily_key="test-key")
    assert result["source_counts"]["Tavily discovery"] == 1
    assert seen == [(["LLM inference"], "test-key", 1)]
    off = collect_configured_diagnostics({"feeds": [], "sources": {}},
        tavily=lambda *args, **kwargs: pytest.fail("disabled source called"))
    assert off["source_errors"] == 0


def test_tavily_error_is_reported_without_exposing_key():
    config = {"feeds": [], "sources": {"tavily_enabled": True,
              "tavily_queries": ["AI agents"], "tavily_max_calls": 1}}
    def fail(queries, key, max_calls):
        raise OSError("test-key")
    result = collect_configured_diagnostics(config, tavily=fail, tavily_key="test-key")
    assert result["source_errors"] == 1
    assert result["source_counts"]["Tavily discovery"] == 0
    assert "test-key" not in str(result)


def test_cli_dry_run_reports_artifacts_without_delivery(tmp_path, monkeypatch, capsys):
    import json
    from ai_daily_briefing import cli, runtime
    config = {"schedule": {"timezone": "America/Mexico_City", "time": "07:00",
                            "days": ["monday"]}, "model": {"name": "qwen3-hermes:8b"},
              "feeds": [{"kind": "news", "name": "Example", "url": "https://example.org/rss"}]}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setattr(runtime, "run_configured_dry_run", lambda config, workdir: {
        "run_id": "test-run", "status": "no-news", "items": [], "artifacts": {}})
    assert cli.main([str(path), "--dry-run", "--workdir", str(tmp_path)]) == 0
    assert '"status": "no-news"' in capsys.readouterr().out
