"""Fresh official Lever discovery for the shared model browser lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .ashby_discovery import JAPAN_RE, ROLE_RE, _role_family, _role_priority
from .ledger import Ledger
from .learning import LearningDriver
from .resume_routing import select_resume
from .state import canonical_url, is_excluded_employer


SITES = (
    ("binance", "Binance"),
    ("offchainlabs", "Offchain Labs"),
    ("arcadia", "Arcadia"),
    ("jobgether", "Jobgether"),
)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _fetch_json(url: str) -> Any:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "api.lever.co":
        raise ValueError("Lever discovery escaped the official API host")
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "AniccaJobSearch/1.0"},
        method="GET",
    )
    with build_opener(_NoRedirect()).open(request, timeout=15) as response:
        if int(response.status) != 200:
            raise ValueError(f"Lever postings returned HTTP {response.status}")
        return json.load(response)


def live_site_jobs(
    site: str,
    company: str,
    *,
    fetch_json: Callable[[str], Any] = _fetch_json,
) -> list[dict[str, Any]]:
    if not site or not site.replace("-", "").replace("_", "").isalnum():
        raise ValueError("unsafe Lever site slug")
    payload = fetch_json(f"https://api.lever.co/v0/postings/{site}?mode=json")
    if not isinstance(payload, list):
        raise ValueError("unexpected Lever postings response")
    rows: list[dict[str, Any]] = []
    for job in payload:
        if not isinstance(job, dict):
            continue
        title = str(job.get("text") or "").strip()
        url = canonical_url(str(job.get("hostedUrl") or ""))
        parsed = urlsplit(url)
        categories = job.get("categories")
        location = (
            str(categories.get("location") or "")
            if isinstance(categories, dict)
            else ""
        )
        if (
            not title
            or parsed.scheme != "https"
            or parsed.hostname != "jobs.lever.co"
            or not parsed.path.startswith(f"/{site}/")
        ):
            continue
        rows.append(
            {
                "ats": "lever",
                "company": company,
                "title": title,
                "url": url,
                "location": location,
                "is_remote": str(job.get("workplaceType") or "").casefold() == "remote",
                "description": str(job.get("descriptionPlain") or "")[:4_000],
                "posted_at_ms": int(job.get("createdAt") or 0),
            }
        )
    return rows


def candidate_jobs(jobs: list[dict[str, Any]], seen: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job in jobs:
        company = str(job.get("company") or "").strip()
        title = str(job.get("title") or "").strip()
        url = canonical_url(str(job.get("url") or ""))
        parsed = urlsplit(url)
        location = str(job.get("location") or "")
        if (
            str(job.get("ats") or "").casefold() != "lever"
            or not company
            or not title
            or parsed.scheme != "https"
            or parsed.hostname != "jobs.lever.co"
            or url.casefold() in seen
            or is_excluded_employer(company)
            or not ROLE_RE.search(title)
            or not (JAPAN_RE.search(location) or job.get("is_remote") is True)
        ):
            continue
        rows.append({**job, "company": company, "title": title, "url": url})
    rows.sort(
        key=lambda row: (_role_priority(str(row["title"])), int(row.get("posted_at_ms") or 0)),
        reverse=True,
    )
    return rows


def discover_one(
    *,
    ledger_path: Path,
    profile_path: Path,
    materials_root: Path,
    prompt_path: Path,
    max_jobs: int = 1,
) -> dict[str, Any]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    live: list[dict[str, Any]] = []
    errors: list[str] = []
    for site, company in SITES:
        try:
            live.extend(live_site_jobs(site, company))
        except Exception as error:
            errors.append(f"{site}:{type(error).__name__}")
    ledger = Ledger(ledger_path)
    try:
        exclusions = profile.get("candidate", {}).get("employer_exclusions", [])
        ledger.reject_excluded_employers(
            frozenset(str(value) for value in exclusions) if isinstance(exclusions, list) else None
        )
        seen = {
            str(row[0]).casefold()
            for row in ledger.connection.execute("SELECT canonical_url FROM applications")
        }
        jobs = candidate_jobs(live, seen)
        baseline = json.loads(
            (Path(__file__).resolve().parents[1] / "config/strategy.default.json").read_text()
        )
        replay = json.loads(
            (Path(__file__).resolve().parents[1] / "config/learning-replay.v1.json").read_text()
        )["cases"]
        driver = LearningDriver(ledger, baseline_strategy=baseline, replay_cases=replay)
        prompt_sha256 = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
        discovered: list[dict[str, Any]] = []
        for job in jobs[: max(1, max_jobs)]:
            role_family = _role_family(str(job["title"]))
            routed = select_resume(
                posting_text=str(job.get("description") or ""),
                role_family=role_family,
                materials_root=materials_root,
            )
            assignment = driver.assign(str(job["url"]))
            application_id = ledger.add_attributed_application(
                str(job["company"]), str(job["title"]), str(job["url"]),
                strategy_generation_id=assignment["strategy_generation_id"],
                source="official_ats", query_family="official_lever_japan_discovery",
                rank_config=assignment["strategy"], role_family=role_family,
                material_variant=routed["resume_variant"], message_variant="none",
                model_route="codex", prompt_sha256=prompt_sha256,
                material_sha256=routed["resume_sha256"],
            )
            ledger.transition(application_id, "qualified")
            ledger.transition(application_id, "materials_ready")
            discovered.append({
                "application_id": application_id, "company": job["company"],
                "title": job["title"], "url": job["url"], "state": "materials_ready",
            })
        return {
            "status": "discovered" if discovered else "no_work",
            "discovered": discovered,
            "queried_sites": [site for site, _ in SITES],
            "live_refresh_errors": errors,
        }
    finally:
        ledger.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--materials-root", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-jobs", type=int, default=1)
    args = parser.parse_args()
    result = discover_one(
        ledger_path=args.ledger, profile_path=args.profile,
        materials_root=args.materials_root, prompt_path=args.prompt, max_jobs=args.max_jobs,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    os.chmod(args.output, 0o600)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
