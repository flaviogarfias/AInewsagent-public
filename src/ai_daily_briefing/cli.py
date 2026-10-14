"""Read-only collector CLI: no emails, paid APIs, or schedule activation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .configuration import validate_configuration
from .hf_papers import fetch_daily_papers
from .hacker_news import fetch_stories
from .identity import unique_candidates
from .sources import collect_feeds
from .semantic_scholar import enrich_papers
from .tavily import search_news


def collect_configured(config: dict, hf=fetch_daily_papers, feeds=collect_feeds,
                       hn=fetch_stories, semantic=enrich_papers, tavily=search_news,
                       semantic_key: str | None = None, tavily_key: str | None = None) -> list[dict]:
    """Collect configured free/public sources only, with explicit call bounds."""
    options = config.get("sources", {})
    key = semantic_key if semantic_key is not None else os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    if options.get("semantic_scholar") and not key:
        raise ValueError("SEMANTIC_SCHOLAR_API_KEY required when Semantic Scholar is enabled")
    news_key = tavily_key if tavily_key is not None else os.environ.get("TAVILY_API_KEY", "")
    if options.get("tavily_enabled") and not news_key:
        raise ValueError("TAVILY_API_KEY required when Tavily is enabled")
    candidates = []
    if options.get("huggingface", False):
        candidates.extend(hf(options.get("hf_limit", 20)))
    candidates.extend(feeds(config.get("feeds", []), max_per_feed=options.get("max_per_feed", 20)))
    if options.get("hacker_news", False):
        candidates.extend(hn(options.get("hn_queries", []), max_calls=options.get("hn_max_calls", 2)))
    if options.get("tavily_enabled", False):
        candidates.extend(tavily(options["tavily_queries"], news_key,
                                 max_calls=options.get("tavily_max_calls", 2)))
    candidates = unique_candidates(candidates)
    if options.get("semantic_scholar"):
        candidates = semantic(candidates, key, max_calls=options.get("semantic_max_calls", 5))
    return candidates


def collect_configured_diagnostics(config: dict, hf=fetch_daily_papers, feeds=collect_feeds,
                                   hn=fetch_stories, semantic=enrich_papers, tavily=search_news,
                                   semantic_key: str | None = None, tavily_key: str | None = None) -> dict:
    """Isolate public-source outages, retaining results and safe per-source counts."""
    options = config.get("sources", {})
    key = semantic_key if semantic_key is not None else os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    if options.get("semantic_scholar") and not key:
        raise ValueError("SEMANTIC_SCHOLAR_API_KEY required when Semantic Scholar is enabled")
    news_key = tavily_key if tavily_key is not None else os.environ.get("TAVILY_API_KEY", "")
    if options.get("tavily_enabled") and not news_key:
        raise ValueError("TAVILY_API_KEY required when Tavily is enabled")
    candidates: list[dict] = []
    counts: dict[str, int] = {}
    failures: list[str] = []

    def collect_one(name: str, callback) -> None:
        try:
            items = callback()
        except (OSError, ValueError):
            failures.append(name)
            counts[name] = 0
        else:
            candidates.extend(items)
            counts[name] = len(items)

    if options.get("huggingface", False):
        collect_one("Hugging Face Daily Papers", lambda: hf(options.get("hf_limit", 20)))
    for feed in config.get("feeds", []):
        collect_one(feed["name"], lambda feed=feed: feeds([feed], max_per_feed=options.get("max_per_feed", 20)))
    if options.get("hacker_news", False):
        collect_one("Hacker News discovery", lambda: hn(options.get("hn_queries", []),
                                                          max_calls=options.get("hn_max_calls", 2)))
    if options.get("tavily_enabled", False):
        collect_one("Tavily discovery", lambda: tavily(options["tavily_queries"], news_key,
                                                       max_calls=options.get("tavily_max_calls", 2)))
    candidates = unique_candidates(candidates)
    if options.get("semantic_scholar"):
        try:
            candidates = semantic(candidates, key, max_calls=options.get("semantic_max_calls", 5))
        except (OSError, ValueError):
            failures.append("Semantic Scholar")
    return {"candidates": candidates, "source_errors": len(failures),
            "failed_sources": failures, "source_counts": counts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect public AI briefing candidates without sending")
    parser.add_argument("config", type=Path)
    parser.add_argument("--collect", action="store_true", help="live public source collection only")
    parser.add_argument("--dry-run", action="store_true", help="prepare an audited HTML/PDF without sending")
    parser.add_argument("--workdir", type=Path, default=Path("var"))
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    errors = validate_configuration(config)
    if errors:
        parser.error("; ".join(errors))
    if args.dry_run:
        from . import runtime
        result = runtime.run_configured_dry_run(config, args.workdir)
        print(json.dumps({"run_id": result["run_id"], "status": result["status"],
                          "selected": len(result["items"]),
                          "artifacts": {name: str(path) for name, path in result["artifacts"].items()}},
                         ensure_ascii=False, indent=2))
    elif args.collect:
        candidates = collect_configured(config)
        print(json.dumps({"count": len(candidates), "candidates": candidates}, ensure_ascii=False, indent=2))
    else:
        print("Configuración válida; use --collect para consultar fuentes públicas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
