from ai_daily_briefing.identity import canonical_url, unique_candidates
import pytest


def test_normalizes_arxiv_versions_and_tracking_parameters():
    assert canonical_url("https://arxiv.org/pdf/2510.12345v2?utm_source=news#abstract") == "https://arxiv.org/abs/2510.12345"


def test_deduplicates_same_paper_and_rejects_invalid_links():
    items = [
        {"url": "https://arxiv.org/abs/2510.12345v1", "title": "Paper"},
        {"url": "https://arxiv.org/pdf/2510.12345v2", "title": "Paper"},
        {"url": "javascript:alert(1)", "title": "Bad"},
    ]
    assert [item["url"] for item in unique_candidates(items)] == ["https://arxiv.org/abs/2510.12345"]


@pytest.mark.parametrize("url", ["http://127.0.0.1/admin", "http://[::1]/private",
                                  "http://localhost:8888/", "http://169.254.169.254/latest/meta-data/",
                                  "http://10.1.2.3/", "http://192.168.1.4/"])
def test_private_destination_is_rejected(url):
    with pytest.raises(ValueError):
        canonical_url(url)
