"""Discover one fresh Japan Workday posting before the model-owned browser wake."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from .ledger import Ledger
from .state import canonical_url, is_excluded_employer


def _fetch_jobs(source: dict[str, str]) -> list[dict[str, Any]]:
    endpoint = (
        f"https://{source['host']}/wday/cxs/{source['tenant']}/"
        f"{source['site']}/jobs"
    )
    request = Request(
        endpoint,
        data=json.dumps(
            {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "Japan"}
        ).encode(),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 job-search-loop/1.0",
        },
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        value = json.load(response)
    rows = value.get("jobPostings") if isinstance(value, dict) else None
    return [row for row in (rows or []) if isinstance(row, dict)]


def discover_one(
    *,
    ledger_path: Path,
    sources: tuple[dict[str, str], ...],
    fetch_jobs: Callable[[dict[str, str]], list[dict[str, Any]]] = _fetch_jobs,
) -> dict[str, Any]:
    ledger = Ledger(ledger_path)
    try:
        queued = []
        for row in ledger.pending_materials_ready_applications():
            if "myworkdayjobs.com" not in str(row["canonical_url"]).casefold():
                continue
            fit = ledger.connection.execute(
                "SELECT decision FROM workday_fit_decisions WHERE application_id = ?",
                (row["application_id"],),
            ).fetchone()
            if fit is None or str(fit["decision"]) == "qualified":
                queued.append(row)
        if queued:
            return {
                "status": "queue_present",
                "errors": [],
                "discovered": [],
                "queued_application_ids": [str(row["application_id"]) for row in queued],
            }
        seen = {
            canonical_url(str(row[0])).casefold()
            for row in ledger.connection.execute("SELECT canonical_url FROM applications")
        }
        candidates: list[dict[str, str | int]] = []
        errors: list[str] = []
        for source in sources:
            if is_excluded_employer(source["company"]):
                continue
            try:
                jobs = fetch_jobs(source)
            except Exception as error:
                errors.append(f"{source['tenant']}:{type(error).__name__}")
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
                        "url": url,
                        "location": location,
                    }
                )
        if not candidates:
            return {"status": "no_fresh_workday", "errors": errors, "discovered": []}
        selected = candidates[0]
        application_id = ledger.add_application(
            str(selected["company"]), str(selected["title"]), str(selected["url"])
        )
        ledger.transition(
            application_id,
            "qualified",
            {"reason": "official_workday_discovery", "location": selected["location"]},
        )
        ledger.transition(
            application_id,
            "materials_ready",
            {"reason": "mandatory_model_browser_lane"},
        )
        return {
            "status": "discovered",
            "errors": errors,
            "discovered": [
                {
                    "application_id": application_id,
                    "company": selected["company"],
                    "title": selected["title"],
                    "url": selected["url"],
                    "location": selected["location"],
                    "state": "materials_ready",
                }
            ],
        }
    finally:
        ledger.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.sources.read_text(encoding="utf-8"))
    sources = tuple(dict(row) for row in payload.get("sources", []))
    result = discover_one(ledger_path=args.ledger, sources=sources)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    os.chmod(args.output, 0o600)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
