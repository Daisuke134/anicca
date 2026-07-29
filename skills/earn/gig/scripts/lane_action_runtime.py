#!/usr/bin/env python3
"""Production runtime seam that drives the four-lane LaneStateMachine.

`lane_state_machine.LaneStateMachine` owns the durable at-most-once envelope for
the listing/application/reply/delivery lanes, but on its own it has no runtime
caller.  This module is that caller and nothing more: a thin `observe -> run_once`
pass-through plus a CLI so the production pass (`gig_pass.sh`) can close each lane
in the shared ledger.  It deliberately holds no per-lane policy, registry, or
dispatch table -- the four lanes keep their own bespoke controllers; this only
connects them to the unified envelope.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable


def _load_state_machine():
    try:
        from lane_state_machine import LaneStateMachine  # type: ignore
    except ModuleNotFoundError:  # imported directly by unit-test loaders
        path = Path(__file__).with_name("lane_state_machine.py")
        spec = importlib.util.spec_from_file_location("lane_state_machine", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load lane_state_machine")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.LaneStateMachine
    return LaneStateMachine


LaneStateMachine = _load_state_machine()


def _state_dir(state_dir: Path | str | None) -> Path:
    if state_dir is not None:
        return Path(state_dir)
    return Path(os.environ.get("GIG_STATE_DIR") or (Path.home() / "gig"))


def open_state_machine(state_dir: Path | str | None = None) -> Any:
    """Open the shared lane-actions ledger under the Gig runtime state dir."""
    return LaneStateMachine(_state_dir(state_dir) / "lane-actions.sqlite3")


def run_lane_action(
    machine: Any,
    *,
    lane: str,
    event_key: str,
    entity_key: str,
    action_kind: str,
    owner: str,
    now: int,
    compose: Callable[[dict[str, Any]], str],
    execute: Callable[[dict[str, Any], str], Any],
    verify: Callable[[dict[str, Any]], Any],
    lease_seconds: int = 300,
) -> dict[str, Any]:
    """Observe one lane event, then drive it a single step through the envelope."""
    action = machine.observe(
        lane=lane,
        event_key=event_key,
        entity_key=entity_key,
        action_kind=action_kind,
        observed_at=now,
    )
    return machine.run_once(
        action_id=action["action_id"],
        owner=owner,
        now=now,
        compose=compose,
        execute=execute,
        verify=verify,
        lease_seconds=lease_seconds,
    )


def record_lane_closure(
    machine: Any,
    *,
    lane: str,
    event_key: str,
    entity_key: str,
    action_kind: str,
    owner: str,
    now: int,
    evidence_hash: str | None = None,
) -> dict[str, Any]:
    """Close one lane for a pass through the shared runtime seam.

    A ``verified_noop`` closure records that the lane was driven this pass with no
    side effect owed to the unified ledger; the lane's own controller remains the
    authority for any real customer side effect it performed.  For a concrete
    action kind, the recorded ``evidence_hash`` is the authoritative proof that
    reconciles the side effect to ``verified``.
    """
    return run_lane_action(
        machine,
        lane=lane,
        event_key=event_key,
        entity_key=entity_key,
        action_kind=action_kind,
        owner=owner,
        now=now,
        compose=lambda _action: f"{lane}:{action_kind}:{event_key}",
        execute=lambda _action, _intent: None,
        verify=lambda _action: (
            {"evidence_hash": evidence_hash} if evidence_hash else None
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record", help="record one lane closure for a pass")
    record.add_argument("--state-dir", type=Path, default=None)
    record.add_argument("--lane", required=True)
    record.add_argument("--action-kind", required=True)
    record.add_argument("--event-key", required=True)
    record.add_argument("--entity-key", required=True)
    record.add_argument("--owner", required=True)
    record.add_argument("--now", required=True, type=int)
    record.add_argument("--evidence-hash", default=None)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    machine = open_state_machine(args.state_dir)
    row = record_lane_closure(
        machine,
        lane=args.lane,
        event_key=args.event_key,
        entity_key=args.entity_key,
        action_kind=args.action_kind,
        owner=args.owner,
        now=args.now,
        evidence_hash=args.evidence_hash,
    )
    print(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
