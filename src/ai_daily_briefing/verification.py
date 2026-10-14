"""Lightweight reachability check, not a content fact-check."""

from __future__ import annotations

from urllib.request import Request

from .identity import canonical_url
from .http_public import public_get


def verify_source(url: str, opener=None) -> bool:
    """Check accessible non-empty HTTP content on the original host."""
    try:
        original = canonical_url(url)
        if opener is None:
            public_get(original, limit=1_000_000)
            return True
        request = Request(original, headers={"User-Agent": "Mozilla/5.0 (AI briefing verifier)"})
        with opener(request, timeout=15) as response:
            final = canonical_url(response.geturl())
            if final.split("/", 3)[2] != original.split("/", 3)[2]:
                return False
            return response.status == 200 and bool(response.read(256))
    except (ValueError, OSError, AttributeError):
        return False
