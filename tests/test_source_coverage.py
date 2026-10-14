"""Public source coverage contract for the portable example."""

import json
from pathlib import Path


def test_example_includes_independent_primary_ai_news_feeds():
    config = json.loads(Path("config/briefing.example.json").read_text())
    urls = {feed["url"] for feed in config["feeds"] if feed["kind"] == "news"}
    assert "https://openai.com/news/rss.xml" in urls
    assert "https://developer.nvidia.com/blog/feed" in urls
    assert "https://huggingface.co/blog/feed.xml" in urls
    assert config["sources"]["paid_call_budget"] == 0
