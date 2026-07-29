#!/usr/bin/env python3
"""Count real-world effects per lane since an epoch, from each lane's authoritative ledger.

Why this exists: gig_pass.sh recorded lane attempts without --records, so every lane's
productivity clock (last_productive_at) sat at 0.0 forever and "alive but earning
nothing" -- the exact shape of the 4.5 day application outage -- was undetectable.
Counting from the model's self-reported step JSON would just move the lie: the agent
already once wrote "applied" rows the funnel could not count. So productivity is
evidence-gated: only rows in the ledger each lane's own controller writes are counted.

Which ledger is authoritative per lane (verified against the live files 2026-07-27):

  apply    ~/gig/applied.jsonl                jsonl, status=="applied", ts epoch s
  reply    ~/gig/connector-outbox.sqlite3     connector_actions, state='replied',
                                              seller_sent_at (fallback updated_at)
  fulfill  ~/gig/evidence/gig-pass-*/paid-work-transaction.json
                                              committed internal paid-work bundles
            ~/gig/paid-progress.jsonl          newly sent buyer-visible paid progress
  list     ~/gig/shuppin.jsonl                via listing_ledger.py -- the single
                                              source of truth for listing counts.
                                              Productive = a draft made or a listing
                                              published; status is freeform agent
                                              text and deliberately ignored.

The listing lane used to count those rows itself with
`isinstance(row["ts"], (int, float))`, which silently dropped 26 of 104 live rows whose
ts is an ISO 8601 string -- a lane that had published could still read as barren. It now
shares listing_ledger's taxonomy, id normaliser and timestamp parser with the funnel and
the daily report, so the three cannot drift apart again.

Contract (same as record_lane_closures): ledger-only, never fatal. A missing, locked,
or corrupt ledger counts 0 for that lane without erasing healthy sibling lanes,
complains on stderr, and exits 0 -- bookkeeping must never fail customer work.

Usage: lane_productivity.py --since EPOCH
Output: one "lane N" line per lane (apply reply fulfill list), N >= 0.
Env: GIG_STATE_DIR (default ~/gig), GIG_REPLY_OUTBOX_DB (default STATE/connector-outbox.sqlite3)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import listing_ledger  # noqa: E402  -- the single source of truth for listing counts

STATE = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))


def _rows(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            yield row


def count_apply(since: float) -> int:
    return len(_apply_evidence(since))


def _apply_evidence(since: float) -> list[dict]:
    matched = []
    for row in _rows(STATE / "applied.jsonl"):
        ts = row.get("ts")
        if (
            row.get("status") != "applied"
            or isinstance(ts, bool)
            or not isinstance(ts, (int, float))
            or ts < since
        ):
            continue
        matched.append({
            "request_id": str(row.get("requestId") or row.get("request_id") or ""),
            "ts": float(ts),
        })
    return matched


def _listing_counts(since: float, until: float | None = None):
    return listing_ledger.count_ledger(
        STATE / listing_ledger.LEDGER_FILENAME, since=since, until=until
    )


def count_list(since: float) -> int:
    """Identity-bound drafts/publications; unverifiable rows are not effects."""
    return len(_listing_evidence(since)[1])


def _listing_evidence(since: float) -> tuple[str, list[dict]]:
    matched = []
    published = False
    created = False
    updated = False
    for event in listing_ledger.load_events(STATE / listing_ledger.LEDGER_FILENAME):
        if event.ts is None or event.ts < since:
            continue
        if event.kind not in {
            listing_ledger.KIND_PUBLISHED,
            listing_ledger.KIND_CREATED,
            listing_ledger.KIND_UPDATED,
        }:
            continue
        if not event.service_ids:
            continue
        published = published or event.kind == listing_ledger.KIND_PUBLISHED
        created = created or event.kind == listing_ledger.KIND_CREATED
        updated = updated or event.kind == listing_ledger.KIND_UPDATED
        matched.append({
            "kind": event.kind,
            "service_ids": list(event.service_ids),
            "ts": event.ts,
        })
    action_kind = "publish" if published else "draft" if created else "update"
    return action_kind, matched


def count_list_published(since: float, until: float | None = None) -> int:
    """Distinct listings published in the window -- the same quantity the funnel and
    the daily report publish. Kept separate from count_list because "did this lane do
    work" and "how many listings do we have" are different questions; conflating them
    is what let the three systems disagree."""
    return _listing_counts(since, until).published_listings


def count_reply(since: float) -> int:
    return len(_reply_evidence(since))


def _reply_evidence(since: float) -> list[dict]:
    db = Path(os.environ.get("GIG_REPLY_OUTBOX_DB", str(STATE / "connector-outbox.sqlite3")))
    if not db.exists():
        return []
    # mode=ro: the outbox is live production state and a counter must not create,
    # lock-upgrade, or otherwise write it.
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT action_id,COALESCE(seller_sent_at, updated_at) AS sent_at "
            "FROM connector_actions WHERE state = 'replied' "
            "AND COALESCE(seller_sent_at, updated_at) >= ? ORDER BY action_id",
            (since,),
        ).fetchall()
        return [
            {"action_id": int(action_id), "sent_at": int(sent_at)}
            for action_id, sent_at in rows
        ]
    finally:
        conn.close()


def _committed_delivery_evidence(since: float) -> list[dict]:
    matched = []
    for ledger in sorted(
        (STATE / "evidence").glob("gig-pass-*/paid-work-transaction.json")
    ):
        try:
            raw = ledger.read_bytes()
            row = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            continue
        if row.get("status") != "committed":
            continue
        finished = row.get("finished_at")
        if not isinstance(finished, str):
            continue
        try:
            when = datetime.datetime.fromisoformat(finished)
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=datetime.timezone.utc)
        if when.timestamp() >= since:
            matched.append({
                "pass_id": ledger.parent.name.removeprefix("gig-pass-"),
                "finished_at": finished,
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
    return matched


def _paid_progress_evidence(since: float) -> list[dict]:
    matched = []
    for row in _rows(STATE / "paid-progress.jsonl"):
        ts = row.get("ts")
        if (
            row.get("action") != "paid_progress"
            or row.get("status") != "replied"
            or isinstance(ts, bool)
            or not isinstance(ts, (int, float))
            or ts < since
        ):
            continue
        matched.append({
            "pass_id": str(row.get("pass_id") or ""),
            "talkroom_id": str(row.get("talkroom_id") or ""),
            "ts": float(ts),
        })
    return matched


def count_fulfill(since: float) -> int:
    """Internal committed work plus newly sent buyer-visible paid progress."""
    return len(_committed_delivery_evidence(since)) + len(_paid_progress_evidence(since))


def _evidence_hash(lane: str, records: list[dict]) -> str | None:
    if not records:
        return None
    payload = json.dumps(
        {"lane": lane, "records": records},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def closure_snapshot(since: float) -> dict[str, dict]:
    """Classify this pass from the same authoritative rows used by productivity.

    The unified lane ledger is a closure index, not a second source of truth.  A
    concrete action is therefore recorded only when a lane-owned ledger contains
    a matching row at/after the pass start; otherwise a lane that ran closes as a
    verified noop.
    """
    def safe(lane: str, reader, fallback):
        try:
            return reader(since)
        except Exception as exc:  # noqa: BLE001 -- isolate a broken lane ledger
            print(
                f"lane_productivity: {lane} closure evidence unreadable: {exc}",
                file=sys.stderr,
            )
            return fallback

    apply_rows = safe("application", _apply_evidence, [])
    reply_rows = safe("reply", _reply_evidence, [])
    listing_kind, listing_rows = safe(
        "listing", _listing_evidence, ("publish", [])
    )
    progress_rows = safe("delivery-progress", _paid_progress_evidence, [])
    build_rows = safe("delivery-build", _committed_delivery_evidence, [])
    delivery_rows = progress_rows + build_rows

    def closure(lane: str, action_kind: str, rows: list[dict]) -> dict:
        return {
            "records": len(rows),
            "action_kind": action_kind if rows else "verified_noop",
            "evidence_hash": _evidence_hash(lane, rows),
        }

    return {
        "application": closure("application", "apply", apply_rows),
        "delivery": closure(
            "delivery", "progress" if progress_rows else "build", delivery_rows
        ),
        "listing": closure("listing", listing_kind, listing_rows),
        "reply": closure("reply", "reply", reply_rows),
    }


COUNTERS = {
    "apply": count_apply,
    "reply": count_reply,
    "fulfill": count_fulfill,
    "list": count_list,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=float, required=True,
                    help="pass start epoch; only effects at/after this count")
    ap.add_argument(
        "--closure-json",
        action="store_true",
        help="emit concrete action/noop closure metadata with evidence hashes",
    )
    args = ap.parse_args()

    if args.closure_json:
        try:
            snapshot = closure_snapshot(args.since)
        except Exception as exc:  # noqa: BLE001 -- bookkeeping is never pass-fatal
            print(f"lane_productivity: closure evidence unreadable: {exc}", file=sys.stderr)
            snapshot = {
                lane: {
                    "records": 0,
                    "action_kind": "verified_noop",
                    "evidence_hash": None,
                }
                for lane in ("application", "delivery", "listing", "reply")
            }
        print(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
        return 0

    for lane, counter in COUNTERS.items():
        try:
            count = counter(args.since)
        except Exception as exc:  # noqa: BLE001 -- degrade to 0, never fail the pass
            print(f"lane_productivity: {lane} ledger unreadable: {exc}", file=sys.stderr)
            count = 0
        print(f"{lane} {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
