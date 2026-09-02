"""Append-only paper effect receipts and reconciliation fence."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _rows(path: Path) -> list[dict[str, Any]]:
    try:
        values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    except FileNotFoundError:
        return []
    if not all(isinstance(value, dict) for value in values):
        raise ValueError("receipt_ledger_invalid")
    return values


def _append_once(path: Path, row: dict[str, Any], identity: tuple[str, ...]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        with os.fdopen(os.dup(descriptor), "r", encoding="utf-8") as handle:
            existing = [json.loads(line) for line in handle if line.strip()]
        if any(all(item.get(key) == row.get(key) for key in identity) for item in existing):
            return False
        payload = (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
        os.write(descriptor, payload)
        os.fsync(descriptor)
        return True
    finally:
        os.close(descriptor)


def seal(ledger: Path, decision: dict[str, Any], order: dict[str, Any]) -> dict[str, str]:
    decision_id = _digest({"paper": True, "decision": decision})
    effect_id = _digest({"decision_id": decision_id, "order": order})
    client_order_id = f"lm-ai-{effect_id[:24]}"
    now = datetime.now(timezone.utc).isoformat()
    _append_once(ledger, {
        "decision": decision, "decision_id": decision_id, "paper": True,
        "receipt_type": "decision", "recorded_at": now, "schema_version": 1,
    }, ("receipt_type", "decision_id"))
    _append_once(ledger, {
        "client_order_id": client_order_id, "decision_id": decision_id,
        "effect_id": effect_id, "order": order, "paper": True,
        "receipt_type": "effect_intent", "recorded_at": now,
        "schema_version": 1, "status": "planned",
    }, ("receipt_type", "effect_id", "status"))
    return {"client_order_id": client_order_id, "decision_id": decision_id, "effect_id": effect_id}


def record_no_trade(ledger: Path, decision: dict[str, Any]) -> str:
    decision_id = _digest({"paper": True, "decision": decision})
    _append_once(ledger, {
        "decision": decision, "decision_id": decision_id, "outcome": "no_trade",
        "paper": True, "receipt_type": "decision",
        "recorded_at": datetime.now(timezone.utc).isoformat(), "schema_version": 1,
    }, ("receipt_type", "decision_id"))
    return decision_id


def mark_started(ledger: Path, sealed: dict[str, str]) -> None:
    if any(row.get("receipt_type") == "outcome" and row.get("effect_id") == sealed["effect_id"]
           for row in _rows(ledger)):
        raise ValueError("effect_already_completed")
    _append_once(ledger, {
        **sealed, "paper": True, "receipt_type": "effect_intent",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": 1, "status": "started",
    }, ("receipt_type", "effect_id", "status"))


def reconcile_started(
    ledger: Path,
    find_order: Callable[[str], dict[str, Any] | None],
) -> dict[str, int]:
    rows = _rows(ledger)
    outcomes = {row.get("effect_id") for row in rows if row.get("receipt_type") == "outcome"}
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("receipt_type") == "effect_intent" and isinstance(row.get("effect_id"), str):
            latest[row["effect_id"]] = row
    pending = [row for effect_id, row in latest.items()
               if row.get("status") in {"started", "reconciliation_blocked"}
               and effect_id not in outcomes]
    reconciled = 0
    for intent in pending:
        order = find_order(intent["client_order_id"])
        if order is None:
            _append_once(ledger, {
                "client_order_id": intent["client_order_id"], "effect_id": intent["effect_id"],
                "paper": True, "receipt_type": "effect_intent",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "schema_version": 1, "status": "reconciliation_blocked",
            }, ("receipt_type", "effect_id", "status"))
            raise ValueError("reconciliation_blocked")
        _append_once(ledger, {
            "client_order_id": intent["client_order_id"], "effect_id": intent["effect_id"],
            "paper": True, "receipt_type": "effect_intent",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": 1, "status": "applied",
        }, ("receipt_type", "effect_id", "status"))
        _append_once(ledger, {
            "broker": order, "effect_id": intent["effect_id"], "outcome": "broker_reconciled",
            "paper": True, "receipt_type": "outcome",
            "recorded_at": datetime.now(timezone.utc).isoformat(), "schema_version": 1,
        }, ("receipt_type", "effect_id"))
        reconciled += 1
    return {"pending": len(pending), "reconciled": reconciled}
