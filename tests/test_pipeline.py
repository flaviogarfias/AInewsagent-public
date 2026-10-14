from ai_daily_briefing.pipeline import prepare_briefing
from ai_daily_briefing.state import DeliveryState
import pytest

def test_default_preparation_rejects_unverified_arxiv_date(tmp_path):
    paper = {"kind": "paper", "title": "Language model inference method",
             "url": "https://arxiv.org/abs/2610.12582", "source": "arXiv cs.CL",
             "published": "2026-10-13T04:00:00Z",
             "abstract": "An inference method for language models with extensive technical baselines and comparisons."}
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing([paper], state, "2026-10-13T09:30:00-06:00",
                                  evaluate=lambda item: pytest.fail("unverified paper evaluated"),
                                  verify=lambda url: True)
    assert report["items"] == []
    assert report["source_errors"] == 1


def test_old_arxiv_submission_is_not_new_just_because_rss_is_new(tmp_path):
    paper = {"kind": "paper", "title": "Language model inference method",
             "url": "https://arxiv.org/abs/2610.12582", "source": "arXiv cs.CL",
             "published": "2026-10-13T04:00:00Z",
             "abstract": "An inference method for language models with extensive technical baselines and comparisons."}
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing([paper], state, "2026-10-13T09:30:00-06:00",
                                  evaluate=lambda item: pytest.fail("old paper sent to model"),
                                  verify=lambda url: True,
                                  paper_date_lookup=lambda url: "2026-10-08T18:05:42Z")
    assert report["items"] == []
    assert report["source_errors"] == 0

def test_fresh_original_arxiv_date_is_selected_with_both_dates_even_when_red(tmp_path):
    paper = {"kind": "paper", "title": "Language model inference method",
             "url": "https://arxiv.org/abs/2610.12582", "source": "arXiv cs.CL",
             "published": "2026-10-13T04:00:00Z",
             "abstract": "An inference method for language models with extensive technical baselines and comparisons."}
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing([paper], state, "2026-10-13T09:30:00-06:00",
                                  evaluate=lambda item: {"criteria": {"novelty": False, "rigor": False,
                                      "ecosystem_relevance": False, "reproducibility": False},
                                      "summary": "Estudio de modelos."}, verify=lambda url: True,
                                  paper_date_lookup=lambda url: "2026-10-12T18:05:42Z")
    assert len(report["items"]) == 1
    item = report["items"][0]
    assert item["traffic_light"] == "red"
    assert item["published"] == "2026-10-12T18:05:42Z"
    assert item["feed_published"] == paper["published"]
    assert "Fecha original de arXiv: 2026-10-12T18:05:42Z" in report["html"]
    assert "Fecha del feed: 2026-10-13T04:00:00Z" in report["html"]

def test_invalid_arxiv_metadata_counts_as_source_error(tmp_path):
    paper = {"kind": "paper", "title": "Language model inference method",
             "url": "https://arxiv.org/abs/2610.12582", "source": "arXiv cs.CL",
             "published": "2026-10-13T04:00:00Z",
             "abstract": "An inference method for language models with extensive technical baselines and comparisons."}
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing([paper], state, "2026-10-13T09:30:00-06:00",
                                  evaluate=lambda item: pytest.fail("unverified date sent to model"),
                                  verify=lambda url: True,
                                  paper_date_lookup=lambda url: (_ for _ in ()).throw(ValueError("bad XML")))
    assert report["items"] == []
    assert report["source_errors"] == 1

def test_old_feed_entries_do_not_hide_a_fresh_seventh_paper(tmp_path):
    base = {"kind": "paper", "source": "arXiv cs.CL", "published": "2026-10-13T04:00:00Z",
            "abstract": "An inference method for language models with extensive technical baselines and comparisons."}
    papers = [{**base, "title": f"Language model inference study {n}",
               "url": f"https://arxiv.org/abs/2610.{n:05d}"} for n in range(1, 8)]
    # Six higher-ranked RSS entries are old; the seventh is genuinely recent.
    def date(url):
        return "2026-10-12T18:05:42Z" if url.endswith("00007") else "2026-10-08T18:05:42Z"
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing(papers, state, "2026-10-13T09:30:00-06:00",
                                  evaluate=lambda item: {"criteria": {"novelty": False, "rigor": False,
                                      "ecosystem_relevance": False, "reproducibility": False},
                                      "summary": "Estudio de modelos."}, verify=lambda url: True,
                                  paper_date_lookup=date, max_evaluations_per_kind=6)
    assert len(report["items"]) == 1
    assert report["items"][0]["url"] == papers[-1]["url"]

def test_batch_checks_all_arxiv_dates_before_shortlisting(tmp_path):
    base = {"kind": "paper", "source": "arXiv cs.CL", "published": "2026-10-13T04:00:00Z",
            "abstract": "An inference method for language models with extensive technical baselines and comparisons."}
    papers = [{**base, "title": f"Language model inference study {n}",
               "url": f"https://arxiv.org/abs/2610.{n:05d}"} for n in range(1, 8)]
    calls = []
    def lookup(urls):
        calls.append(urls)
        return {url: "2026-10-12T18:05:42Z" if url.endswith("00007") else "2026-10-08T18:05:42Z"
                for url in urls}
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing(papers, state, "2026-10-13T09:30:00-06:00",
                                  evaluate=lambda item: {"criteria": {"novelty": False, "rigor": False,
                                      "ecosystem_relevance": False, "reproducibility": False},
                                      "summary": "Estudio de modelos."}, verify=lambda url: True,
                                  paper_dates_lookup=lookup, max_evaluations_per_kind=2)
    assert len(report["items"]) == 1
    assert report["items"][0]["url"] == papers[-1]["url"]
    assert calls == [[paper["url"] for paper in papers]]


def test_dry_run_prepares_canonical_report_without_advancing_delivery(tmp_path):
    items = [{"kind": "paper", "title": "Multi-agent LLM inference research", "url": "https://arxiv.org/abs/2610.12345",
              "published": "2026-10-03T01:00:00Z", "abstract": "A multi-agent method for language model inference with detailed empirical evaluation and reproducible benchmarks.", "source": "arXiv"}]
    database = tmp_path / "state.sqlite3"
    with DeliveryState(database) as state:
        report = prepare_briefing(items, state, "2026-10-03T07:00:00-06:00",
                                  evaluate=lambda item: {"criteria": {"novelty": True, "rigor": True,
                                          "ecosystem_relevance": True, "reproducibility": True},
                                          "summary": "Evidence-based summary"},
                                  verify=lambda url: True,
                                  paper_date_lookup=lambda url: items[0]["published"])
        assert len(report["items"]) == 1
        assert report["items"][0]["traffic_light"] == "yellow"
        assert "Evidence-based summary" in report["html"]
        assert not state.is_sent(items[0]["url"])


def test_pipeline_rejects_short_news_and_caps_peripheral_paper(tmp_path):
    paper = {"kind": "paper", "title": "Cancer drug response", "url": "https://example.org/paper",
             "published": "2026-10-03T01:00:00Z", "source": "Journal",
             "abstract": "A long experimental pharmacogenomic study of cancer treatments and patient responses across extensive drug-response matrices."}
    news = {"kind": "news", "title": "Private learning", "url": "https://example.org/news",
            "published": "2026-10-03T01:00:00Z", "source": "Company", "abstract": "Mobile Systems"}
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing([paper, news], state, "2026-10-03T07:00:00-06:00",
                                  evaluate=lambda item: {"criteria": {"novelty": True, "rigor": True,
                                         "ecosystem_relevance": True, "reproducibility": True}, "summary": "Detailed source."},
                                  verify=lambda url: True)
    assert len(report["items"]) == 1
    assert report["items"][0]["traffic_light"] == "red"


def test_long_ellipsis_feed_teaser_fetches_original_article_before_evaluation(tmp_path):
    teaser = ("Enterprise applications have become increasingly demanding. Agentic AI "
              "has compounded the need for vast amounts of enterprise data with frequent, complex...")
    news = {"kind": "news", "title": "How to Rewrite Apache Spark UDFs for GPU Acceleration with AI Agents",
            "url": "https://developer.nvidia.com/blog/rewrite-apache-spark-udfs-gpu-acceleration-ai-agents",
            "source": "NVIDIA Developer", "published": "2026-10-13T21:33:21Z", "abstract": teaser}
    article = ("Spark UDFs force GPU pipelines back to CPU. Rewriting them as Spark SQL "
               "expressions or CUDA kernels reduces data transfers; the article reports "
               "measurements and an agent-driven workflow for testing conversions.")
    seen = []
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing([news], state, "2026-10-13T17:39:00-06:00",
            evaluate=lambda item: (seen.append(item["abstract"]) or
                {"criteria": {"economic_impact": False, "deployment": False,
                              "competitive_disruption": False, "source_verifiability": True},
                 "summary": "Se describen conversiones verificadas de UDF de Spark para evitar caídas a CPU."}),
            verify=lambda url: True, fetch_text=lambda url: article)
    assert seen == [article]
    assert len(report["items"]) == 1
    assert report["items"][0]["traffic_light"] == "red"


def test_substantive_paper_with_ellipsis_keeps_its_place(tmp_path):
    abstract = ("We benchmark multiple language model inference systems against established "
                "baselines with detailed latency measurements and reproducible comparisons...")
    paper = {"kind": "paper", "title": "LLM inference benchmarks", "url": "https://example.org/paper",
             "source": "Journal", "published": "2026-10-13T04:00:00Z", "abstract": abstract}
    seen = []
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing([paper], state, "2026-10-13T17:39:00-06:00",
            evaluate=lambda item: (seen.append(item["abstract"]) or
                {"criteria": {"novelty": False, "rigor": False,
                              "ecosystem_relevance": False, "reproducibility": False},
                 "summary": "Estudio de inferencia de LLM."}), verify=lambda url: True)
    assert seen == [abstract]
    assert len(report["items"]) == 1
    assert report["items"][0]["traffic_light"] == "red"


def test_news_with_short_feed_label_can_use_original_article_text(tmp_path):
    news = {"kind": "news", "title": "LLM inference launch", "url": "https://example.org/news",
            "published": "2026-10-03T01:00:00Z", "source": "Vendor", "abstract": "Mobile Systems"}
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing([news], state, "2026-10-03T07:00:00-06:00",
                                  evaluate=lambda item: {"criteria": {"economic_impact": True,
                                         "deployment": True, "competitive_disruption": False,
                                         "source_verifiability": True}, "summary": "Probado en producción."},
                                  verify=lambda url: True,
                                  fetch_text=lambda url: "A new LLM inference system deployed for customers in production with measured improvements to latency and cost.")
    assert len(report["items"]) == 1
    assert report["items"][0]["summary"] == "Probado en producción."


def test_evaluates_multiple_shortlisted_candidates_then_selects_best(tmp_path):
    base = {"kind": "paper", "published": "2026-10-03T01:00:00Z", "source": "arXiv",
            "abstract": "We evaluate LLM agent infrastructure against strong baselines with detailed deployment and reproducibility evidence."}
    items = [{**base, "title": "First agent paper", "url": "https://example.org/one"},
             {**base, "title": "Second agent paper", "url": "https://example.org/two"}]
    calls = []
    def evaluate(item):
        calls.append(item["url"])
        strong = item["title"].startswith("Second")
        return {"criteria": {"novelty": strong, "rigor": strong, "ecosystem_relevance": True,
                              "reproducibility": strong}, "summary": "Verified evidence."}
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing(items, state, "2026-10-03T07:00:00-06:00",
                                  evaluate=evaluate, verify=lambda url: True,
                                  max_evaluations_per_kind=1)
    assert len(calls) == 1
    assert len(report["items"]) == 1


def test_one_article_timeout_does_not_abort_other_candidates(tmp_path):
    base = {"kind": "news", "published": "2026-10-03T01:00:00Z", "source": "Vendor", "abstract": ""}
    items = [{**base, "title": "AI inference launch A", "url": "https://example.org/a"},
             {**base, "title": "AI inference launch B", "url": "https://example.org/b"}]
    def fetch(url):
        if url.endswith("/a"):
            raise TimeoutError("source timed out")
        return "An LLM inference launch reached production customers with published measurements of throughput and latency."
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        result = prepare_briefing(items, state, "2026-10-03T07:00:00-06:00",
                                  evaluate=lambda item: {"criteria": {"economic_impact": False,
                                         "deployment": True, "competitive_disruption": False,
                                         "source_verifiability": True}, "summary": "Production deployment."},
                                  verify=lambda url: True, fetch_text=fetch)
    assert result["items"][0]["url"] == "https://example.org/b"
    assert result["source_errors"] == 1


def test_pipeline_preserves_peripheral_paper_gate_from_shortlist(tmp_path):
    item = {"kind": "paper", "title": "Nearest-neighbour baselines for fingerprint prediction from MS/MS spectra under different assumptions",
            "url": "https://example.org/spectra", "source": "arXiv",
            "published": "2026-10-05T12:00:00Z",
            "abstract": "A systematic machine learning benchmark for molecular fingerprint prediction with reproducible baselines and careful error analysis."}
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing([item], state, "2026-10-05T07:00:00-06:00",
                                  evaluate=lambda item: {"criteria": {"novelty": True,
                                      "rigor": True, "ecosystem_relevance": True,
                                      "reproducibility": True}, "summary": "Molecular predictions."},
                                  verify=lambda url: True)
    assert report["items"][0]["traffic_light"] == "red"


def test_pipeline_caps_model_classified_application_as_peripheral(tmp_path):
    item = {"kind": "paper", "title": "LLM methods for interpretive structural modeling",
            "url": "https://example.org/ism", "source": "arXiv", "published": "2026-10-05T12:00:00Z",
            "abstract": "The study uses large language models as instruments to automate interpretive structural modeling for management tasks."}
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing([item], state, "2026-10-05T07:00:00-06:00",
                                  evaluate=lambda item: {"criteria": {"novelty": True,
                                      "rigor": True, "ecosystem_relevance": True,
                                      "reproducibility": True}, "summary": "Aplica LLM a ISM.",
                                      "central_ai": False}, verify=lambda url: True)
    assert report["items"][0]["traffic_light"] == "red"


def test_model_keywords_cannot_promote_molecular_relaxation_application(tmp_path):
    item = {"kind": "paper", "title": "Optimizing the Optimizer: Language Models Discover Faster Molecular Relaxation",
            "url": "https://arxiv.org/abs/2610.06577", "source": "Hugging Face Daily Papers",
            "published": "2026-10-05T00:00:00Z",
            "abstract": "Language models and LLMs optimize molecular relaxation with fewer force calls in chemical physics."}
    with DeliveryState(tmp_path / "state.sqlite3") as state:
        report = prepare_briefing([item], state, "2026-10-06T08:37:00-06:00",
                                  evaluate=lambda item: {"criteria": {"novelty": True,
                                      "rigor": True, "ecosystem_relevance": True,
                                      "reproducibility": True}, "summary": "A domain-specific optimizer.",
                                      "central_ai": True}, verify=lambda url: True,
                                  paper_date_lookup=lambda url: item["published"])
    assert report["items"][0]["topic_priority"] == "peripheral"
    assert report["items"][0]["traffic_light"] == "red"
