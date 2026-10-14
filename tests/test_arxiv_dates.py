import pytest

from ai_daily_briefing.arxiv_dates import original_arxiv_date, original_arxiv_dates


FEED = b'''<feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>http://arxiv.org/abs/2610.12582v1</id>
<published>2026-10-08T18:05:42Z</published>
<updated>2026-10-13T00:00:00Z</updated></entry></feed>'''


def test_arxiv_original_date_is_published_not_updated():
    calls = []
    def fetch(url, limit):
        calls.append((url, limit))
        return FEED, "application/atom+xml"
    assert original_arxiv_date("https://arxiv.org/abs/2610.12582", fetch=fetch) == "2026-10-08T18:05:42Z"
    assert calls[0][0] == "https://export.arxiv.org/api/query?id_list=2610.12582"


def test_arxiv_original_date_rejects_mismatched_response():
    with pytest.raises(ValueError, match="arxiv metadata mismatch"):
        original_arxiv_date("https://arxiv.org/abs/2610.99999", fetch=lambda url, limit: (FEED, "application/atom+xml"))


def test_non_arxiv_paper_does_not_need_arxiv_api():
    assert original_arxiv_date("https://example.org/paper", fetch=lambda *args: pytest.fail("API called")) is None


def test_malformed_metadata_is_rejected_as_source_error():
    with pytest.raises(ValueError, match="invalid arxiv metadata"):
        original_arxiv_date("https://arxiv.org/abs/2610.12582",
                            fetch=lambda url, limit: (b"<feed>", "application/atom+xml"))


def test_batch_fetches_original_dates_in_one_request():
    second = b'''<entry><id>http://arxiv.org/abs/2610.12495v1</id>
<published>2026-10-12T13:12:12Z</published></entry>'''
    feed = FEED.replace(b"</feed>", second + b"</feed>")
    urls = ["https://arxiv.org/abs/2610.12582", "https://arxiv.org/abs/2610.12495"]
    calls = []
    def fetch(url, limit):
        calls.append((url, limit))
        return feed, "application/atom+xml"
    assert original_arxiv_dates(urls, fetch=fetch) == {
        urls[0]: "2026-10-08T18:05:42Z", urls[1]: "2026-10-12T13:12:12Z"}
    assert calls == [("https://export.arxiv.org/api/query?id_list=2610.12582,2610.12495&max_results=2", 2_000_000)]


def test_large_arxiv_candidate_set_is_split_into_bounded_requests():
    urls = [f"https://arxiv.org/abs/2610.{n:05d}" for n in range(1, 102)]
    calls = []
    def fetch(url, limit):
        from urllib.parse import parse_qs, urlsplit
        query = parse_qs(urlsplit(url).query)
        ids = query["id_list"][0].split(",")
        calls.append(ids)
        assert len(ids) <= 100 and int(query["max_results"][0]) == len(ids)
        entries = "".join(f"<entry><id>http://arxiv.org/abs/{identifier}v1</id>"
                          f"<published>2026-10-12T12:00:00Z</published></entry>" for identifier in ids)
        return (f'<feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>'.encode(),
                "application/atom+xml")
    dates = original_arxiv_dates(urls, fetch=fetch)
    assert len(calls) == 2 and len(dates) == len(urls)
    assert all(dates[url] == "2026-10-12T12:00:00Z" for url in urls)


def test_legacy_arxiv_id_does_not_invalidate_modern_ids_in_same_batch():
    urls = ["https://arxiv.org/abs/cs/9901001", "https://arxiv.org/abs/2610.12582"]
    feed = b'''<feed xmlns="http://www.w3.org/2005/Atom">
    <entry><id>http://arxiv.org/abs/cs/9901001v1</id><published>1999-01-05T00:56:54Z</published></entry>
    <entry><id>http://arxiv.org/abs/2610.12582v1</id><published>2026-10-12T12:00:00Z</published></entry>
    </feed>'''
    assert original_arxiv_dates(urls, fetch=lambda url, limit: (feed, "application/atom+xml")) == {
        urls[0]: "1999-01-05T00:56:54Z", urls[1]: "2026-10-12T12:00:00Z"}