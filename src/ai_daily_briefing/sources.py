"""Public RSS/Atom collection; feed metadata is not proof a source page was read."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable

from .identity import unique_candidates
from .http_public import public_get


def fetch_feed(url: str) -> bytes:
    content, _ = public_get(url, limit=2_000_000)
    return content


def _text(node: ET.Element, tag: str) -> str:
    found = node.find(tag)
    return "".join(found.itertext()).strip() if found is not None else ""


def _clean(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", value)).strip()


def parse_feed(data: bytes, kind: str, source: str) -> list[dict]:
    """Parse RSS 2 or Atom into a common candidate shape."""
    root = ET.fromstring(data)
    atom = "{http://www.w3.org/2005/Atom}"
    entries = root.findall(f"{atom}entry") if root.tag == f"{atom}feed" else root.findall("./channel/item")
    results = []
    for entry in entries:
        if root.tag == f"{atom}feed":
            link = next((n.get("href", "") for n in entry.findall(f"{atom}link") if n.get("rel", "alternate") == "alternate"), "")
            url = link or _text(entry, f"{atom}id")
            title = _text(entry, f"{atom}title")
            summary = _text(entry, f"{atom}summary")
            published = _text(entry, f"{atom}published") or _text(entry, f"{atom}updated")
        else:
            url = _text(entry, "link") or _text(entry, "guid")
            title = _text(entry, "title")
            summary = _text(entry, "description")
            published = _text(entry, "pubDate")
        if title and url:
            results.append({"kind": kind, "source": source, "title": _clean(title),
                            "url": url, "abstract": _clean(summary), "published": published,
                            "evidence_level": "feed-metadata"})
    return unique_candidates(results)


def collect_feeds(feeds: list[dict], fetch: Callable[[str], bytes] = fetch_feed,
                  max_per_feed: int = 20) -> list[dict]:
    """Collect bounded public feeds; fail loudly rather than silently dropping a source."""
    if max_per_feed < 1:
        raise ValueError("max_per_feed must be positive")
    items = []
    for feed in feeds:
        items.extend(parse_feed(fetch(feed["url"]), feed["kind"], feed["name"])[:max_per_feed])
    return unique_candidates(items)
