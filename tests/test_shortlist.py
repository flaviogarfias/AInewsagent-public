from ai_daily_briefing.shortlist import shortlist_candidates


def test_shortlist_bounds_each_category_and_prioritizes_core():
    items = [
        {"kind": "paper", "title": "Cancer treatment experiment", "abstract": "Drug matrices",
         "url": "https://example.org/a", "published": "2026-10-03T03:00:00Z", "votes": 100},
        {"kind": "paper", "title": "LLM agent inference", "abstract": "Inference serving",
         "url": "https://example.org/b", "published": "2026-10-03T02:00:00Z", "votes": 2},
        {"kind": "news", "title": "AI agents launch", "abstract": "",
         "url": "https://example.org/c", "published": "2026-10-03T02:00:00Z", "hn_points": 70},
    ]
    selected = shortlist_candidates(items, "2026-10-03T07:00:00-06:00", per_kind=1)
    assert [item["url"] for item in selected] == ["https://example.org/b", "https://example.org/c"]


def test_shortlist_excludes_future_and_old_items():
    items = [{"kind": "paper", "title": "LLM", "url": "https://example.org/a",
              "published": "2026-10-07T00:00:00Z"}]
    assert shortlist_candidates(items, "2026-10-03T07:00:00-06:00") == []


def test_primary_news_feed_precedes_hn_hobby_discovery():
    base = {"kind": "news", "published": "2026-10-03T01:00:00Z"}
    items = [{**base, "title": "Show HN: LEGO AI generator", "url": "https://github.com/owner/repo",
              "source": "Hacker News discovery", "abstract": "", "hn_points": 500},
             {**base, "title": "Private learning from federated data", "url": "https://research.google/blog/private",
              "source": "Google Research", "abstract": "Mobile Systems"}]
    assert shortlist_candidates(items, "2026-10-03T07:00:00-06:00", per_kind=1)[0]["source"] == "Google Research"


def test_paper_shortlist_requires_ai_system_topic_in_title():
    base = {"kind": "paper", "published": "2026-10-05T12:00:00Z",
            "abstract": "A systematic machine learning benchmark with extensive ablations and strong validation."}
    items = [{**base, "title": "Nearest-neighbour baselines for fingerprint prediction from MS/MS spectra under different assumptions",
              "url": "https://example.org/spectra", "votes": 999},
             {**base, "title": "Reliable LLM inference for multi-agent systems",
              "url": "https://example.org/agents", "votes": 1}]
    selected = shortlist_candidates(items, "2026-10-05T07:00:00-06:00", per_kind=1)
    assert [item["url"] for item in selected] == ["https://example.org/agents"]
