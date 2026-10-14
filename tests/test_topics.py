from ai_daily_briefing.topics import topic_priority, has_enough_evidence


def test_peripheral_domain_paper_is_not_promoted_as_core_ai():
    assert topic_priority("Reverse Item Response Theory for Cancer Drug-Response Matrices", "Pharmacogenomic analysis") == "peripheral"
    assert topic_priority("Hybrid Machine Learning-Assisted Raman Spectroscopy with Generative Feature Augmentation for Pharmaceutical Identification", "Machine learning improves identification precision using Raman spectra.") == "peripheral"
    assert topic_priority("The Price of Greenwashing: Algorithmic Verification and Market Discipline using Conformal Machine Learning", "Machine learning measures corporate greenwashing with market data.") == "peripheral"
    assert topic_priority("New multi-agent LLM inference system", "Large language model serving") == "core"


def test_molecular_relaxation_application_does_not_become_core_from_model_keywords():
    title = "Optimizing the Optimizer: Language Models Discover Faster Molecular Relaxation"
    abstract = "Language models and LLMs optimize molecular geometries and reduce expensive force calculations."
    assert topic_priority(title, abstract) == "peripheral"
    assert topic_priority("Language models improve general-purpose inference optimizers",
                          "Benchmarks across model families and inference engines") == "core"


def test_niche_consumer_agent_demo_remains_peripheral_even_if_abstract_mentions_agents():
    title = "Show HN: Made an open-source Lego AI generator"
    abstract = "Agent tooling for generative LEGO models building, using an LLM to generate step-by-step instructions."
    assert topic_priority(title, abstract) == "peripheral"
    assert topic_priority("LLM inference engine for agents", "Benchmarks on deployed models") == "core"


def test_long_feed_teaser_ending_in_ellipsis_is_not_sufficient_evidence():
    teaser = ("Enterprise applications have become increasingly demanding. Agentic AI "
              "has compounded the need for vast amounts of enterprise data with frequent, complex...")
    assert len(teaser) >= 80
    assert not has_enough_evidence({"kind": "news", "abstract": teaser})
    assert not has_enough_evidence({"kind": "news", "abstract": teaser[:-3] + "…"})


def test_substantive_paper_abstract_ending_in_ellipsis_is_not_discarded():
    abstract = ("We benchmark multiple language model inference systems against established "
                "baselines with detailed latency measurements and reproducible comparisons...")
    assert has_enough_evidence({"kind": "paper", "abstract": abstract})


def test_short_feed_category_is_not_sufficient_evidence_to_summarize():
    assert not has_enough_evidence({"abstract": "Mobile Systems"})
    assert has_enough_evidence({"abstract": "A detailed empirical evaluation of a language model against recognized baselines with quantitative experimental results."})
