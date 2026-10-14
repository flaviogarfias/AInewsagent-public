from ai_daily_briefing.scoring import score_candidate


def test_scoring_marks_all_priority_criteria_as_green():
    candidate = {
        "kind": "paper", "source_verified": True, "code_link_verified": True,
        "criteria": {
            "novelty": True,
            "rigor": True,
            "ecosystem_relevance": True,
            "reproducibility": True,
        }
    }

    assert score_candidate(candidate) == (4, "green")


def test_unverified_source_cannot_be_green_and_peripheral_is_red():
    paper = {"kind": "paper", "criteria": {"novelty": True, "rigor": True,
             "ecosystem_relevance": True, "reproducibility": True}, "source_verified": False}
    peripheral = {"kind": "news", "topic_priority": "peripheral", "source_verified": True,
                  "criteria": {"economic_impact": True, "deployment": True,
                               "competitive_disruption": True, "source_verifiability": True}}
    assert score_candidate(paper)[1] != "green"
    assert score_candidate(peripheral)[1] == "red"


def test_paper_cannot_be_green_from_abstract_claim_of_reproducibility_alone():
    paper = {"kind": "paper", "source_verified": True,
             "criteria": {"novelty": True, "rigor": True,
                          "ecosystem_relevance": True, "reproducibility": True}}
    assert score_candidate(paper) == (4, "yellow")
