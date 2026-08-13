from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .ledger import FenceError, Ledger
from .playwright_ats import ranked_pre_submit_candidates
from .state import canonical_url
from .summary import write_summary


EXCLUDED_APPLICATION_STATES = frozenset(
    {
        "submit_claimed",
        "submit_unknown",
        "submitted",
        "recruiter_contact",
        "screening",
        "assessment",
        "interview",
        "rejected",
        "withdrawn",
        "offer",
    }
)


def filter_terminal_candidates(
    ledger_path: Path,
    payload: dict[str, Any],
    *,
    preserve_cross_owner_audit: bool = False,
) -> dict[str, Any]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("prefilter candidates are missing")
    ledger = Ledger(Path(ledger_path))
    included: list[dict[str, Any]] = []
    reasons: list[str] = []
    try:
        applications = ledger.connection.execute(
            "SELECT company, title, canonical_url, current_state, owner FROM applications"
        ).fetchall()
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            candidate_url = canonical_url(str(candidate.get("official_url") or ""))
            candidate_alias = ledger._posting_alias(
                str(candidate.get("company") or ""),
                str(candidate.get("title") or ""),
            )
            matching = next(
                (
                    row
                    for row in applications
                    if canonical_url(str(row["canonical_url"])) == candidate_url
                    or (
                        str(row["canonical_url"]).startswith("evidence://")
                        and ledger._posting_alias(str(row["company"]), str(row["title"]))
                        == candidate_alias
                    )
                ),
                None,
            )
            state = str(matching["current_state"]) if matching is not None else None
            if (
                state in EXCLUDED_APPLICATION_STATES
                and not (
                    preserve_cross_owner_audit
                    and str(matching["owner"]) != "agent"
                )
            ):
                reasons.append(state)
                continue
            included.append(candidate)
    finally:
        ledger.close()
    return {
        **payload,
        "candidates": included,
        "terminal_filter": {
            "observed_count": len(candidates),
            "excluded_count": len(reasons),
            "included_count": len(included),
            "reasons": reasons,
        },
    }


def materialize_canonical_routes(
    ledger_path: Path, prefilter_result: Path
) -> list[dict[str, Any]]:
    payload = json.loads(Path(prefilter_result).read_text(encoding="utf-8"))
    payload = filter_terminal_candidates(
        ledger_path, payload, preserve_cross_owner_audit=True
    )
    candidates = ranked_pre_submit_candidates(payload, limit=3)
    ledger = Ledger(Path(ledger_path))
    materialized: list[dict[str, Any]] = []
    try:
        for candidate in candidates:
            official_url = str(candidate.get("official_url") or "")
            url_sha256 = hashlib.sha256(official_url.encode("utf-8")).hexdigest()
            try:
                application_id = ledger.add_application(
                    str(candidate.get("company") or ""),
                    str(candidate.get("title") or ""),
                    official_url,
                )
            except FenceError as error:
                if "canonical posting is already owned by " not in str(error):
                    raise
                materialized.append({"status": "skipped_cross_owner", "reason": "canonical_posting_owned_elsewhere", "url_sha256": url_sha256})
                continue
            source_material = json.dumps(
                {
                    "official_url": official_url,
                    "source_spans": list(candidate.get("source_spans") or []),
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            route_id = ledger.register_application_route(
                application_id,
                route_kind="canonical_ats",
                endpoint=official_url,
                ordinal=1,
                source_url=official_url,
                source_sha256=hashlib.sha256(source_material.encode("utf-8")).hexdigest(),
                recipient_acceptance="not_applicable",
            )
            materialized.append(
                {
                    "application_id": application_id,
                    "route_id": route_id,
                    "url_sha256": url_sha256,
                }
            )
    finally:
        ledger.close()
    return materialized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("filter",))
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    filtered = filter_terminal_candidates(args.ledger, payload)
    write_summary(args.output, filtered)
    print(json.dumps(filtered["terminal_filter"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
