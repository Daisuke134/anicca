#!/usr/bin/env python3
"""Reconcile one fenced Gig incident against fresh observed state.

The controller never equates a successful repair command with recovery.
Recovery requires a fresh observation in which the incident fingerprint is
absent. Persistent failures are retried with bounded exponential backoff.
"""

from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


GIG_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = GIG_ROOT / "scripts"
KNOWN_REPAIR_CLASSES = frozenset(
    {
        "scheduler_restart",
        "lane_probe",
        "browser_restart",
        "disk_recover",
        "application_expand",
        "sandbox_recover",
        "ledger_reconcile",
        "telegram_reconcile",
        "telegram_probe",
    }
)
DIAGNOSTIC_REPAIR_CLASSES = frozenset(
    {
        "schema_diagnose",
        "provider_diagnose",
        "task_diagnose",
    }
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _append_audit(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        handle.flush()
        os.fsync(handle.fileno())


def _present(
    fingerprint: str,
    incidents: list[dict[str, Any]],
) -> bool:
    return any(
        isinstance(row, dict) and row.get("fingerprint") == fingerprint
        for row in incidents
    )


def _verification(
    *,
    fingerprint: str,
    incidents: list[dict[str, Any]],
    observed_at: int,
    action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value = {
        "fresh_fingerprint_present": _present(fingerprint, incidents),
        "observed_at": observed_at,
        "observed_fingerprints": sorted(
            str(row["fingerprint"])
            for row in incidents
            if isinstance(row, dict) and row.get("fingerprint")
        ),
    }
    if action is not None:
        value["repair_action"] = action
    return value


def _audit_row(
    incident: dict[str, Any],
    *,
    now: int,
    kind: str,
    state: str,
    verification: dict[str, Any],
    action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "ts": now,
        "kind": kind,
        "state": state,
        "incident_id": int(incident["incident_id"]),
        "fingerprint": str(incident["fingerprint"]),
        "repair_class": str(incident["repair_class"]),
        "fencing_token": int(incident["fencing_token"]),
        "verification": verification,
    }
    if action is not None:
        row["action"] = action
    return row


def reconcile_once(
    *,
    queue: Any,
    owner: str,
    uid: int,
    now: int,
    audit_path: Path,
    observe_incidents: Callable[[], list[dict[str, Any]]],
    dispatcher: Callable[..., dict[str, Any]],
    max_attempts: int = 3,
    lease_seconds: int = 120,
    base_backoff_seconds: int = 60,
    max_backoff_seconds: int = 3600,
) -> dict[str, Any]:
    incident = queue.claim(
        owner=owner,
        now=now,
        lease_seconds=lease_seconds,
    )
    if incident is None:
        return {"status": "queue_empty", "repair_dispatched": False}

    fingerprint = str(incident["fingerprint"])
    observed = observe_incidents()
    before = _verification(
        fingerprint=fingerprint,
        incidents=observed,
        observed_at=now,
    )
    if not before["fresh_fingerprint_present"]:
        recovered = queue.recover(
            int(incident["incident_id"]),
            owner=owner,
            fencing_token=int(incident["fencing_token"]),
            verification=before,
            recovered_at=now,
        )
        _append_audit(
            audit_path,
            _audit_row(
                incident,
                now=now,
                kind="self_heal_recovery",
                state="verified",
                verification=before,
            ),
        )
        return {
            "status": "recovered",
            "incident_id": recovered["incident_id"],
            "verification": before,
            "repair_dispatched": False,
        }

    repair_class = str(incident["repair_class"])
    if repair_class in DIAGNOSTIC_REPAIR_CLASSES:
        action = dispatcher(repair_class, uid, incident)
        verification = dict(before)
        verification["reason"] = (
            "diagnosis_recorded_requires_test_first_patch_and_canary"
        )
        verification["diagnostic_action"] = action
        blocked = queue.block(
            int(incident["incident_id"]),
            owner=owner,
            fencing_token=int(incident["fencing_token"]),
            verification=verification,
            blocked_at=now,
            action=action,
        )
        _append_audit(
            audit_path,
            _audit_row(
                incident,
                now=now,
                kind="self_heal_diagnosis",
                state="blocked",
                verification=verification,
                action=action,
            ),
        )
        return {
            "status": "diagnosed_blocked",
            "incident_id": blocked["incident_id"],
            "verification": verification,
            "repair_dispatched": False,
        }
    if repair_class not in KNOWN_REPAIR_CLASSES:
        verification = dict(before)
        verification["reason"] = "unknown_class_requires_canary_and_rollback"
        blocked = queue.block(
            int(incident["incident_id"]),
            owner=owner,
            fencing_token=int(incident["fencing_token"]),
            verification=verification,
            blocked_at=now,
        )
        _append_audit(
            audit_path,
            _audit_row(
                incident,
                now=now,
                kind="self_heal_blocked",
                state="blocked",
                verification=verification,
            ),
        )
        return {
            "status": "blocked_unknown_class",
            "incident_id": blocked["incident_id"],
            "verification": verification,
            "repair_dispatched": False,
        }

    if repair_class == "ledger_reconcile":
        action = dispatcher(repair_class, uid, incident)
    else:
        action = dispatcher(repair_class, uid)
    after_incidents = observe_incidents()
    after = _verification(
        fingerprint=fingerprint,
        incidents=after_incidents,
        observed_at=now,
        action=action,
    )
    next_attempt_count = int(incident.get("attempt_count") or 0) + 1

    if not after["fresh_fingerprint_present"]:
        recovered = queue.recover(
            int(incident["incident_id"]),
            owner=owner,
            fencing_token=int(incident["fencing_token"]),
            verification=after,
            recovered_at=now,
            action=action,
            increment_attempt=True,
        )
        _append_audit(
            audit_path,
            _audit_row(
                incident,
                now=now,
                kind="self_heal_recovery",
                state="verified",
                verification=after,
                action=action,
            ),
        )
        return {
            "status": "recovered",
            "incident_id": recovered["incident_id"],
            "verification": after,
            "repair_dispatched": True,
        }

    if next_attempt_count >= max_attempts:
        after["reason"] = "bounded_attempt_limit_reached"
        blocked = queue.block(
            int(incident["incident_id"]),
            owner=owner,
            fencing_token=int(incident["fencing_token"]),
            verification=after,
            blocked_at=now,
            action=action,
            increment_attempt=True,
        )
        _append_audit(
            audit_path,
            _audit_row(
                incident,
                now=now,
                kind="self_heal_blocked",
                state="blocked",
                verification=after,
                action=action,
            ),
        )
        return {
            "status": "blocked_attempt_limit",
            "incident_id": blocked["incident_id"],
            "verification": after,
            "repair_dispatched": True,
        }

    delay = min(
        max_backoff_seconds,
        base_backoff_seconds * (2 ** int(incident.get("attempt_count") or 0)),
    )
    deferred = queue.defer(
        int(incident["incident_id"]),
        owner=owner,
        fencing_token=int(incident["fencing_token"]),
        verification=after,
        action=action,
        next_attempt_at=now + delay,
    )
    _append_audit(
        audit_path,
        _audit_row(
            incident,
            now=now,
            kind="self_heal_attempt",
            state="repairing",
            verification=after,
            action=action,
        ),
    )
    return {
        "status": "repairing",
        "incident_id": deferred["incident_id"],
        "attempt_count": deferred["attempt_count"],
        "next_attempt_at": deferred["next_attempt_at"],
        "verification": after,
        "repair_dispatched": True,
    }


def reconcile_batch(
    *,
    queue: Any,
    owner: str,
    uid: int,
    now: int,
    audit_path: Path,
    observe_incidents: Callable[[], list[dict[str, Any]]],
    dispatcher: Callable[..., dict[str, Any]],
    max_incidents: int = 20,
    **reconcile_options: Any,
) -> dict[str, Any]:
    """Drain stale/no-side-effect incidents, allowing at most one real repair."""
    if max_incidents <= 0:
        raise ValueError("max_incidents must be positive")
    results: list[dict[str, Any]] = []
    repair_dispatched = False
    for _ in range(max_incidents):
        result = reconcile_once(
            queue=queue,
            owner=owner,
            uid=uid,
            now=now,
            audit_path=audit_path,
            observe_incidents=observe_incidents,
            dispatcher=dispatcher,
            **reconcile_options,
        )
        if result["status"] == "queue_empty":
            break
        results.append(result)
        if result.get("repair_dispatched") is True:
            repair_dispatched = True
            break
    return {
        "status": (
            "repair_dispatched" if repair_dispatched else "batch_complete"
        ),
        "processed": len(results),
        "recovered": sum(row["status"] == "recovered" for row in results),
        "blocked": sum(
            str(row["status"]).startswith("blocked") for row in results
        ),
        "repair_dispatched": repair_dispatched,
        "results": results,
    }


def main() -> int:
    home = Path.home()
    life_manager_home = Path(
        os.environ.get(
            "LIFE_MANAGER_HOME",
            os.environ.get(
                "ANICCA_HOME",
                Path(os.environ.get("XDG_STATE_HOME", home / ".local/state"))
                / "life-manager",
            ),
        )
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repair-database",
        type=Path,
        default=home / "gig" / "gig-control.sqlite3",
    )
    parser.add_argument("--state-dir", type=Path, default=home / "gig")
    parser.add_argument(
        "--host-state-dir",
        type=Path,
        default=life_manager_home / "state",
    )
    parser.add_argument(
        "--telegram-database",
        type=Path,
        default=home / "gig" / "telegram-outbox.sqlite3",
    )
    parser.add_argument("--audit", type=Path, default=home / "gig" / "audit.jsonl")
    parser.add_argument("--owner", default=f"gig-healer-{os.getpid()}")
    parser.add_argument("--uid", type=int, default=os.getuid())
    parser.add_argument("--now", type=int)
    args = parser.parse_args()

    repair_queue = _load("gig_repair_queue_runtime", SCRIPTS / "repair_queue.py")
    gig_slo = _load("gig_slo_runtime", SCRIPTS / "gig_slo.py")
    gig_healer = _load("gig_healer_runtime", SCRIPTS / "gig_healer.py")
    queue = repair_queue.RepairQueue(args.repair_database)
    observed_at = args.now if args.now is not None else int(time.time())

    def observe() -> list[dict[str, Any]]:
        snapshot = gig_slo.collect_snapshot(
            state_dir=args.state_dir,
            telegram_database=args.telegram_database,
            now=observed_at,
            host_state_dir=args.host_state_dir,
        )
        return gig_slo.evaluate(snapshot, now=observed_at)

    initial_incidents = observe()
    active_fingerprints = {
        str(row["fingerprint"])
        for row in initial_incidents
        if isinstance(row, dict) and row.get("fingerprint")
    }
    queue.requeue_resolved_blocked(
        active_fingerprints=active_fingerprints,
        now=observed_at,
    )
    result = reconcile_batch(
        queue=queue,
        owner=args.owner,
        uid=args.uid,
        now=observed_at,
        audit_path=args.audit,
        observe_incidents=observe,
        dispatcher=lambda repair_class, uid, incident=None: gig_healer.dispatch(
            repair_class, uid=uid, incident=incident
        ),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
