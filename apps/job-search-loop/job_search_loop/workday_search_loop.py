from __future__ import annotations

import argparse
import json
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .agent_runner import AgentRunner, wrap_untrusted
from .ledger import Ledger
from .state import canonical_url, is_excluded_employer
from .workday_discovery import _fetch_jobs, discover_one
from .workday_qualification import fetch_official_description, qualify_one


def rotated_sources(
    sources: tuple[dict[str, str], ...], index: int
) -> tuple[dict[str, str], ...]:
    if not sources:
        return ()
    offset = index % len(sources)
    return sources[offset:] + sources[:offset]


def unique_sources(
    sources: tuple[dict[str, str], ...],
) -> tuple[dict[str, str], ...]:
    unique = []
    seen = set()
    for source in sources:
        key = (source["host"].casefold(), source["tenant"], source["site"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return tuple(unique)


def cached_source_fetcher(
    fetch: Callable[[dict[str, str]], list[dict[str, Any]]],
    cache: dict[str, list[dict[str, Any]]] | None = None,
) -> Callable[[dict[str, str]], list[dict[str, Any]]]:
    values = cache if cache is not None else {}

    def cached(source: dict[str, str]) -> list[dict[str, Any]]:
        key = json.dumps(source, ensure_ascii=False, sort_keys=True)
        if key not in values:
            values[key] = fetch(source)
        return values[key]

    return cached


def snapshot_candidates(
    *,
    ledger_path: Path,
    sources: tuple[dict[str, str], ...],
    fetch_jobs: Callable[[dict[str, str]], list[dict[str, Any]]],
) -> list[dict[str, str]]:
    ledger = Ledger(ledger_path)
    try:
        seen = {
            canonical_url(str(row[0])).casefold()
            for row in ledger.connection.execute("SELECT canonical_url FROM applications")
        }
    finally:
        ledger.close()
    candidates = []
    for source in sources:
        if is_excluded_employer(source["company"]):
            continue
        try:
            jobs = fetch_jobs(source)
        except Exception:
            continue
        for job in jobs:
            title = " ".join(str(job.get("title") or "").split())
            location = " ".join(str(job.get("locationsText") or "").split())
            path = str(job.get("externalPath") or "")
            if not title or not path.startswith("/job/"):
                continue
            url = canonical_url(f"https://{source['host']}/{source['site']}{path}")
            if url.casefold() in seen:
                continue
            candidates.append(
                {
                    "company": source["company"],
                    "title": title,
                    "location": location,
                    "url": url,
                }
            )
    return candidates


def validate_shortlist(
    result: dict[str, Any], candidates: list[dict[str, str]]
) -> tuple[str, ...]:
    ranked_ids = result.get("ranked_candidate_ids")
    if not isinstance(ranked_ids, list) or not ranked_ids:
        raise ValueError("Workday shortlist must contain ranked_candidate_ids")
    allowed = {row["candidate_id"]: row["url"] for row in candidates}
    validated = []
    for value in ranked_ids:
        if not isinstance(value, str) or value not in allowed:
            continue
        url = allowed[value]
        if url not in validated:
            validated.append(url)
    if not validated:
        raise ValueError("Workday shortlist contains no official candidate ID")
    return tuple(validated)


def rank_candidates(
    *,
    candidates: list[dict[str, str]],
    rank_chunk: Callable[[list[dict[str, str]]], dict[str, Any]],
    chunk_size: int = 400,
) -> tuple[str, ...]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    identified = [
        {**row, "candidate_id": f"candidate-{index:06d}"}
        for index, row in enumerate(candidates)
    ]
    finalists: list[dict[str, str]] = []
    by_url = {row["url"].casefold(): row for row in identified}
    for offset in range(0, len(identified), chunk_size):
        chunk = identified[offset : offset + chunk_size]
        for url in validate_shortlist(rank_chunk(chunk), chunk):
            row = by_url[url.casefold()]
            if row not in finalists:
                finalists.append(row)
    if len(finalists) <= 8:
        return tuple(row["url"] for row in finalists)
    return validate_shortlist(rank_chunk(finalists), finalists)


def search_until_qualified(
    *,
    discover: Callable[[], dict[str, Any]],
    qualify: Callable[[], dict[str, Any]],
    max_candidates: int,
) -> dict[str, Any]:
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    discoveries = []
    decisions = []
    for _ in range(max_candidates):
        discovery = discover()
        discoveries.append(discovery)
        if discovery.get("status") == "no_fresh_workday":
            return {
                "status": "sources_exhausted",
                "discoveries": discoveries,
                "decisions": decisions,
            }
        decision = qualify()
        decisions.append(decision)
        if decision.get("decision") == "qualified":
            return {
                "status": "qualified",
                "discoveries": discoveries,
                "decisions": decisions,
            }
        if decision.get("status") == "no_pending_workday_fit":
            return {
                "status": "sources_exhausted",
                "discoveries": discoveries,
                "decisions": decisions,
            }
    return {
        "status": "budget_exhausted",
        "discoveries": discoveries,
        "decisions": decisions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--candidate-memory", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--shortlist-schema", required=True, type=Path)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--max-candidates", type=int, default=8)
    args = parser.parse_args()
    runner = AgentRunner(evidence_root=args.evidence_root, runner_path=args.runner)
    source_payload = json.loads(args.sources.read_text(encoding="utf-8"))
    sources = unique_sources(
        tuple(dict(row) for row in source_payload.get("sources", []))
    )
    allowed_hosts = {str(row["host"]).casefold() for row in sources}
    source_cursor = 0
    jobs_by_source: dict[str, list[dict[str, Any]]] = {}
    fetch_jobs = cached_source_fetcher(_fetch_jobs, jobs_by_source)
    candidates = snapshot_candidates(
        ledger_path=args.ledger,
        sources=sources,
        fetch_jobs=fetch_jobs,
    )
    snapshot = {
        "version": 1,
        "sources": [
            {"source": json.loads(key), "jobs": jobs}
            for key, jobs in jobs_by_source.items()
        ],
    }
    args.snapshot.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.snapshot.write_text(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(args.snapshot, 0o600)
    preferred_urls: tuple[str, ...] = ()
    if candidates:
        candidate_memory = args.candidate_memory.read_text(encoding="utf-8")
        def rank_chunk(chunk: list[dict[str, str]]) -> dict[str, Any]:
            return runner.run(
                task="improve",
                prompt=(
                "Rank the Workday jobs for this candidate's realistic chance of winning "
                "an interview and reaching at least JPY 7M, prioritizing JPY 10M-30M. "
                "Use the whole supplied snapshot, not company prestige or source order. "
                "Prefer roles whose actual work is supported by demonstrated experience. "
                "Do not invent requirements, compensation, or candidate facts. Return up "
                "to 8 unique candidate_id values, best first, copied exactly from the snapshot. "
                "Return only the schema.\n\n"
                + wrap_untrusted(
                    "workday_snapshot",
                    json.dumps(chunk, ensure_ascii=False),
                )
                + "\n\n"
                + wrap_untrusted("candidate_memory", candidate_memory)
            ),
                schema_path=args.shortlist_schema,
                workdir=args.workdir,
                run_id=f"workday-shortlist-{uuid.uuid4().hex}",
            )

        preferred_urls = rank_candidates(
            candidates=candidates,
            rank_chunk=rank_chunk,
        )

    def discover_next() -> dict[str, Any]:
        nonlocal source_cursor
        ordered = rotated_sources(sources, source_cursor)
        source_cursor += 1
        return discover_one(
            ledger_path=args.ledger,
            sources=ordered,
            fetch_jobs=fetch_jobs,
            preferred_urls=preferred_urls,
        )

    result = search_until_qualified(
        discover=discover_next,
        qualify=lambda: qualify_one(
            ledger_path=args.ledger,
            candidate_memory_path=args.candidate_memory,
            fetch_description=lambda url: fetch_official_description(url, sources),
            run_model=lambda prompt: runner.run(
                task="improve",
                prompt=prompt,
                schema_path=args.schema,
                workdir=args.workdir,
                run_id=f"workday-fit-{uuid.uuid4().hex}",
            ),
            allowed_hosts=allowed_hosts,
        ),
        max_candidates=args.max_candidates,
    )
    result["discovered"] = [
        row
        for discovery in result["discoveries"]
        for row in discovery.get("discovered", [])
    ]
    result["shortlist"] = list(preferred_urls)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(args.output, 0o600)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
