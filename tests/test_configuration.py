from ai_daily_briefing.configuration import validate_configuration


def test_model_endpoint_cannot_send_source_text_to_remote_host():
    configuration = {"schedule": {"timezone": "America/Mexico_City", "time": "07:00",
                                  "days": ["monday"]},
                     "model": {"name": "qwen3:8b", "base_url": "https://models.example.org"},
                     "feeds": [{"name": "Source", "kind": "news", "url": "https://example.org/rss"}]}
    assert any("model.base_url" in error for error in validate_configuration(configuration))
    configuration["model"]["base_url"] = "http://127.0.0.1:11434"
    assert validate_configuration(configuration) == []


def test_model_endpoint_rejects_credentials_and_paths():
    configuration = {"schedule": {"timezone": "America/Mexico_City", "time": "07:00",
                                  "days": ["monday"]},
                     "model": {"name": "qwen3:8b", "base_url": "http://user:pass@127.0.0.1:11434/x"},
                     "feeds": [{"name": "Source", "kind": "news", "url": "https://example.org/rss"}]}
    assert any("model.base_url" in error for error in validate_configuration(configuration))


def test_configuration_rejects_sunday_schedule():
    configuration = {
        "schedule": {"timezone": "America/Mexico_City", "days": ["monday", "sunday"]},
        "model": {"name": "qwen3-hermes:8b"},
    }

    errors = validate_configuration(configuration)

    assert "sunday is not an allowed delivery day" in errors


def test_configuration_requires_complete_schedule_and_safe_feed_urls():
    configuration = {"schedule": {"timezone": "Invalid/Zone", "time": "25:00", "days": []},
                     "model": {"name": ""},
                     "feeds": [{"name": "bad", "kind": "news", "url": "file:///etc/passwd"}]}
    errors = validate_configuration(configuration)
    assert any("timezone" in error for error in errors)
    assert any("time" in error for error in errors)
    assert any("model" in error for error in errors)
    assert any("feed" in error for error in errors)


def test_configuration_rejects_unbounded_or_missing_tavily_queries():
    base = {"schedule": {"timezone": "America/Mexico_City", "time": "07:00", "days": ["monday"]},
            "model": {"name": "qwen3-hermes:8b"},
            "feeds": [{"name": "Source", "kind": "news", "url": "https://example.org/rss"}]}
    base["sources"] = {"tavily_enabled": True, "tavily_queries": [], "tavily_max_calls": 100}
    errors = validate_configuration(base)
    assert any("tavily_queries" in error for error in errors)
    assert any("tavily_max_calls" in error for error in errors)


def test_configuration_accepts_bounded_optional_tavily():
    base = {"schedule": {"timezone": "America/Mexico_City", "time": "07:00", "days": ["monday"]},
            "model": {"name": "qwen3-hermes:8b"},
            "feeds": [{"name": "Source", "kind": "news", "url": "https://example.org/rss"}],
            "sources": {"tavily_enabled": True, "tavily_queries": ["LLM inference"], "tavily_max_calls": 1}}
    assert validate_configuration(base) == []


def test_configuration_rejects_paid_sources_or_unbounded_public_calls():
    configuration = {"schedule": {"timezone": "America/Mexico_City", "time": "07:00",
                                  "days": ["monday"]},
                     "model": {"name": "qwen3-hermes:8b"},
                     "feeds": [{"name": "Source", "kind": "news", "url": "https://example.org/rss"}],
                     "sources": {"brave_enabled": True, "paid_call_budget": 0,
                                 "hacker_news": True, "hn_max_calls": 100}}
    errors = validate_configuration(configuration)
    assert any("Brave" in error for error in errors)
    assert any("hn_max_calls" in error for error in errors)


def test_enabled_delivery_requires_real_targets_before_any_collection():
    configuration = {"schedule": {"timezone": "America/Mexico_City", "time": "07:00",
                                  "days": ["monday"]},
                     "model": {"name": "qwen3-hermes:8b"},
                     "feeds": [{"name": "Source", "kind": "news", "url": "https://example.org/rss"}],
                     "delivery": {"send_enabled": True, "sender": "replace@example.org",
                                  "recipient": "other@example.org", "slack_channel_id": "REPLACE"}}
    errors = validate_configuration(configuration)
    assert any("delivery.sender" in error for error in errors)
    assert any("delivery.recipient" in error for error in errors)
    assert any("delivery.slack_channel_id" in error for error in errors)
    assert any("delivery.slack_channel_name" in error for error in errors)


def test_disabled_delivery_accepts_example_placeholders():
    configuration = {"schedule": {"timezone": "America/Mexico_City", "time": "07:00",
                                  "days": ["monday"]},
                     "model": {"name": "qwen3-hermes:8b"},
                     "feeds": [{"name": "Source", "kind": "news", "url": "https://example.org/rss"}],
                     "delivery": {"send_enabled": False, "sender": "replace@example.org",
                                  "recipient": "replace@example.org", "slack_channel_id": "REPLACE"}}
    assert validate_configuration(configuration) == []
