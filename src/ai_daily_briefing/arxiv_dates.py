"""Original arXiv submission date, distinct from an RSS discovery date."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime

from .http_public import public_get

_ARXIV_ID = r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]+)?/\d{7})"
_ARXIV_ABS = re.compile(r"^https://arxiv\.org/abs/(" + _ARXIV_ID + r")$", re.I)
_ARXIV_ENTRY_ID = re.compile(r"https?://(?:www\.)?arxiv\.org/abs/(" + _ARXIV_ID + r")(?:v\d+)?", re.I)
_ATOM = "{http://www.w3.org/2005/Atom}"


def original_arxiv_date(url: str, fetch=public_get) -> str | None:
    """Return the matching Atom `published` value; None for other publishers."""
    match = _ARXIV_ABS.fullmatch(url)
    if not match:
        return None
    identifier = match.group(1)
    data, _ = fetch(f"https://export.arxiv.org/api/query?id_list={identifier}", limit=200_000)
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError("invalid arxiv metadata") from error
    entries = root.findall(f"{_ATOM}entry")
    if len(entries) != 1:
        raise ValueError("arxiv metadata mismatch")
    entry = entries[0]
    source_id = entry.findtext(f"{_ATOM}id", "")
    source_match = _ARXIV_ENTRY_ID.fullmatch(source_id)
    if not source_match or source_match.group(1) != identifier:
        raise ValueError("arxiv metadata mismatch")
    published = entry.findtext(f"{_ATOM}published", "")
    try:
        date = datetime.fromisoformat(published.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("arxiv original date missing") from error
    if date.tzinfo is None:
        raise ValueError("arxiv original date missing")
    return published


def original_arxiv_dates(urls: list[str], fetch=public_get) -> dict[str, str]:
    """Fetch all submitted dates in one bounded Atom query; reject partial replies."""
    if not urls:
        return {}
    matches = [_ARXIV_ABS.fullmatch(url) for url in urls]
    if any(match is None for match in matches):
        raise ValueError("invalid arxiv batch")
    all_ids = [match.group(1) for match in matches if match is not None]
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("duplicate arxiv batch ID")
    all_dates = {}
    for start in range(0, len(all_ids), 100):
        ids = all_ids[start:start + 100]
        data, _ = fetch("https://export.arxiv.org/api/query?id_list=" + ",".join(ids) +
                        f"&max_results={len(ids)}", limit=2_000_000)
        try:
            root = ET.fromstring(data)
        except ET.ParseError as error:
            raise ValueError("invalid arxiv metadata") from error
        dates = {}
        for entry in root.findall(f"{_ATOM}entry"):
            source_id = entry.findtext(f"{_ATOM}id", "")
            match = _ARXIV_ENTRY_ID.fullmatch(source_id)
            if not match or match.group(1) not in ids or match.group(1) in dates:
                raise ValueError("arxiv metadata mismatch")
            published = entry.findtext(f"{_ATOM}published", "")
            try:
                date = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError("arxiv original date missing") from error
            if date.tzinfo is None:
                raise ValueError("arxiv original date missing")
            dates[match.group(1)] = published
        if set(dates) != set(ids):
            raise ValueError("arxiv metadata mismatch")
        all_dates.update(dates)
    return {url: all_dates[identifier] for url, identifier in zip(urls, all_ids)}
