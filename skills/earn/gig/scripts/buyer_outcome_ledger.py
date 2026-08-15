#!/usr/bin/env python3
"""buyer_outcome_ledger.py -- E2 (gig loop docs/loop-engineering/26-*.md sec CC'):
buyer reactions as an outcome metric, not just a screen a human happens to read.

WHY: A4's marketplace-snapshot.json already carries buyer_recent_messages per order
(coconala_queue_snapshot.py) but nothing durable outlives one pass's evidence dir --
a message like 買い手B's "ほぼ思った通りの仕上がりです！" is real signal about
whether the work actually satisfied the buyer, and it was being observed once and
then discarded when the next pass's evidence directory replaced it.

This script reads the freshest pass evidence's marketplace-snapshot.json and appends
each buyer message not already recorded to ~/gig/buyer-outcomes.jsonl, one row per
message: {ts, talkroom_id, project_id, text, attachments_count, phase, reaction}.
`text` is used as-is -- coconala_queue_snapshot.py's safe_text() already truncated
and sanitized it before it reached the snapshot; this script does not re-sanitize.

`reaction` is always written null. Classifying a message ("this reads as satisfied",
"this reads as a complaint") is judgment, and per building-agents judgment belongs to
a model, never to a keyword list hardcoded here -- a later step reads the null
`reaction` rows and fills them in.

DEDUPE: buyer_recent_messages is a rolling last-10 window per talkroom, so the same
message reappears across many consecutive passes. A message is identified by
sha256(text)[:16] + talkroom_id, recomputed from what is already on disk rather than
stored as its own field, so the ledger schema stays exactly the fields above and nothing
else. Running this script twice against the same snapshot appends nothing the second
time.

SAFETY (fail-closed, mirrors project_janitor.py's contract): a missing/unparsable
snapshot returns an empty summary. One bad order or one bad message must never stop
the rest of the scan. No network calls, no writes outside --ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


def _dedupe_key(talkroom_id: str, text: str) -> str:
    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]
    return f"{talkroom_id}:{digest}"


def _existing_keys(ledger_path: Path) -> set[str]:
    keys: set[str] = set()
    if not ledger_path.exists():
        return keys
    try:
        with ledger_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                talkroom_id = row.get("talkroom_id")
                text = row.get("text")
                if talkroom_id is not None and text is not None:
                    keys.add(_dedupe_key(str(talkroom_id), str(text)))
    except OSError:
        pass
    return keys


def _freshest_evidence_dir(evidence_root: Path) -> Path | None:
    if not evidence_root.is_dir():
        return None
    candidates = [
        d for d in evidence_root.iterdir()
        if d.is_dir() and (d / "marketplace-snapshot.json").is_file()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda d: d.stat().st_mtime)


def _project_phase(projects_root: Path, project_id: str | None) -> str | None:
    if not project_id:
        return None
    state_path = projects_root / project_id / "state.json"
    if not state_path.is_file():
        return None
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(state, dict):
        return None
    return state.get("queue_class") or state.get("talkroom_state") or None


def scan(snapshot_path: Path, projects_root: Path, ledger_path: Path) -> dict:
    summary: dict[str, Any] = {
        "snapshot": str(snapshot_path),
        "scanned_orders": 0,
        "scanned_messages": 0,
        "appended": 0,
        "skipped_existing": 0,
        "errors": 0,
    }
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        summary["error"] = f"{type(exc).__name__}:{exc}"
        return summary

    orders = snapshot.get("orders") if isinstance(snapshot, dict) else None
    if not isinstance(orders, list):
        return summary

    existing_keys = _existing_keys(ledger_path)
    new_rows: list[dict[str, Any]] = []
    now = int(time.time())

    for order in orders:
        if not isinstance(order, dict):
            continue
        summary["scanned_orders"] += 1
        talkroom_id = str(order.get("talkroom_id") or "")
        if not talkroom_id:
            continue
        project_id = str(order.get("request_id") or talkroom_id)
        messages = order.get("buyer_recent_messages")
        if not isinstance(messages, list):
            continue
        phase = order.get("talkroom_state") or _project_phase(projects_root, project_id)
        for message in messages:
            try:
                if not isinstance(message, dict):
                    continue
                summary["scanned_messages"] += 1
                text = str(message.get("text") or "")
                if not text:
                    continue
                key = _dedupe_key(talkroom_id, text)
                if key in existing_keys:
                    summary["skipped_existing"] += 1
                    continue
                existing_keys.add(key)  # same message never appended twice within one run
                attachments = message.get("attachments")
                new_rows.append({
                    "ts": now,
                    "talkroom_id": talkroom_id,
                    "project_id": project_id,
                    "text": text,
                    "attachments_count": len(attachments) if isinstance(attachments, list) else 0,
                    "phase": phase,
                    "reaction": None,
                })
            except Exception as exc:  # noqa: BLE001 -- one bad message must not stop the scan
                summary["errors"] += 1
                print(f"buyer_outcome_ledger: skipping message in {talkroom_id}: {exc}", file=sys.stderr)
                continue

    if new_rows:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as handle:
            for row in new_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary["appended"] = len(new_rows)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_root = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
    parser.add_argument(
        "--evidence-dir", type=Path, default=None,
        help="pass evidence dir holding marketplace-snapshot.json; default = freshest under --evidence-root",
    )
    parser.add_argument(
        "--evidence-root", type=Path,
        default=Path(os.environ.get("GIG_EVIDENCE_ROOT", str(default_root / "evidence"))),
    )
    parser.add_argument(
        "--projects-root", type=Path,
        default=Path(os.environ.get("GIG_PROJECTS_ROOT", str(default_root / "projects"))),
    )
    parser.add_argument(
        "--ledger", type=Path,
        default=Path(os.environ.get("GIG_BUYER_OUTCOMES_LEDGER", str(default_root / "buyer-outcomes.jsonl"))),
    )
    args = parser.parse_args(argv)

    evidence_dir = args.evidence_dir or _freshest_evidence_dir(args.evidence_root)
    if evidence_dir is None:
        print(json.dumps({
            "snapshot": None, "scanned_orders": 0, "scanned_messages": 0,
            "appended": 0, "skipped_existing": 0, "errors": 0,
            "error": "no_evidence_dir_with_snapshot_found",
        }, ensure_ascii=False))
        return 0

    summary = scan(evidence_dir / "marketplace-snapshot.json", args.projects_root, args.ledger)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
