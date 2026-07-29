#!/usr/bin/env python3
"""Sync project state.json from the authoritative talkroom observation.

Why: state.json drifts from the real screen whenever something happens outside the
step that owns it -- a human sends the delivery by hand, a pass dies mid-step, or a
later observation supersedes an earlier decision. Measured on 2026-07-27 for the live
40,000 JPY order: state.json said formal_delivery=False and was 9.5 hours old, while
the newest talkroom snapshot said formal_delivery_confirmed=true and
transaction_state=納品確認待ち. A loop that plans from a stale state re-does delivered
work or asks the buyer for what it already has -- the exact behaviour that cost trust
on this account.

Direction of trust: the live talkroom DOM wins over our own notes. Fields only move
toward what was actually observed.

Safety rules, deliberate:
  * evidence-backed truths are never downgraded -- once a delivery has been seen as
    confirmed, a later snapshot that lacks the field does not flip it back to False.
    Only an explicit False observation can lower it.
  * writes are atomic (tmp + os.replace, per the checkpoint pattern in
    anthropics/defending-code-reference-harness) so a kill mid-write cannot leave a
    truncated state.json that breaks the next pass.
  * every change is appended to events.jsonl with before/after and the evidence file,
    so a human can audit what moved and why.
  * unknown/extra keys in state.json are preserved untouched.

Usage:
  state_reconciler.py --project 17943244
  state_reconciler.py --all [--dry-run]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

STATE_DIR = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
PROJECTS = STATE_DIR / "projects"
EVIDENCE = STATE_DIR / "evidence"

# snapshot field -> state field. Booleans here are "sticky true": a truth that has
# been observed once is not silently withdrawn by a snapshot that omits it.
STICKY_BOOL = {
    "formal_delivery_confirmed": "formal_delivery",
    "buyer_visible_artifact_observed": "buyer_visible",
    # agreement is a fact about something the buyer did; a later snapshot that no
    # longer surfaces it must not erase it.
    "buyer_agreement_observed": "buyer_agreement_observed",
}
# plain mirrors: always take the newest observation
MIRROR = {
    "transaction_state": "transaction_state",
    # genuinely transient: it resets each time we ship a new artifact.
    "buyer_reply_after_artifact_observed": "buyer_reply_after_artifact_observed",
}


def is_settled(talkroom_id: str) -> bool:
    """True once revenue for this room is in the append-only earnings ledger."""
    ledger = STATE_DIR / "earnings.jsonl"
    if not ledger.exists():
        return False
    with ledger.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(row.get("talkroom_id") or "") == str(talkroom_id):
                return True
    return False


def newest_snapshot(talkroom_id: str) -> Path | None:
    files = glob.glob(str(EVIDENCE / "*" / "live-dom" / f"talkroom-{talkroom_id}.json"))
    if not files:
        return None
    return Path(max(files, key=os.path.getmtime))


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _atomic_write(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)  # rename is atomic: no torn state.json after a kill


def reconcile_one(project_dir: Path, dry_run: bool = False) -> dict:
    state_path = project_dir / "state.json"
    state = _load(state_path)
    if state is None:
        return {"project": project_dir.name, "status": "no_state"}

    talkroom = str(state.get("talkroom_id") or "")
    if not talkroom:
        return {"project": project_dir.name, "status": "no_talkroom_id"}

    if is_settled(talkroom):
        # Closed rooms stop being observed on purpose, so their newest snapshot is
        # frozen at close time. Reconciling from it would drag a finished project
        # backwards -- measured: it tried to flip Fkimura's buyer_agreement_observed
        # true -> false from a snapshot two days stale. Settled means done.
        return {"project": project_dir.name, "status": "settled_skip", "changed": 0}

    snap_path = newest_snapshot(talkroom)
    if snap_path is None:
        return {"project": project_dir.name, "status": "no_snapshot"}
    snap = _load(snap_path)
    if snap is None:
        return {"project": project_dir.name, "status": "unreadable_snapshot"}

    # Never let an observation older than our own notes overwrite them.
    state_updated = float(state.get("updated_at") or 0)
    if os.path.getmtime(snap_path) <= state_updated:
        return {
            "project": project_dir.name,
            "status": "state_newer_than_snapshot",
            "changed": 0,
        }

    changes = {}
    for src, dst in STICKY_BOOL.items():
        if src not in snap:
            continue
        observed, current = snap[src], state.get(dst)
        if observed is None or observed == current:
            continue
        if current is True and observed is not False:
            continue  # never withdraw a confirmed truth on a vague signal
        changes[dst] = {"from": current, "to": observed}

    for src, dst in MIRROR.items():
        if src not in snap:
            continue
        observed = snap[src]
        if observed is not None and state.get(dst) != observed:
            changes[dst] = {"from": state.get(dst), "to": observed}

    observed_at = snap.get("observed_at")
    if observed_at and state.get("observed_at") != observed_at:
        changes["observed_at"] = {"from": state.get("observed_at"), "to": observed_at}

    result = {
        "project": project_dir.name,
        "status": "ok",
        "talkroom_id": talkroom,
        "snapshot": str(snap_path),
        "changes": changes,
        "changed": len(changes),
    }
    if not changes or dry_run:
        return result

    for field, delta in changes.items():
        state[field] = delta["to"]
    state["updated_at"] = time.time()
    state["reconciled_from"] = str(snap_path)
    _atomic_write(state_path, state)

    event = {
        "ts": time.time(),
        "event": "state_reconciled",
        "request_id": project_dir.name,
        "talkroom_id": talkroom,
        "evidence": str(snap_path),
        "changes": changes,
    }
    with (project_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        handle.flush()
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.project:
        targets = [PROJECTS / args.project]
    elif args.all:
        targets = sorted(p for p in PROJECTS.glob("*") if (p / "state.json").exists())
    else:
        ap.error("need --project or --all")

    results = [reconcile_one(t, dry_run=args.dry_run) for t in targets]
    print(
        json.dumps(
            {
                "status": "ok",
                "dry_run": args.dry_run,
                "projects": len(results),
                "changed": sum(r.get("changed", 0) for r in results),
                "results": results,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
