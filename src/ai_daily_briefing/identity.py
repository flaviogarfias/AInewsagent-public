"""Stable identities for URLs; do not assume a page is reachable here."""

from __future__ import annotations

import re
import ipaddress
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_ARXIV = re.compile(r"^/(?:abs|pdf)/((?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]+)?/\d{7}))(?:v\d+)?(?:\.pdf)?$", re.I)
_TRACKING = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def canonical_url(url: str) -> str:
    """Remove delivery aliases and tracking; reject non-public HTTP URLs."""
    parsed = urlsplit(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() not in {"http", "https"} or not host or parsed.username or parsed.password:
        raise ValueError("invalid public URL")
    if ("." not in host or host.endswith((".local", ".localhost", ".internal", ".test")) or
            not any(char.isalpha() for char in host) or parsed.port not in (None, 80, 443)):
        raise ValueError("private or nonstandard destination")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP literals are not permitted as source URLs")
    if host == "arxiv.org" or host == "www.arxiv.org":
        match = _ARXIV.match(parsed.path)
        if match:
            return "https://arxiv.org/abs/" + match.group(1)
    query = urlencode([(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                       if not k.lower().startswith("utm_") and k.lower() not in _TRACKING])
    port = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
    return urlunsplit((parsed.scheme.lower(), host + port, parsed.path.rstrip("/") or "/", query, ""))


def unique_candidates(items: list[dict]) -> list[dict]:
    """Return first occurrence per canonical link without changing inputs."""
    seen: set[str] = set()
    result = []
    for item in items:
        try:
            url = canonical_url(str(item.get("url", "")))
        except ValueError:
            continue
        if url in seen:
            continue
        seen.add(url)
        result.append({**item, "url": url})
    return result
