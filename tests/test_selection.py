from ai_daily_briefing.selection import select_daily


def test_selects_at_most_one_unseen_per_category_and_ignores_old():
    candidates = [
        {"kind": "paper", "title": "Old", "url": "https://example.org/old", "published": "2026-09-01T00:00:00Z", "score": 4},
        {"kind": "paper", "title": "A", "url": "https://example.org/a", "published": "2026-10-02T10:00:00Z", "score": 2},
        {"kind": "paper", "title": "B", "url": "https://example.org/b", "published": "2026-10-02T11:00:00Z", "score": 3},
        {"kind": "news", "title": "C", "url": "https://example.org/c", "published": "Sat, 03 Oct 2026 01:00:00 GMT", "score": 1},
    ]
    selection = select_daily(candidates, "2026-10-03T07:00:00-06:00", sent={"https://example.org/b"}, window_hours=48)
    assert [item["title"] for item in selection] == ["A", "C"]


def test_unknown_dates_are_excluded_not_assumed_recent():
    candidates = [{"kind": "paper", "title": "No date", "url": "https://example.org/a", "score": 4}]
    assert select_daily(candidates, "2026-10-03T07:00:00-06:00") == []


def test_core_candidate_precedes_peripheral_even_with_lower_score():
    base = {"kind": "paper", "published": "2026-10-03T01:00:00Z"}
    candidates = [{**base, "title": "Drug", "url": "https://example.org/a",
                   "topic_priority": "peripheral", "score": 4},
                  {**base, "title": "Agent", "url": "https://example.org/b",
                   "topic_priority": "core", "score": 2}]
    assert select_daily(candidates, "2026-10-03T07:00:00-06:00")[0]["title"] == "Agent"


def test_primary_news_wins_score_tie_against_hn_discovery():
    base = {"kind": "news", "score": 2, "topic_priority": "core"}
    candidates = [{**base, "title": "HN", "url": "https://github.com/owner/repo",
                   "source": "Hacker News discovery", "published": "2026-10-03T04:00:00Z"},
                  {**base, "title": "Official", "url": "https://research.google/blog/article",
                   "source": "Google Research", "published": "2026-10-03T01:00:00Z"}]
    assert select_daily(candidates, "2026-10-03T07:00:00-06:00")[0]["title"] == "Official"
