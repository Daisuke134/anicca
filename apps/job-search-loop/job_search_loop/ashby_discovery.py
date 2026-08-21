"""Bounded, deterministic Ashby discovery from the official ATS cache.

The model lane is not the source of truth for a new URL.  This command selects one
currently cached Tokyo/Japan Ashby posting, applies the existing exclusion and
dedupe fences, and creates the immutable attributed Ledger row.  Browser fast path
execution remains a separate step and is the only code allowed to claim/submit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .ledger import Ledger
from .learning import LearningDriver
from .resume_routing import select_resume
from .state import canonical_url, is_excluded_employer


ROLE_RE = re.compile(
    r"ai|agent|machine learning|\bml\b|solutions|technical|customer success|"
    r"product|partnership|sales engineer|forward deployed",
    re.IGNORECASE,
)
JAPAN_RE = re.compile(r"tokyo|japan", re.IGNORECASE)
ASHBY_RE = re.compile(r"https://(?:jobs|app)\.ashbyhq\.com/[^/]+/[^/?#]+", re.IGNORECASE)


def _read_jobs(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    jobs = value.get("jobs") if isinstance(value, dict) else None
    if not isinstance(jobs, list):
        raise ValueError("official ATS cache has no jobs array")
    return [job for job in jobs if isinstance(job, dict)]


def _role_family(title: str) -> str:
    return "technical_business" if re.search(
        r"solutions|customer success|partnership|sales|product", title, re.IGNORECASE
    ) else "applied_ai"


def _board_slug(url: str) -> str:
    parts = urlsplit(url).path.strip("/").split("/")
    return parts[0] if len(parts) >= 2 else ""


def _candidate_jobs(
    jobs: list[dict[str, Any]], seen: set[str], limited_boards: set[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job in jobs:
        company = str(job.get("company") or "").strip()
        title = str(job.get("title") or "").strip()
        url = canonical_url(str(job.get("url") or ""))
        location = " ".join(
            [str(job.get("location") or ""), *[str(x) for x in (job.get("secondary_locations") or [])]]
        )
        if str(job.get("ats") or "").casefold() != "ashby":
            continue
        if job.get("isListed") is False:
            continue
        if not company or not title or not ASHBY_RE.fullmatch(url):
            continue
        if (
            is_excluded_employer(company)
            or url.casefold() in seen
            or _board_slug(url).casefold() in limited_boards
        ):
            continue
        if not (JAPAN_RE.search(location) or job.get("is_remote") is True):
            continue
        if not ROLE_RE.search(title):
            continue
        rows.append({**job, "company": company, "title": title, "url": url})
    rows.sort(key=lambda row: int(row.get("posted_at_ms") or 0), reverse=True)
    return rows


def _japan_board_slugs(jobs: list[dict[str, Any]]) -> dict[str, str]:
    boards: dict[str, str] = {}
    for job in jobs:
        if str(job.get("ats") or "").casefold() != "ashby":
            continue
        location = " ".join(
            [str(job.get("location") or ""), *[str(x) for x in (job.get("secondary_locations") or [])]]
        )
        if not JAPAN_RE.search(location):
            continue
        path = urlsplit(str(job.get("url") or "")).path.strip("/").split("/")
        if len(path) < 2 or not path[0]:
            continue
        boards.setdefault(path[0], str(job.get("company") or path[0]))
    return boards


def _posted_at_ms(value: Any) -> int:
    if not isinstance(value, str):
        return 0
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return 0


def _live_board_jobs(slug: str, company: str) -> list[dict[str, Any]]:
    request = Request(
        f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true",
        headers={"User-Agent": "Mozilla/5.0 job-search-loop/1.0", "Accept": "application/json"},
    )
    with urlopen(request, timeout=15) as response:
        value = json.load(response)
    source = value.get("jobs") if isinstance(value, dict) else None
    if not isinstance(source, list):
        return []
    rows: list[dict[str, Any]] = []
    for job in source:
        if not isinstance(job, dict):
            continue
        rows.append(
            {
                "ats": "ashby",
                "company": company,
                "title": job.get("title"),
                "url": job.get("jobUrl"),
                "location": job.get("location"),
                "secondary_locations": job.get("secondaryLocations") or [],
                "is_remote": job.get("isRemote") is True,
                "isListed": job.get("isListed"),
                "description": job.get("descriptionPlain") or "",
                "posted_at_ms": _posted_at_ms(job.get("publishedAt")),
            }
        )
    return rows


def _fresh_jobs(cached_jobs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for slug, company in sorted(_japan_board_slugs(cached_jobs).items()):
        try:
            rows.extend(_live_board_jobs(slug, company))
        except Exception as error:
            errors.append(f"{slug}:{type(error).__name__}")
    return rows, errors


def discover_one(
    *,
    cache_path: Path,
    ledger_path: Path,
    profile_path: Path,
    materials_root: Path,
    prompt_path: Path,
    max_jobs: int = 1,
) -> dict[str, Any]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    ledger = Ledger(ledger_path)
    try:
        exclusions = profile.get("candidate", {}).get("employer_exclusions", [])
        ledger.reject_excluded_employers(
            frozenset(str(value) for value in exclusions)
            if isinstance(exclusions, list)
            else None
        )
        seen = {
            str(row[0]).casefold()
            for row in ledger.connection.execute("SELECT canonical_url FROM applications")
        }
        limited_boards = {
            _board_slug(str(row[0])).casefold()
            for row in ledger.connection.execute(
                """
                SELECT applications.canonical_url
                FROM applications
                JOIN events ON events.application_id = applications.id
                WHERE events.payload_json LIKE '%provider_application_limit_visible%'
                """
            )
            if _board_slug(str(row[0]))
        }
        cached_jobs = _read_jobs(cache_path)
        live_jobs, refresh_errors = _fresh_jobs(cached_jobs)
        jobs = _candidate_jobs([*live_jobs, *cached_jobs], seen, limited_boards)
        baseline = json.loads(
            (Path(__file__).resolve().parents[1] / "config" / "strategy.default.json").read_text()
        )
        replay = json.loads(
            (Path(__file__).resolve().parents[1] / "config" / "learning-replay.v1.json").read_text()
        )["cases"]
        driver = LearningDriver(ledger, baseline_strategy=baseline, replay_cases=replay)
        prompt_sha256 = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
        discovered: list[dict[str, Any]] = []
        for job in jobs[: max(1, max_jobs)]:
            posting = str(job.get("description") or job.get("descriptionPlain") or "")
            role_family = _role_family(str(job["title"]))
            routed = select_resume(
                posting_text=posting,
                role_family=role_family,
                materials_root=materials_root,
            )
            assignment = driver.assign(str(job["url"]))
            application_id = ledger.add_attributed_application(
                str(job["company"]),
                str(job["title"]),
                str(job["url"]),
                strategy_generation_id=assignment["strategy_generation_id"],
                source="official_ats",
                query_family="official_ashby_tokyo_discovery",
                rank_config=assignment["strategy"],
                role_family=role_family,
                material_variant=routed["resume_variant"],
                message_variant="none",
                model_route="codex",
                prompt_sha256=prompt_sha256,
                material_sha256=routed["resume_sha256"],
            )
            ledger.transition(application_id, "qualified")
            ledger.transition(application_id, "materials_ready")
            discovered.append(
                {
                    "application_id": application_id,
                    "company": str(job["company"]),
                    "title": str(job["title"]),
                    "url": str(job["url"]),
                    "state": "materials_ready",
                }
            )
        return {
            "status": "discovered" if discovered else "no_work",
            "discovered": discovered,
            "live_board_count": len(_japan_board_slugs(cached_jobs)),
            "live_refresh_errors": refresh_errors,
            "provider_limited_boards": sorted(limited_boards),
        }
    finally:
        ledger.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--materials-root", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-jobs", type=int, default=1)
    args = parser.parse_args()
    result = discover_one(
        cache_path=args.cache,
        ledger_path=args.ledger,
        profile_path=args.profile,
        materials_root=args.materials_root,
        prompt_path=args.prompt,
        max_jobs=args.max_jobs,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    os.chmod(args.output, 0o600)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
