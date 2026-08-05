from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

from .discovery import _default_providers, search_jobs
from .dedup import fingerprint_text
from .knockout import assess_candidate, shortlist_candidates
from .state import canonical_url


JAPAN_RE = re.compile(r"\b(?:japan|tokyo)\b|日本|東京", re.IGNORECASE)
AI_RE = re.compile(r"\b(?:AI|LLM|GenAI|machine learning)\b|生成AI", re.IGNORECASE)


def _excerpt(text: Any, pattern: re.Pattern[str], limit: int = 240) -> str | None:
    if not isinstance(text, str):
        return None
    match = pattern.search(text)
    if match is None:
        return None
    start = max(0, match.start() - 80)
    return text[start : start + limit].strip() or None


def build_prefilter_result(
    plan: dict[str, Any], *, search: Callable[[str], dict[str, Any]]
) -> dict[str, Any]:
    queries = plan.get("queries")
    if not isinstance(queries, list):
        raise ValueError("recovery plan requires queries")
    candidates_by_url: dict[str, dict[str, Any]] = {}
    provider_results: list[dict[str, Any]] = []
    for query_item in queries:
        if not isinstance(query_item, dict):
            continue
        query = str(query_item.get("query", "")).strip()
        if not query:
            continue
        try:
            discovery = search(query)
        except Exception as exc:
            provider_results.append(
                {
                    "provider": "multi_source",
                    "query": query,
                    "status": "failed",
                    "result_count": 0,
                    "error": str(exc)[-500:],
                }
            )
            continue
        providers = discovery.get("providers")
        if isinstance(providers, list):
            for provider in providers:
                if not isinstance(provider, dict):
                    continue
                provider_results.append(
                    {
                        "provider": str(provider.get("name", "unknown")),
                        "query": query,
                        "status": str(provider.get("status", "unknown")),
                        "result_count": int(provider.get("count", 0) or 0),
                        "error": (
                            str(provider["error"])[-500:]
                            if provider.get("error") is not None
                            else None
                        ),
                    }
                )
        rows = discovery.get("results")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            url = str(row.get("canonical_url") or row.get("url") or "").strip()
            title = str(row.get("title") or "").strip()
            company = str(row.get("company") or "").strip()
            if not url or not title or not company:
                continue
            normalized_url = canonical_url(url)
            if normalized_url in candidates_by_url:
                continue
            location = str(row.get("location") or "").strip() or None
            description = row.get("description")
            candidate = {
                "bucket": query_item.get("bucket"),
                "language": query_item.get("language"),
                "provider": row.get("discovery_provider"),
                "official_url": normalized_url,
                "title": title,
                "company": company,
                "location": location,
                "ai_requirement_evidence": _excerpt(description, AI_RE),
                "japan_eligibility_evidence": (
                    location if location and JAPAN_RE.search(location) else None
                ),
                "compensation_evidence": None,
                "deadline_evidence": None,
                "jd_fingerprint": fingerprint_text(description),
            }
            candidate.update(
                assess_candidate(
                    {
                        **candidate,
                        "url": normalized_url,
                        "description": description,
                    }
                )
            )
            candidates_by_url[normalized_url] = candidate
    candidates = list(candidates_by_url.values())
    return {
        "status": "usable" if candidates else "browser_fallback_required",
        "candidates": candidates,
        "provider_results": provider_results,
        "blocked": [],
    }


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--queue-output", type=Path)
    parser.add_argument("--framework-root", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.recovery_plan.read_text(encoding="utf-8"))
    app_root = Path(__file__).resolve().parents[1]

    def search(query: str) -> dict[str, Any]:
        return search_jobs(
            query,
            providers=_default_providers(
                query,
                app_root=app_root,
                framework_root=args.framework_root.expanduser().resolve(),
            ),
        )

    queue_result = build_prefilter_result(plan, search=search)
    result = {
        **queue_result,
        "candidates": shortlist_candidates(queue_result["candidates"], limit=12),
    }
    if args.queue_output is not None:
        _write_private_json(args.queue_output, queue_result)
    _write_private_json(args.output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "candidate_count": len(result["candidates"]),
                "queue_candidate_count": len(queue_result["candidates"]),
                "provider_result_count": len(result["provider_results"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
