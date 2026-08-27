"""Durable keep/revert controller around one bounded learning slice."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    _atomic_write_bytes(path, encoded)


def run_learning_controller(
    *,
    cycle_id: str,
    cycle: Callable[..., dict[str, Any]],
    cycle_kwargs: dict[str, Any],
    canary: dict[str, Any],
    receipt_path: Path,
    active_version_path: Path | None = None,
) -> dict[str, Any]:
    """Run one change, canary it, and durably record final weight state."""

    if not cycle_id:
        raise ValueError("cycle_id is required")
    weights_path = Path(cycle_kwargs["weights_path"])
    before = weights_path.read_bytes()
    before_hash = _hash(before)

    decision = cycle(**cycle_kwargs)
    candidate = weights_path.read_bytes()
    candidate_hash = _hash(candidate)
    if canary.get("status") not in {"pass", "fail"}:
        raise ValueError("canary status must be pass or fail")

    status = decision["status"]
    reason = decision["reason"]
    if status == "keep" and canary["status"] != "pass":
        _atomic_write_bytes(weights_path, before)
        status = "revert"
        reason = "canary_failed"

    after = weights_path.read_bytes()
    receipt = {
        "cycle_id": cycle_id,
        "slice": decision["slice"],
        "opponent": decision["opponent"],
        "reward": decision["reward"],
        "weight_file": decision["weight_file"],
        "status": status,
        "reason": reason,
        "changed_rules": decision["changed_rules"] if status == "keep" else [],
        "before_hash": before_hash,
        "candidate_hash": candidate_hash,
        "after_hash": _hash(after),
        "held_out": decision.get("held_out"),
        "canary": canary,
        "promotion_status": (
            "active"
            if status == "keep" and active_version_path is not None
            else "not_promoted"
        ),
    }
    _atomic_write_json(Path(receipt_path), receipt)
    if status == "keep" and active_version_path is not None:
        _atomic_write_json(
            Path(active_version_path),
            {
                "version_id": receipt["after_hash"],
                "status": "active",
                "learning_cycle_id": cycle_id,
                "slice": decision["slice"],
                "weight_file": weights_path.as_posix(),
                "weight_hash": receipt["after_hash"],
            },
        )
    return receipt


def consume_weights(
    *,
    run_id: str,
    weights_path: Path,
    learning_receipt_path: Path,
    consumption_receipt_path: Path,
    active_version_path: Path | None = None,
) -> dict[str, Any]:
    """Prove the next generation run consumed the promoted weight hash."""

    learning = json.loads(
        Path(learning_receipt_path).read_text(encoding="utf-8")
    )
    if learning.get("status") != "keep":
        raise ValueError("only a kept learning cycle can be consumed")
    consumed_hash = _hash(Path(weights_path).read_bytes())
    if consumed_hash != learning.get("after_hash"):
        raise ValueError("consumed weight hash differs from promoted hash")
    active_version_id = learning["after_hash"]
    if active_version_path is not None:
        active = json.loads(
            Path(active_version_path).read_text(encoding="utf-8")
        )
        if (
            active.get("status") != "active"
            or active.get("learning_cycle_id") != learning.get("cycle_id")
            or active.get("weight_hash") != consumed_hash
            or active.get("version_id") != consumed_hash
        ):
            raise ValueError("active strategy version differs from kept cycle")
        active_version_id = active["version_id"]

    receipt = {
        "run_id": run_id,
        "learning_cycle_id": learning["cycle_id"],
        "slice": learning["slice"],
        "weight_file": Path(weights_path).as_posix(),
        "consumed_hash": consumed_hash,
        "active_version_id": active_version_id,
    }
    _atomic_write_json(Path(consumption_receipt_path), receipt)
    return receipt
