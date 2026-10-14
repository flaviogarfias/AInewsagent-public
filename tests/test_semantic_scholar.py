import pytest
from ai_daily_briefing.semantic_scholar import enrich_papers


def test_semantic_scholar_enriches_only_bounded_arxiv_ids():
    paper = {"kind": "paper", "url": "https://arxiv.org/abs/2610.00049", "title": "Old title", "abstract": ""}
    visited = []
    def fetch(url, headers):
        visited.append(url)
        assert headers["x-api-key"] == "test-key"
        return {"paperId": "123", "title": "Original title", "abstract": "Full scholarly abstract with experimental details",
                "citationCount": 0, "influentialCitationCount": 0,
                "externalIds": {"ArXiv": "2610.00049"}}
    result = enrich_papers([paper], "test-key", fetch=fetch, max_calls=1)
    assert len(visited) == 1
    assert result[0]["title"] == "Old title"
    assert result[0]["abstract"].startswith("Full scholarly")
    assert result[0]["citation_count"] == 0


def test_semantic_scholar_requires_explicit_key_and_never_substitutes_results():
    with pytest.raises(ValueError):
        enrich_papers([{"kind": "paper", "url": "https://arxiv.org/abs/2610.00049"}], "")
