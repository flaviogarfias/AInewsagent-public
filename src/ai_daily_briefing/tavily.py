"""Bounded Tavily news discovery; snippets never count as read articles."""
from __future__ import annotations

import json
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .identity import unique_candidates

ENDPOINT = "https://api.tavily.com/search"


def search_news(queries: list[str], key: str, max_calls: int = 2,
                opener: Callable = urlopen) -> list[dict]:
    """Use at most max_calls basic searches (one credit each); do not log secrets."""
    if not key or "=" in key or key != key.strip():
        raise ValueError("TAVILY_API_KEY must be a bare nonempty key")
    if not 1 <= max_calls <= 4:
        raise ValueError("Tavily max_calls must be 1..4")
    if not queries:
        return []
    usage_request = Request("https://api.tavily.com/usage",
                            headers={"Authorization": f"Bearer {key}"})
    try:
        with opener(usage_request, timeout=15) as response:
            usage = json.loads(response.read(2_000_001))
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        raise OSError(f"Tavily usage preflight failed ({type(error).__name__})") from None
    account = usage.get("account") if isinstance(usage, dict) else None
    if not isinstance(account, dict) or account.get("current_plan") != "Researcher":
        raise ValueError("Tavily requires Researcher free plan")
    used, limit, paygo = (account.get("plan_usage"), account.get("plan_limit"),
                          account.get("paygo_usage"))
    if (type(used) is not int or type(limit) is not int or type(paygo) is not int or
            used < 0 or limit <= 0 or paygo != 0 or used + min(max_calls, len(queries)) + 5 > limit):
        raise ValueError("Tavily free credits insufficient or usage unknown")
    items = []
    for query in queries[:max_calls]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Tavily query must be nonempty")
        body = json.dumps({"query": query, "search_depth": "basic", "topic": "news",
                           "time_range": "week", "max_results": 8, "include_answer": False,
                           "include_raw_content": False}).encode()
        request = Request(ENDPOINT, data=body, method="POST",
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with opener(request, timeout=15) as response:
                data = json.loads(response.read(2_000_001))
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            raise OSError(f"Tavily search failed ({type(error).__name__})") from None
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise OSError("Tavily response missing results")
        for hit in data["results"][:8]:
            if isinstance(hit, dict) and hit.get("title") and hit.get("url"):
                items.append({"kind": "news", "source": "Tavily discovery", "title": hit["title"],
                              "url": hit["url"], "abstract": hit.get("content") or "",
                              "published": hit.get("published_date") or "",
                              "evidence_level": "search-snippet"})
    return unique_candidates(items)
