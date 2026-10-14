from ai_daily_briefing.hacker_news import parse_hits, fetch_stories


def test_hn_uses_original_url_and_rejects_low_point_discussions():
    payload = {"hits": [
        {"title": "AI infrastructure production deployment", "url": "https://vendor.example/news",
         "created_at": "2026-10-03T12:00:00Z", "points": 72, "objectID": "12"},
        {"title": "Ask HN", "url": None, "created_at": "2026-10-03T11:00:00Z",
         "points": 200, "objectID": "13"},
        {"title": "Early link", "url": "https://vendor.example/early",
         "created_at": "2026-10-03T11:00:00Z", "points": 3, "objectID": "14"},
    ]}
    items = parse_hits(payload, min_points=50)
    assert len(items) == 1
    assert items[0]["url"] == "https://vendor.example/news"
    assert items[0]["evidence_level"] == "discovery-only"


def test_hn_paginates_with_strict_request_budget():
    requested = []
    def fetch(url):
        requested.append(url)
        return {"hits": [], "nbPages": 100}
    assert fetch_stories(["LLM", "AI agents"], fetch=fetch, max_calls=1) == []
    assert len(requested) == 1
