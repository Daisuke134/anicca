#!/usr/bin/env python3
"""reconcile_selfheal.py -- F3 (docs/loop-engineering/26-gig-loop-asis-tobe-plan.md sec CC'/EW'):
turns A6's reconcile-report.json (site_ledger_reconcile.py, written every pass) into selfheal
requests.

WHY: A6 already records, every pass, exactly where the live site and state.json disagree --
but nothing consumed it. A single disagreeing pass is normal timing skew (the site snapshot
and state.json are read moments apart); the same (check, talkroom) disagreeing for 3+
CONSECUTIVE reports is real drift nothing is fixing (this is exactly how 91000001's
buyer_visible_artifact_observed stayed false while the site's delivery link sat there for
days -- see site_ledger_reconcile.py's own docstring). One-off flickers are not requested.

Sibling of F1 (selfimprove_consumer.py), called from its main() so on_exit still runs one
process and prints one summary line -- this is not a second consumer pipeline. It shares F1's
request ledger (the configured gig state directory) and one host-state slot, the same
{kind, reason, ...} shape, and
the same "never clobber an in-flight request" rule.

STATE: a small persistence file (default ~/gig/.reconcile-selfheal-state.json) keyed by
"<check_name>|<talkroom_id>". Each key holds {streak, requested}: streak counts consecutive
*reports* (across passes, not within one) where that check disagreed; requested is true once a
request has been emitted for the current streak (dedupe -- one open request per (check,
talkroom) until the discrepancy clears, at which point the key is dropped, so a later
recurrence can request again after another 3 consecutive reports).

IDEMPOTENT ACROSS RE-RUNS ON THE SAME REPORT: the state file remembers the generated_at of the
last report it scored, so invoking this twice against the same newest report (e.g. a manual
debug run between passes) does not double-count the streak.

FIRST RUN: the persistence state starts empty (no history to replay), so nothing can qualify
until 3 real consecutive reports have been scored after this ships -- same no-flood contract
F1 uses for the audit cursor.

FAIL-CLOSED: no reconcile-report.json found, or its JSON does not match the expected shape (a
dict with a "rows" list) -- skip, log to stderr, no state mutated. Malformed rows within an
otherwise-valid report are counted and skipped, never guessed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

KIND = "site_ledger_divergence"
PERSISTENCE_THRESHOLD = 3


def find_newest_report(evidence_root: Path) -> Path | None:
    candidates = sorted(
        evidence_root.glob("gig-pass-*/reconcile-report.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _load_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"last_report_generated_at": None, "entries": {}}
    if isinstance(data, dict) and isinstance(data.get("entries"), dict):
        return data
    return {"last_report_generated_at": None, "entries": {}}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def run(
    state_path: Path,
    request_ledger: Path,
    selfheal_req: Path,
    *,
    report_path: Path | None = None,
    evidence_root: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "report": None,
        "checked_pairs": 0,
        "qualified": 0,
        "cleared": 0,
        "skipped_malformed_rows": 0,
        "selfheal_req_written": False,
        "sample": None,
        "dry_run": dry_run,
        "skipped_reason": None,
    }

    if report_path is None:
        report_path = find_newest_report(evidence_root or Path.home() / "gig" / "evidence")
    if report_path is None or not report_path.exists():
        summary["skipped_reason"] = "no_report_found"
        return summary

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        summary["skipped_reason"] = f"unreadable_report: {exc}"
        print(f"reconcile_selfheal: skipping unreadable report {report_path}: {exc}", file=sys.stderr)
        return summary
    if not isinstance(report, dict) or not isinstance(report.get("rows"), list):
        summary["skipped_reason"] = "malformed_report_shape"
        print(f"reconcile_selfheal: skipping malformed report shape: {report_path}", file=sys.stderr)
        return summary

    summary["report"] = str(report_path)
    generated_at = report.get("generated_at")

    state = _load_state(state_path)
    if generated_at is not None and state.get("last_report_generated_at") == generated_at:
        summary["skipped_reason"] = "already_scored_this_report"
        return summary

    entries: dict[str, Any] = state["entries"]
    new_requests: list[dict[str, Any]] = []
    now = int(time.time())

    for row in report["rows"]:
        if not isinstance(row, dict) or row.get("status") != "ok":
            continue
        talkroom_id = row.get("talkroom_id")
        checks = row.get("checks")
        if talkroom_id is None or not isinstance(checks, list):
            summary["skipped_malformed_rows"] += 1
            continue
        for check in checks:
            if not isinstance(check, dict) or "name" not in check or "agree" not in check:
                summary["skipped_malformed_rows"] += 1
                continue
            key = f"{check['name']}|{talkroom_id}"
            entry = entries.get(key) or {"streak": 0, "requested": False}

            if check["agree"]:
                if entry.get("streak"):
                    summary["cleared"] += 1
                entries.pop(key, None)
                continue

            entry["streak"] = int(entry.get("streak", 0)) + 1
            summary["checked_pairs"] += 1
            if entry["streak"] >= PERSISTENCE_THRESHOLD and not entry.get("requested"):
                reason = (
                    f"site_ledger_reconcile: {check['name']} disagrees for talkroom "
                    f"{talkroom_id} across {entry['streak']} consecutive reports "
                    f"(site={check.get('site_value')!r} ledger={check.get('ledger_value')!r})"
                )
                request = {
                    "ts": now,
                    "kind": KIND,
                    "reason": reason,
                    "failure_reason": reason,
                    "project_id": row.get("project_id"),
                    "talkroom_id": talkroom_id,
                    "check": check["name"],
                }
                new_requests.append(request)
                summary["qualified"] += 1
                if summary["sample"] is None:
                    summary["sample"] = request
                entry["requested"] = True
            entries[key] = entry

    if dry_run:
        return summary

    if new_requests:
        request_ledger.parent.mkdir(parents=True, exist_ok=True)
        with request_ledger.open("a", encoding="utf-8") as handle:
            for request in new_requests:
                handle.write(json.dumps(request, ensure_ascii=False) + "\n")
        # Same rule as F1: never clobber an in-flight request in the singular slot.
        if not selfheal_req.exists():
            selfheal_req.parent.mkdir(parents=True, exist_ok=True)
            tmp = selfheal_req.with_suffix(selfheal_req.suffix + ".tmp")
            tmp.write_text(json.dumps(new_requests[-1], ensure_ascii=False), encoding="utf-8")
            tmp.replace(selfheal_req)
            summary["selfheal_req_written"] = True

    state["last_report_generated_at"] = generated_at
    state["entries"] = entries
    _write_state(state_path, state)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_root = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
    host_state = Path(os.environ.get(
        "GIG_HOST_STATE_DIR",
        str(Path.home() / ".local" / "state" / "mr-bot" / "state"),
    ))
    parser.add_argument("--report", type=Path, default=None, help="override: score this report instead of the newest")
    parser.add_argument("--evidence-root", type=Path, default=default_root / "evidence")
    parser.add_argument("--state", type=Path, default=default_root / ".reconcile-selfheal-state.json")
    parser.add_argument("--request-ledger", type=Path, default=default_root / "selfheal-request.jsonl")
    parser.add_argument(
        "--selfheal-req", type=Path,
        default=Path(os.environ.get(
            "GIG_SELFHEAL_REQ", str(host_state / ".gig-core-selfheal-request.json")
        )),
    )
    parser.add_argument("--dry-run", action="store_true", help="report what would happen; write nothing")
    args = parser.parse_args(argv)

    summary = run(
        args.state, args.request_ledger, args.selfheal_req,
        report_path=args.report, evidence_root=args.evidence_root, dry_run=args.dry_run,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
