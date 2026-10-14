"""Conservative topical prefilter; not a substitute for expert relevance review."""

from __future__ import annotations

import re

_TERMS = re.compile(r"\b(?:artificial intelligence|machine learning|deep learning|language model|"
                    r"large language model|llm|llms|multi.agent|ai agent|agentic|transformer|"
                    r"inference|foundation model|neural network|generative ai|federated learning)\b", re.I)


_APPLICATION = re.compile(r"\b(?:lego|recipe|wallpaper|avatar|coloring book|"
                          r"raman spectroscopy|molecular relaxation|pharmaceutical identification|drug.response|"
                          r"greenwashing|market discipline)\b", re.I)


def topic_priority(title: str, abstract: str) -> str:
    """AI applied to a narrow consumer hobby is peripheral despite tool keywords."""
    if _APPLICATION.search(title):
        return "peripheral"
    return "core" if _TERMS.search(title + " " + abstract) else "peripheral"


def has_enough_evidence(item: dict) -> bool:
    """A category label or a feed teaser is not enough for a summary."""
    abstract = str(item.get("abstract", "")).strip()
    return len(abstract) >= 80 and (item.get("kind") != "news" or
                                    not abstract.endswith(("...", "…")))
