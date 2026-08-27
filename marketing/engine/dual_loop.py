"""Shared mutation boundary for reconciliation and strategy optimization."""

from __future__ import annotations

import hashlib
import json
from typing import Any


_RECONCILE_MUTATIONS = [
    "adapter_action",
    "checkpoint_state",
    "retry_schedule",
]
_STRATEGY_PREFIXES = (
    "strategy.demo.",
    "strategy.rule.",
    "strategy.weight.",
)


def _differences(
    desired: dict[str, Any],
    actual: dict[str, Any],
    *,
    prefix: str = "",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(set(desired) | set(actual)):
        path = f"{prefix}.{key}" if prefix else key
        wanted = desired.get(key)
        observed = actual.get(key)
        if isinstance(wanted, dict) and isinstance(observed, dict):
            rows.extend(_differences(wanted, observed, prefix=path))
        elif wanted != observed:
            rows.append(
                {
                    "path": path,
                    "desired": wanted,
                    "actual": observed,
                }
            )
    return rows


def reconcile(
    *,
    reconciliation_id: str,
    desired_state: dict[str, Any],
    actual_state: dict[str, Any],
) -> dict[str, Any]:
    """Compare actual state with a fixed identity and desired state."""

    if not reconciliation_id:
        raise ValueError("reconciliation_id is required")
    for field in ("scope", "identity"):
        if not isinstance(desired_state.get(field), dict):
            raise ValueError(f"desired state {field} is required")
        if actual_state.get(field) != desired_state[field]:
            raise ValueError(f"actual state {field} must match desired state")

    differences = _differences(desired_state, actual_state)
    return {
        "reconciliation_id": reconciliation_id,
        "scope": desired_state["scope"],
        "identity": desired_state["identity"],
        "desired_state": desired_state,
        "actual_state": actual_state,
        "status": "action_required" if differences else "converged",
        "differences": differences,
        "allowed_mutations": list(_RECONCILE_MUTATIONS),
    }


def authorize_optimization(
    *,
    reconciliation_receipt: dict[str, Any],
    reward_receipt: dict[str, Any],
    requested_mutations: list[str],
) -> dict[str, Any]:
    """Authorize one strategy-only candidate after terminal, scorable evidence."""

    if reconciliation_receipt.get("status") != "converged":
        raise ValueError("optimizer requires converged actual state")
    if reward_receipt.get("status") != "scorable":
        raise ValueError("optimizer requires scorable reward")
    if len(requested_mutations) != 1:
        raise ValueError("optimizer requires exactly one mutation")
    if not all(
        isinstance(mutation, str)
        and mutation.startswith(_STRATEGY_PREFIXES)
        for mutation in requested_mutations
    ):
        raise ValueError("optimizer mutation is outside strategy boundary")

    material = json.dumps(
        {
            "reconciliation_id": reconciliation_receipt.get(
                "reconciliation_id"
            ),
            "reward_id": reward_receipt.get("reward_id"),
            "mutations": requested_mutations,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    version_id = hashlib.sha256(material).hexdigest()
    return {
        "status": "authorized",
        "reward": reward_receipt,
        "allowed_mutations": list(requested_mutations),
        "candidate_version": {
            "version_id": version_id,
            "scope": reward_receipt.get("scope"),
            "status": "candidate",
            "reward_id": reward_receipt.get("reward_id"),
            "mutations": list(requested_mutations),
        },
    }
