from __future__ import annotations

import argparse
import json
import os
import uuid
from collections import Counter, deque
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .agent_runner import AgentRunner, wrap_untrusted
from .application_reporting import deliver_fit_decision
from .ledger import Ledger
from .state import canonical_url, is_excluded_employer
from .workday_discovery import _fetch_jobs, discover_one
from .workday_qualification import fetch_official_description, qualify_one

SHORTLIST_SIZE = 24


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


def qualified_queue_ids(
    ledger_path: Path, allowed_hosts: set[str]
) -> tuple[str, ...]:
    ledger = Ledger(ledger_path)
    try:
        return tuple(
            str(row["application_id"])
            for row in ledger.pending_materials_ready_applications()
            if (urlsplit(str(row["canonical_url"])).hostname or "").casefold()
            in allowed_hosts
            and ledger.workday_fit_qualified(str(row["application_id"]))
        )
    finally:
        ledger.close()


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
    exclusions: frozenset[str] = frozenset(),
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
        if is_excluded_employer(source["company"], exclusions):
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


def interleave_companies(
    candidates: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Keep each ranking window company-diverse without deciding candidate fit."""
    buckets: dict[str, deque[dict[str, str]]] = {}
    order: list[str] = []
    for row in candidates:
        key = str(
            row.get("company")
            or urlsplit(str(row.get("url") or "")).hostname
            or "unknown"
        ).strip().casefold()
        if key not in buckets:
            buckets[key] = deque()
            order.append(key)
        buckets[key].append(row)
    result: list[dict[str, str]] = []
    while any(buckets[key] for key in order):
        for key in order:
            if buckets[key]:
                result.append(buckets[key].popleft())
    return result


def submitted_company_portfolio(ledger_path: Path) -> dict[str, int]:
    ledger = Ledger(ledger_path)
    try:
        rows = ledger.connection.execute(
            "SELECT company FROM applications WHERE current_state='submitted'"
        ).fetchall()
    finally:
        ledger.close()
    return dict(Counter(str(row[0]) for row in rows))


def candidate_employer_exclusions(candidate_memory_path: Path) -> frozenset[str]:
    value = json.loads(candidate_memory_path.read_text(encoding="utf-8"))
    for concept in value.get("concepts", []):
        if concept.get("concept") == "candidate.employer_exclusions":
            exclusions = concept.get("value")
            if not isinstance(exclusions, list) or any(
                not isinstance(item, str) or not item.strip() for item in exclusions
            ):
                raise ValueError("candidate employer exclusions are invalid")
            return frozenset(item.strip() for item in exclusions)
    return frozenset()


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
    def select(rows: list[dict[str, str]]) -> tuple[str, ...]:
        presented = [
            {**row, "candidate_id": f"c{index}"}
            for index, row in enumerate(rows)
        ]
        return validate_shortlist(rank_chunk(presented), presented)

    candidates = interleave_companies(candidates)
    finalists: list[dict[str, str]] = []
    by_url = {row["url"].casefold(): row for row in candidates}
    for offset in range(0, len(candidates), chunk_size):
        chunk = candidates[offset : offset + chunk_size]
        for url in select(chunk):
            row = by_url[url.casefold()]
            if row not in finalists:
                finalists.append(row)
    if len(finalists) <= SHORTLIST_SIZE:
        return tuple(row["url"] for row in finalists)
    return select(finalists)


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
        try:
            decision = qualify()
        except Exception as error:
            decisions.append(
                {
                    "status": "qualification_retryable_failure",
                    "error": type(error).__name__,
                }
            )
            continue
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
    employer_exclusions = candidate_employer_exclusions(args.candidate_memory)
    sources = tuple(
        source
        for source in sources
        if not is_excluded_employer(source["company"], employer_exclusions)
    )
    allowed_hosts = {str(row["host"]).casefold() for row in sources}
    queued_ids = qualified_queue_ids(args.ledger, allowed_hosts)
    source_cursor = 0
    jobs_by_source: dict[str, list[dict[str, Any]]] = {}
    fetch_jobs = cached_source_fetcher(_fetch_jobs, jobs_by_source)
    candidates = snapshot_candidates(
        ledger_path=args.ledger,
        sources=sources,
        fetch_jobs=fetch_jobs,
        exclusions=employer_exclusions,
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
        portfolio = submitted_company_portfolio(args.ledger)
        def rank_chunk(chunk: list[dict[str, str]]) -> dict[str, Any]:
            return runner.run(
                task="improve",
                prompt=(
                "Rank the Workday jobs for this candidate's realistic chance of winning "
                "an interview and reaching at least JPY 7M, prioritizing JPY 10M-30M. "
                "Use the whole supplied snapshot, not company prestige or source order. "
                "Prefer roles whose actual work is supported by demonstrated experience. "
                "This is a company-wide portfolio search, not a single-company campaign. "
                "Treat candidate.preferred_employer_types as an eligibility requirement, "
                "not a soft tie-breaker. Rank only foreign-capital companies operating "
                "in Japan or overseas employers that support Japan-based employment, "
                "EOR, or contracting; exclude domestic Japanese employers. "
                "When interview fit is comparable, prefer employers with fewer prior "
                "submitted applications and keep credible finalists across different "
                "companies. Do not repeatedly choose one employer merely because it has "
                "more postings in the snapshot. "
                "Do not invent requirements, compensation, or candidate facts. Return up "
                f"exactly {min(SHORTLIST_SIZE, len(chunk))} unique candidate_id values, "
                "best first, copied exactly from the snapshot. "
                "Return only the schema.\n\n"
                + wrap_untrusted(
                    "workday_snapshot",
                    json.dumps(chunk, ensure_ascii=False),
                )
                + "\n\n"
                + wrap_untrusted("candidate_memory", candidate_memory)
                + "\n\n"
                + wrap_untrusted(
                    "submitted_company_portfolio",
                    json.dumps(portfolio, ensure_ascii=False, sort_keys=True),
                )
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
            prefer_fresh=True,
        )

    def qualify_next() -> dict[str, Any]:
        decision = qualify_one(
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
        )
        if decision.get("status") == "decided":
            try:
                delivery = deliver_fit_decision(
                    decision=decision,
                    outbox_path=args.ledger.parent / "telegram-outbox.sqlite3",
                )
                decision["telegram_message_id"] = delivery.get("message_id")
                decision["telegram_status"] = delivery.get("status")
            except Exception as error:
                decision["telegram_status"] = "failed"
                decision["telegram_error"] = type(error).__name__
        return decision

    result = search_until_qualified(
        discover=discover_next,
        qualify=qualify_next,
        max_candidates=args.max_candidates,
    )
    result["discovered"] = [
        row
        for discovery in result["discoveries"]
        for row in discovery.get("discovered", [])
    ]
    result["shortlist"] = list(preferred_urls)
    newly_qualified = next(
        (
            str(decision["application_id"])
            for decision in reversed(result["decisions"])
            if decision.get("decision") == "qualified"
            and decision.get("application_id")
        ),
        None,
    )
    result["queued_application_ids"] = list(
        dict.fromkeys(([newly_qualified] if newly_qualified else []) + list(queued_ids))
    )
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
