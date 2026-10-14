import pytest
from urllib.error import HTTPError
from ai_daily_briefing.http_public import public_get


class Response:
    def __init__(self, url, status=200):
        self.url = url
        self.status = status
        self.headers = {"Content-Type": "text/html"}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return None
    def geturl(self):
        return self.url
    def read(self, limit):
        return b"original source content"


def test_public_get_rejects_private_dns_answers_before_opening():
    requests = []
    resolver = lambda host, port: [(None, None, None, None, ("127.0.0.1", 443))]
    with pytest.raises(ValueError, match="public"):
        public_get("https://example.org/a", resolver=resolver,
                   opener=lambda request, timeout, address: requests.append(request))
    assert requests == []


def test_public_get_rejects_redirect_even_to_another_public_domain():
    resolver = lambda host, port: [(None, None, None, None, ("93.184.215.14", 443))]
    with pytest.raises(ValueError, match="redirect"):
        public_get("https://example.org/a", resolver=resolver,
                   opener=lambda request, timeout, address: Response("https://elsewhere.org", 302))


def test_public_get_preserves_feed_trailing_slash_on_wire():
    requested = []
    resolver = lambda host, port: [(None, None, None, None, ("93.184.215.14", 443))]
    def opener(request, timeout, address):
        requested.append(request.full_url)
        return Response(request.full_url)
    public_get("https://example.org/blog/rss/", resolver=resolver, opener=opener)
    assert requested == ["https://example.org/blog/rss/"]


def test_public_get_follows_one_same_host_trailing_slash_redirect():
    resolver = lambda host, port: [(None, None, None, None, ("93.184.215.14", 443))]
    visited = []
    def opener(request, timeout, address):
        visited.append(request.full_url)
        if len(visited) == 1:
            raise HTTPError(request.full_url, 301, "Moved", {"Location": "/article/"}, None)
        return Response(request.full_url)
    content, _ = public_get("https://example.org/article", resolver=resolver, opener=opener)
    assert content
    assert visited == ["https://example.org/article", "https://example.org/article/"]


def test_public_get_passes_validated_dns_answer_into_the_connection():
    selected = (2, 1, 6, "", ("93.184.215.14", 443))
    observed = []
    def opener(request, timeout, address):
        observed.append((request.full_url, address))
        return Response(request.full_url)
    content, _ = public_get("https://example.org/article",
                            resolver=lambda host, port: [selected], opener=opener)
    assert content
    assert observed == [("https://example.org/article", selected)]
