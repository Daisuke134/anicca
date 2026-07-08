#!/usr/bin/env python3
"""cadence.py — Cadence Contract dispatcher (REQ-LV-100/101/103, replaces REQ-LV-041's stale
artifact-age judgment with "did today's contracted cadence actually happen"). Pure, no I/O beyond
its own arguments — all real-file/mtime reads are the CALLER's job (verify-loops.sh /
verify-loops-audit.sh / each loop's own healthcheck.sh gather `evidence` and pass it in here).

Five contract kinds (spec §H, design spec Cadence Contract table):
  row-exists  — clip/affiliate/video/gig: did a real ledger row land today (JST calendar day)?
  increment   — bounty: did gated.json's `checked` value actually INCREASE since yesterday
                (not just "a row exists" — a same-value row must NOT read as healthy, this is the
                direct fix for the old fresh()'s "row exists = OK" blind spot)?
  pass-marker — founder-loop: did STATE.md get written today (JST)? Day-granularity only. Does
                NOT read earn-ledger.jsonl (an empty ledger day is NOT the same as "the pass didn't
                run" — record-earn.mjs's anti-fake gates mean zero-earn days are normal).
  recency     — G1 fix: pure elapsed-seconds check, no JST-day boundary at all. Used for anything
                that must run on an hourly (or sub-day) cadence, where pass-marker's day-granularity
                would hide a loop that ran once at 00:01 and then sat dead the rest of the day.
  compound    — pm-earner: logical AND over named sub-conditions (each itself one of the 4 kinds
                above), evaluated recursively. AND, never OR/majority — REQ-LV-101.

CLI entrypoint (mirrors this codebase's `--classify`/`--should-continue` convention —
healthcheck-runtime-loop.sh::hrl_classify, self-fix.sh::sf_should_continue): bash callers invoke
`python3 cadence.py cadence-met '<today>' '<contract_json>' '<evidence_json>'` and read "true"/
"false" from stdout.
"""
from __future__ import annotations

import json
import sys


def cadence_met(today_jst_date: str, contract: dict, evidence: dict) -> bool:
    kind = contract["kind"]

    if kind == "row-exists":
        return today_jst_date in evidence.get("event_dates", [])

    if kind == "increment":
        return evidence.get("today_value", 0) > evidence.get("previous_value", 0)

    if kind == "pass-marker":
        return evidence.get("marker_jst_date") == today_jst_date

    if kind == "recency":
        marker = evidence.get("marker_epoch_seconds")
        now = evidence.get("now_epoch_seconds")
        if marker is None or now is None:
            return False
        max_age_seconds = contract["max_age_min"] * 60
        return (now - marker) <= max_age_seconds

    if kind == "compound":
        by_condition = evidence.get("by_condition", {})
        for sub_contract in contract["conditions"]:
            sub_evidence = by_condition.get(sub_contract["id"], {})
            if not cadence_met(today_jst_date, sub_contract, sub_evidence):
                return False
        return True

    raise ValueError(f"unknown cadence contract kind: {kind!r}")


def streak(evidence_by_date: dict, today_jst_date: str, contract: dict) -> int:
    """Count consecutive days (walking backward from today_jst_date) whose cadence_met() is True.
    Stops at the first missing/failed day — a gap resets rather than being skipped over."""
    import datetime

    count = 0
    date = datetime.date.fromisoformat(today_jst_date)
    while True:
        date_str = date.isoformat()
        day_evidence = evidence_by_date.get(date_str)
        if day_evidence is None or not cadence_met(date_str, contract, day_evidence):
            break
        count += 1
        date -= datetime.timedelta(days=1)
    return count


def _main():
    if len(sys.argv) < 2:
        print("usage: cadence.py cadence-met <today_jst_date> <contract_json> <evidence_json>", file=sys.stderr)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "cadence-met":
        today, contract_json, evidence_json = sys.argv[2], sys.argv[3], sys.argv[4]
        result = cadence_met(today, json.loads(contract_json), json.loads(evidence_json))
        print("true" if result else "false")
        sys.exit(0 if result else 1)
    elif cmd == "streak":
        evidence_by_date_json, today, contract_json = sys.argv[2], sys.argv[3], sys.argv[4]
        result = streak(json.loads(evidence_by_date_json), today, json.loads(contract_json))
        print(result)
        sys.exit(0)
    else:
        print(f"unknown subcommand: {cmd!r}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    _main()
