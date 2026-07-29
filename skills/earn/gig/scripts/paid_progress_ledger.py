#!/usr/bin/env python3
"""paid_progress_ledger.py -- the single source of truth for "how many buyer-visible
progress replies did we send on paid contracts".

Why this exists: on 2026-07-27 (X22) the paid lane recorded this fact into
~/gig/applied.jsonl, the apply lane's scratch pad. Two true principles collided
there and the collision was resolved in the wrong direction:

  A  The paid-work gate contract says every lower-priority ledger is byte-frozen
     while a paid pass runs (tests/test_gig_paid_work_gate.sh). applied.jsonl is
     one of those ledgers. A paid pass that appended to it broke the invariant --
     measured: the green success case failed on exactly one of eight hashes, and
     only applied.jsonl differed.

  B  The reply really did reach the buyer. An external side effect cannot be
     rolled back by deleting its record, and an unrecorded action is
     indistinguishable from an action never taken (X1).

Both hold. The defect was never "record it" or "don't record it" -- it was
recording it in a file that means something else. applied.jsonl's readers key on
`status`, and none of them read `action`:

  application_ledger.classify_event   "replied" -> STAGE_ENGAGED
  category_bandit                     learns arms from that classification
  funnel.py / gig_funnel.py           "replied" -> the apply funnel's replied stage

So a progress update on an already-won, already-paid contract was being counted
as engagement on a 募集 application that was never applied to. Worse,
funnel.dedupe_latest_status keys on requestId, so one paid_progress row could
become the *latest* row for an id and mask a deeper real stage. And the id
written was often a talkroom id, not a 募集 id, so application_ledger either
mis-joined it through the identity chain or counted it as unrecoverable.

That is the X11 failure again -- one fact projected into a ledger built for a
different fact. This module owns the paid-progress fact instead. Moving the write
here does not lose the record (principle B): it relocates it to the only place
where the record is true, and it restores the freeze (principle A) for free.

TAXONOMY

  identity   A paid contract is identified by the project's request id, falling
             back to its talkroom id. Both are carried explicitly so a reader
             never has to guess which id space it is looking at -- that guess is
             what corrupted the apply funnel.

  evidence   A row is only written when reconcile_paid_delivery.py returned
             ok=true, the reconciled project state says buyer_visible is true,
             AND the fresh browser manifest says send_performed=true. A failed
             send or a verified observation of an already-present message writes
             nothing. The ledger records new buyer-visible effects, not checks.

  dedup      One row per (pass_id, request id). A retried pass that re-reconciles
             an already-recorded send appends nothing, so replaying a pass cannot
             inflate the count.

  time       ts is epoch seconds, written by us, never by a model.

Contract: the recorder is fatal on unverified input (it refuses to claim a send
that evidence does not support); the reader is read-only and never fatal, so a
missing or corrupt ledger yields zero rather than failing a pass that did real
customer work.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

LEDGER_FILENAME = "paid-progress.jsonl"

# Kept for readers that still bucket paid work alongside the apply lane's rows.
# These are the row's own fields, not a projection of somebody else's taxonomy.
STATUS_REPLIED = "replied"
ACTION_PAID_PROGRESS = "paid_progress"


def state_dir() -> Path:
    return Path(os.environ.get("GIG_STATE_DIR") or (Path.home() / "gig"))


def default_ledger_path() -> Path:
    return state_dir() / LEDGER_FILENAME


@dataclass(frozen=True)
class PaidProgressEvent:
    request_id: str
    talkroom_id: str
    pass_id: str
    artifact_version: str
    package_sha256: str
    ts: float | None


def _coerce_ts(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def load_events(path: Path | None = None) -> list[PaidProgressEvent]:
    """Tolerant reader. A missing or corrupt ledger is zero events, never an error."""
    ledger = Path(path) if path is not None else default_ledger_path()
    try:
        raw = ledger.read_text(encoding="utf-8")
    except OSError:
        return []
    events: list[PaidProgressEvent] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        events.append(PaidProgressEvent(
            request_id=str(row.get("requestId") or ""),
            talkroom_id=str(row.get("talkroom_id") or ""),
            pass_id=str(row.get("pass_id") or ""),
            artifact_version=str(row.get("artifact_version") or ""),
            package_sha256=str(row.get("package_sha256") or ""),
            ts=_coerce_ts(row.get("ts")),
        ))
    return events


def count(events: list[PaidProgressEvent], *, since: float | None = None,
          until: float | None = None) -> int:
    """Number of buyer-visible progress replies in the window. Events, not contracts."""
    total = 0
    for event in events:
        if since is not None or until is not None:
            if event.ts is None:
                continue
            if since is not None and event.ts < since:
                continue
            if until is not None and event.ts >= until:
                continue
        total += 1
    return total


def count_contracts(events: list[PaidProgressEvent], *, since: float | None = None,
                    until: float | None = None) -> int:
    """Number of distinct paid contracts we pushed progress to. Contracts, not events."""
    seen = set()
    for event in events:
        if since is not None or until is not None:
            if event.ts is None:
                continue
            if since is not None and event.ts < since:
                continue
            if until is not None and event.ts >= until:
                continue
        identity = event.request_id or event.talkroom_id
        if identity:
            seen.add(identity)
    return len(seen)


def build_row(reconciled: dict, pass_id: str, evidence_dir: str) -> dict:
    """Turn a verified reconciliation into the row, or raise if it is not verified.

    Raising here is the point: this is the boundary where "we think we sent it"
    becomes "the buyer saw it". Anything less than proof must not become a row.
    """
    if not isinstance(reconciled, dict) or not reconciled.get("ok"):
        raise ValueError("paid progress reconciliation was not verified")
    request_id = str(reconciled.get("request_id") or reconciled.get("talkroom_id") or "")
    if not request_id or not (
        reconciled.get("buyer_visible") or reconciled.get("buyer_visible_response")
    ):
        raise ValueError("paid progress lacks buyer-visible request identity")
    talkroom_id = str(reconciled.get("talkroom_id") or "")
    url = reconciled.get("marketplace_url") or (
        "https://coconala.com/talkrooms/" + (talkroom_id or request_id))
    return {
        "ts": int(time.time()),
        "pass_id": pass_id,
        "requestId": request_id,
        "talkroom_id": reconciled.get("talkroom_id"),
        "status": STATUS_REPLIED,
        "action": ACTION_PAID_PROGRESS,
        "buyer_visible": True,
        "artifact_version": str(reconciled.get("latest_buyer_visible_version")
                               or reconciled.get("current_version") or ""),
        "package_sha256": str(reconciled.get("latest_buyer_visible_package_sha256")
                              or reconciled.get("current_package_sha256") or ""),
        "url": url,
        "evidence_dir": evidence_dir,
        "note": ("buyer-visible progress reply verified by paid_queue_evidence.py "
                 "and project ledger reconciliation"),
    }


def already_recorded(ledger: Path, pass_id: str, request_id: str) -> bool:
    for event in load_events(ledger):
        if event.pass_id == pass_id and event.request_id == request_id:
            return True
    return False


def record(reconciled: dict, *, pass_id: str, evidence_dir: str,
           ledger: Path | None = None) -> bool:
    """Append a new verified send; return False for observation-only or dedupe."""
    if not isinstance(reconciled, dict) or reconciled.get("send_performed") is not True:
        return False
    path = Path(ledger) if ledger is not None else default_ledger_path()
    row = build_row(reconciled, pass_id, evidence_dir)
    if already_recorded(path, pass_id, row["requestId"]):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return True


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("record", help="append one verified buyer-visible progress row")
    rec.add_argument("--ledger", type=Path, default=None)
    rec.add_argument("--pass-id", required=True)
    rec.add_argument("--evidence-dir", required=True)
    rec.add_argument("--reconciled", type=Path, default=None,
                     help="file holding reconcile_paid_delivery.py JSON; default stdin")

    rep = sub.add_parser("count", help="report counts over the ledger")
    rep.add_argument("--ledger", type=Path, default=None)

    args = parser.parse_args(argv)

    if args.command == "record":
        raw = (args.reconciled.read_text(encoding="utf-8") if args.reconciled
               else sys.stdin.read())
        try:
            reconciled = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"paid progress reconciliation was not JSON: {exc}", file=sys.stderr)
            return 1
        try:
            record(reconciled, pass_id=args.pass_id,
                   evidence_dir=args.evidence_dir, ledger=args.ledger)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    events = load_events(args.ledger)
    print(json.dumps({"events": count(events),
                      "contracts": count_contracts(events)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
