"""Shared bounded learning mechanics for independently rewarded slices."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _read_weights(path: Path) -> dict[str, float]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        raise ValueError("slice weights must be a non-empty object")
    if any(not isinstance(value, (int, float)) for value in raw.values()):
        raise ValueError("slice weights must be numeric")
    return {str(key): float(value) for key, value in raw.items()}


def _atomic_write(path: Path, payload: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def run_bounded_cycle(
    *,
    slice_name: str,
    opponent: str,
    reward_name: str,
    weight_suffix: str,
    reward_receipt: dict[str, Any],
    blame: list[dict[str, Any]],
    proposal: dict[str, Any],
    held_out_before: float,
    held_out_after: float,
    weights_path: Path,
    rule_gate: dict[str, Any],
    guardrail_failure_reason: str | None = None,
) -> dict[str, Any]:
    """Persist one blamed change only for scorable, non-regressing evidence."""

    weights_path = Path(weights_path)
    normalized = weights_path.as_posix()
    if not normalized.endswith(weight_suffix):
        raise ValueError(f"{slice_name} slice requires {weight_suffix}")
    if reward_receipt.get("reward") != reward_name:
        raise ValueError(f"{slice_name} reward must be {reward_name}")

    decision = {
        "slice": slice_name,
        "opponent": opponent,
        "reward": reward_name,
        "weight_file": normalized,
        "changed_rules": [],
    }
    current = _read_weights(weights_path)

    if rule_gate.get("learning_change_allowed") is not True:
        return {
            **decision,
            "status": "no_change",
            "reason": "critical_rule_conflict",
        }
    if reward_receipt.get("status") != "scorable":
        return {
            **decision,
            "status": "no_change",
            "reason": "reward_not_scorable",
        }
    if guardrail_failure_reason is not None:
        return {
            **decision,
            "status": "revert",
            "reason": guardrail_failure_reason,
        }
    if not isinstance(proposal, dict) or set(proposal) != {"rule_id", "delta"}:
        raise ValueError("a learning cycle requires exactly one proposed change")

    rule_id = proposal["rule_id"]
    delta = proposal["delta"]
    if not isinstance(rule_id, str) or not isinstance(delta, (int, float)):
        raise ValueError("a slice change requires rule_id and numeric delta")
    blamed_rules = {
        row.get("rule_id")
        for row in blame
        if isinstance(row, dict) and row.get("losses", 0) > 0
    }
    if rule_id not in blamed_rules:
        raise ValueError("proposed slice rule was not blamed")
    if rule_id not in current:
        raise ValueError("proposed slice rule is absent from slice weights")

    held_out = {"before": held_out_before, "after": held_out_after}
    if held_out_after < held_out_before:
        return {
            **decision,
            "status": "revert",
            "reason": "held_out_regression",
            "held_out": held_out,
        }

    updated = dict(current)
    updated[rule_id] = round(updated[rule_id] + float(delta), 10)
    _atomic_write(weights_path, updated)
    return {
        **decision,
        "status": "keep",
        "reason": "held_out_non_regression",
        "changed_rules": [rule_id],
        "held_out": held_out,
    }
