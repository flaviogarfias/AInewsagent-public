"""Deterministic scoring for curated briefing candidates."""

from __future__ import annotations


GREEN = "green"
YELLOW = "yellow"
RED = "red"


def score_candidate(candidate: dict) -> tuple[int, str]:
    """Return the count of satisfied criteria and its traffic-light label."""
    names = {
        "paper": ("novelty", "rigor", "ecosystem_relevance", "reproducibility"),
        "news": ("economic_impact", "deployment", "competitive_disruption", "source_verifiability"),
    }
    kind = candidate.get("kind")
    if kind not in names:
        raise ValueError("unknown candidate kind")
    criteria = candidate.get("criteria", {})
    if any(type(criteria.get(name)) is not bool for name in names[kind]):
        raise ValueError("all four rubric criteria must be booleans")
    score = sum(criteria[name] for name in names[kind])
    if candidate.get("topic_priority") == "peripheral":
        return score, RED
    if (score >= 4 and candidate.get("source_verified") is True and
            (kind != "paper" or candidate.get("code_link_verified") is True)):
        return score, GREEN
    if score >= 2:
        return score, YELLOW
    return score, RED
