from ai_daily_briefing.hf_papers import parse_daily_papers


def test_hf_rediscovery_of_old_arxiv_paper_is_not_current_news():
    from ai_daily_briefing.shortlist import shortlist_candidates
    item = {"kind": "paper", "source": "Hugging Face Daily Papers",
            "title": "TextReg: Mitigating Prompt Distributional Overfitting via Regularized Text-Space Optimization",
            "url": "https://arxiv.org/abs/2605.21318", "published": "2026-10-05T00:00:00Z",
            "abstract": "Generalizable prompt optimization of language models."}
    assert shortlist_candidates([item], "2026-10-06T00:50:00-06:00") == []


def test_arxiv_previous_month_remains_eligible_at_month_boundary():
    from ai_daily_briefing.shortlist import shortlist_candidates
    item = {"kind": "paper", "source": "Hugging Face Daily Papers", "title": "LLM inference engine",
            "url": "https://arxiv.org/abs/2609.12345", "published": "2026-10-01T01:00:00Z"}
    assert len(shortlist_candidates([item], "2026-10-01T07:00:00Z")) == 1


def test_hf_daily_papers_normalizes_paper_and_ignores_votes_as_proof():
    payload = [{"paper": {"id": "2610.01092", "title": "Agent systems",
                           "summary": "We evaluate agents", "publishedAt": "2026-10-01T00:00:00Z"},
                "numUpvotes": 10}]
    item = parse_daily_papers(payload)[0]
    assert item["url"] == "https://arxiv.org/abs/2610.01092"
    assert item["evidence_level"] == "api-metadata"
    assert item["votes"] == 10
