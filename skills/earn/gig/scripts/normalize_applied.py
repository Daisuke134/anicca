#!/usr/bin/env python3
"""Repair applied.jsonl rows so real applications are actually counted.

The apply lane's ledger row is written by the agent from a prompt, not by code, so its
shape drifts. On 2026-07-27 the lane submitted a genuine application -- Coconala showed
the 応募しました toast and the evidence screenshot captured it -- and wrote:

    {"requestId": "5176621", "title": "...", "applied_at": "2026-07-27",
     "price_proposed": 8000, "deliver_date": "2026-07-30"}

No "ts" and no "status". Every reader keys on those two fields: gig_funnel counts
status == "applied", the daily report's 24h delta reads ts. So the first application in
four and a half days was invisible to all of them. Work that happened but is not counted
is indistinguishable from work that did not happen, and the loop steers by these numbers.

The repair is deliberately evidence-gated rather than inferential. A missing status is
only filled in when the pass left a "<requestId>-submitted.png" behind, which is written
after the submission is visible on screen. A row with no such proof keeps whatever it
has: this file must never be able to invent an application.

ts is derived from applied_at when absent, so the row lands on the day it happened
rather than at the epoch (the malformed row above sorted to 1970 and fell outside every
window).

Idempotent and atomic: rerunning changes nothing, and a crash mid-write cannot truncate
the ledger.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path


def _evidence_ids(evidence_root: Path) -> set[str]:
    """requestIds whose submission was photographed on the live page."""
    found: set[str] = set()
    try:
        entries = list(evidence_root.glob("*-B2-*-submitted.png"))
    except OSError:
        return found
    for entry in entries:
        parts = entry.name.split("-B2-", 1)
        if len(parts) != 2:
            continue
        tail = parts[1]
        request_id = tail.rsplit("-submitted.png", 1)[0]
        if request_id:
            found.add(request_id)
    return found


def _epoch_from_date(value: str) -> int | None:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return int(datetime.strptime(value.strip(), fmt).timestamp())
        except (ValueError, AttributeError):
            continue
    return None


def normalize(rows: list[dict], proven: set[str], now: float) -> tuple[list[dict], int]:
    """Return repaired rows and how many changed. Pure, so it is testable offline."""
    changed = 0
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            out.append(row)
            continue
        fixed = dict(row)
        request_id = str(fixed.get("requestId") or "").strip()

        if not fixed.get("ts"):
            stamp = _epoch_from_date(str(fixed.get("applied_at") or ""))
            if stamp is not None:
                fixed["ts"] = stamp

        if not fixed.get("status") and request_id and request_id in proven:
            # Only the screenshot may promote a row. Nothing here guesses.
            fixed["status"] = "applied"
            fixed.setdefault("evidence", f"{request_id}-submitted.png")

        if fixed != row:
            fixed["normalized_at"] = int(now)
            changed += 1
        out.append(fixed)
    return out, changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=str(Path.home() / "gig" / "applied.jsonl"))
    ap.add_argument("--evidence-root", default=str(Path.home() / "gig" / "evidence"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ledger = Path(args.ledger)
    if not ledger.exists():
        print(json.dumps({"status": "no_ledger", "changed": 0}))
        return 0

    rows: list[dict] = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            # A torn line is left exactly as found rather than dropped; losing a row
            # here would understate real work, which is the failure this file exists
            # to prevent.
            rows.append({"_unparsed": line})

    proven = _evidence_ids(Path(args.evidence_root))
    fixed, changed = normalize(rows, proven, time.time())

    if args.dry_run or changed == 0:
        print(json.dumps({
            "status": "dry_run" if args.dry_run else "unchanged",
            "changed": changed, "proven_ids": len(proven),
        }, ensure_ascii=False))
        return 0

    tmp = ledger.with_suffix(f".{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for row in fixed:
            if "_unparsed" in row:
                handle.write(row["_unparsed"] + "\n")
            else:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, ledger)

    print(json.dumps({"status": "repaired", "changed": changed,
                      "proven_ids": len(proven)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
