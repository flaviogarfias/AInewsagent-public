import json
from urllib.error import HTTPError
from io import BytesIO

import pytest

from ai_daily_briefing.tavily import search_news


class Response:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit):
        return json.dumps(self.payload).encode()


def test_basic_news_search_is_bounded_and_returns_valid_candidates():
    requests = []
    def open_request(request, timeout):
        requests.append(request)
        assert timeout <= 15
        if request.get_method() == "GET":
            return Response({"account": {"current_plan": "Researcher", "plan_usage": 637,
                                         "plan_limit": 1000, "paygo_usage": 0}})
        return Response({"results": [
            {"title": "A new LLM inference architecture", "url": "https://example.org/llm", "content": "Technical release", "published_date": "2026-10-05"},
            {"title": "Internal endpoint", "url": "http://127.0.0.1/admin", "content": "bad"}]})
    result = search_news(["LLM inference", "AI agents"], "test-key", max_calls=1, opener=open_request)
    assert len(requests) == 2
    assert requests[0].full_url == "https://api.tavily.com/usage"
    assert requests[1].get_header("Authorization") == "Bearer test-key"
    payload = json.loads(requests[1].data)
    assert payload["search_depth"] == "basic"
    assert payload["topic"] == "news"
    assert payload["max_results"] <= 10
    assert payload["include_answer"] is False
    assert len(result) == 1
    assert result[0]["kind"] == "news"
    assert result[0]["url"] == "https://example.org/llm"
    assert result[0]["published"] == "2026-10-05"
    assert result[0]["evidence_level"] == "search-snippet"


def test_tavily_preflight_refuses_paid_plan_before_search():
    calls = []
    def open_request(request, timeout):
        calls.append((request.full_url, request.get_method()))
        return Response({"account": {"current_plan": "Pay As You Go", "plan_usage": 0,
                                     "plan_limit": 1000, "paygo_usage": 0}})
    with pytest.raises(ValueError, match="Researcher"):
        search_news(["LLM"], "test-key", opener=open_request)
    assert calls == [("https://api.tavily.com/usage", "GET")]


def test_tavily_preflight_refuses_insufficient_free_quota():
    calls = []
    def open_request(request, timeout):
        calls.append(request.get_method())
        return Response({"account": {"current_plan": "Researcher", "plan_usage": 999,
                                     "plan_limit": 1000, "paygo_usage": 0}})
    with pytest.raises(ValueError, match="free credits"):
        search_news(["LLM", "AI agents"], "test-key", max_calls=2, opener=open_request)
    assert calls == ["GET"]


def test_tavily_failure_does_not_leak_key():
    def fail(request, timeout):
        raise HTTPError(request.full_url + "?key=test-key", 401, "Unauthorized test-key", {}, BytesIO(b"test-key"))
    with pytest.raises(OSError) as error:
        search_news(["LLM"], "test-key", opener=fail)
    assert "test-key" not in str(error.value)


def test_tavily_rejects_missing_key_and_invalid_bounds_before_calls():
    with pytest.raises(ValueError):
        search_news(["LLM"], "", opener=lambda *args: pytest.fail("network called"))
    with pytest.raises(ValueError):
        search_news(["LLM"], "x", max_calls=0, opener=lambda *args: pytest.fail("network called"))
