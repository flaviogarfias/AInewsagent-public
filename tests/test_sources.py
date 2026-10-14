from ai_daily_briefing.sources import parse_feed, collect_feeds


def test_atom_and_rss_are_normalized_and_bounded():
    atom = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Agent paper</title><id>https://arxiv.org/abs/2510.12345v1</id><summary>Methods and results</summary><published>2026-10-03T01:00:00Z</published></entry></feed>'''
    rss = b'''<rss><channel><item><title>Chip release</title><link>https://example.org/chip</link><description>Production rollout</description><pubDate>Sat, 03 Oct 2026 01:00:00 GMT</pubDate></item></channel></rss>'''
    assert parse_feed(atom, "paper", "arxiv")[0]["url"] == "https://arxiv.org/abs/2510.12345"
    assert parse_feed(rss, "news", "vendor")[0]["title"] == "Chip release"
    result = collect_feeds([{"url": "https://feeds.example/a", "kind": "news", "name": "vendor"}],
                           fetch=lambda url: rss, max_per_feed=1)
    assert len(result) == 1
    assert result[0]["source"] == "vendor"
