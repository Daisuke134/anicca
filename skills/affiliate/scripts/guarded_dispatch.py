#!/usr/bin/env python3
"""Fail-closed Agent boundary around existing Affiliate command entrypoints."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from local_loop import cost_budget_snapshot, quarantine_snapshot


SKILL_ROOT = HERE.parent
REGISTRY_PATH = SKILL_ROOT / "config" / "command-registry.json"
EFFECT_OWNER = "ai.anicca.affiliate-loop"


def _commands() -> dict[str, dict]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {row["command"]: row for row in registry["commands"]}


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _external_gates(
    command: str,
    state_root: Path,
    claim_id: str,
    policy_path: Path,
    readback_command: str,
    commands: dict[str, dict],
) -> bool:
    try:
        claim_path = state_root / "jobs" / f"{claim_id}.json"
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        readback = commands[readback_command]
        quarantine = quarantine_snapshot(state_root)
        cost = cost_budget_snapshot(state_root)
        return all((
            _inside(claim_path, state_root),
            _inside(policy_path, state_root),
            claim.get("job_id") == claim_id,
            claim.get("state") == "EFFECT_STARTED",
            policy.get("decision") == "PASS",
            quarantine.get("state") == "CLEAR",
            command not in quarantine.get("tools", {}),
            cost.get("state") != "COST_CAP_BLOCKED",
            readback.get("effect_class") in {"READ_ONLY", "MONEY_RECONCILE"},
        ))
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def dispatch(
    command: str,
    *,
    caller: str,
    state_root: Path,
    claim_id: str,
    policy_path: Path,
    readback_command: str,
    operation,
) -> dict:
    """Invoke one registered command only after its authority boundary admits it."""
    commands = _commands()
    contract = commands.get(command)
    if contract is None:
        return {"state": "DISPATCH_REJECTED", "reason": "UNREGISTERED_COMMAND"}
    if contract["effect_class"] != "WRITE_EXTERNAL":
        result = operation()
        return result if isinstance(result, dict) else {"state": "INVALID_OUTPUT"}
    if caller != EFFECT_OWNER:
        return {"state": "DIRECT_EFFECT_REJECTED", "reason": "OWNER_REQUIRED"}
    if not _external_gates(
        command, state_root, claim_id, policy_path, readback_command, commands,
    ):
        return {"state": "DISPATCH_REJECTED", "reason": "GATE_REJECTED"}
    result = operation()
    if not isinstance(result, dict):
        return {"state": "POSTCONDITION_UNVERIFIED"}
    if result.get("effect_id") != claim_id or result.get("readback_status") != "EXACT":
        return {"state": "POSTCONDITION_UNVERIFIED", "effect_certainty": "UNKNOWN"}
    return result
