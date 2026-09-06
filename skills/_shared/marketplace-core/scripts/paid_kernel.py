#!/usr/bin/env python3
"""Provider-neutral Paid wake orchestration.

The model-facing ``decide`` callback owns job judgment.  The kernel owns only
identity, durable intent, effect fencing, official reconciliation and receipts.
Provider adapters own observation, mutation and official readback mechanics.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Mapping, Protocol


MUTATIONS = frozenset({"answer", "submit", "formal_delivery", "cancel"})


class PaidAdapter(Protocol):
    def observe_active(self) -> list[dict[str, Any]]: ...
    def observe_one(self, work_id: str) -> dict[str, Any]: ...
    def mutate(self, intent: dict[str, Any]) -> None: ...
    def readback(self, intent: dict[str, Any]) -> dict[str, Any]: ...


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_invalid")
    return value.strip()


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _item_key(row: Mapping[str, Any]) -> str:
    identity = ":".join(_text(row.get(field), field) for field in ("provider", "account_id", "work_id"))
    return hashlib.sha256(identity.encode()).hexdigest()


def _state_path(root: Path, row: Mapping[str, Any]) -> Path:
    return root / "items" / _item_key(row) / "state.json"


@contextmanager
def _item_lock(path: Path):
    lock_path = path.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        os.chmod(lock_path, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("paid_state_invalid")
    return value


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=".state-", delete=False,
                                         encoding="utf-8") as handle:
            temporary = handle.name
            os.fchmod(handle.fileno(), 0o600)
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def _observation(row: Mapping[str, Any]) -> dict[str, Any]:
    required = ("provider", "account_id", "work_id", "latest_event_id", "provider_state", "observed_at")
    return {field: _text(row.get(field), field) for field in required}


def _intent(row: Mapping[str, Any], decision: Mapping[str, Any]) -> dict[str, Any]:
    action = _text(decision.get("action"), "action")
    if action not in MUTATIONS:
        raise ValueError("paid_action_invalid")
    payload = decision.get("payload")
    if not isinstance(payload, Mapping) or not payload:
        raise ValueError("paid_payload_invalid")
    content_sha256 = _digest(payload)
    base = {
        "version": 1,
        "provider": row["provider"],
        "account_id": row["account_id"],
        "work_id": row["work_id"],
        "latest_event_id": row["latest_event_id"],
        "action": action,
        "payload": dict(payload),
        "content_sha256": content_sha256,
    }
    return {**base, "effect_key": _digest(base)}


def _verified_receipt(intent: Mapping[str, Any], readback: Mapping[str, Any]) -> dict[str, Any]:
    if readback.get("verified") is not True:
        raise ValueError("official_readback_unverified")
    return {
        "version": 1,
        "effect_key": intent["effect_key"],
        "provider_receipt_id": _text(readback.get("provider_receipt_id"), "provider_receipt_id"),
        "observed_at": _text(readback.get("observed_at"), "observed_at"),
    }


def _pending(row: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {"work_id": row["work_id"], "status": "pending", "reason": reason,
            "effect": 0, "readback": 0, "failed": 0}


def _run_one_locked(adapter: PaidAdapter, decide: Callable[[dict[str, Any]], Mapping[str, Any]],
                    state_root: Path, source: Mapping[str, Any]) -> dict[str, Any]:
    row = _observation(source)
    path = _state_path(state_root, row)
    state = _load(path)
    previous_intent = state.get("intent")
    if isinstance(previous_intent, Mapping):
        official = adapter.readback(dict(previous_intent))
        if official.get("verified") is True:
            receipt = _verified_receipt(previous_intent, official)
            _write(path, {"version": 1, "observation": row, "intent": previous_intent,
                          "receipt": receipt, "status": "verified"})
            return {"work_id": row["work_id"], "status": "verified", "reason": "replay_zero",
                    "effect": 0, "readback": 1, "failed": 0}
        if official.get("authoritative_absent") is not True:
            return _pending(row, "reconcile_unknown")

    decision = decide(dict(row))
    if not isinstance(decision, Mapping):
        raise ValueError("paid_decision_invalid")
    action = _text(decision.get("action"), "action")
    if action == "noop":
        _write(path, {"version": 1, "observation": row, "status": "noop"})
        return {"work_id": row["work_id"], "status": "noop", "reason": "no_effect_required",
                "effect": 0, "readback": 1, "failed": 0}
    if action == "wait":
        reason = _text(decision.get("reason"), "reason")
        remaining = decision.get("remaining_work")
        if not isinstance(remaining, list) or not remaining or not all(isinstance(v, str) and v.strip() for v in remaining):
            raise ValueError("remaining_work_invalid")
        _write(path, {"version": 1, "observation": row, "status": "waiting_external",
                      "blocker": reason, "remaining_work": remaining})
        return _pending(row, reason)

    intent = _intent(row, decision)
    _write(path, {"version": 1, "observation": row, "intent": intent,
                  "status": "intent_persisted"})
    current = _observation(adapter.observe_one(row["work_id"]))
    if current["latest_event_id"] != row["latest_event_id"]:
        _write(path, {"version": 1, "observation": current, "status": "context_stale"})
        return _pending(row, "newer_provider_event")
    existing = adapter.readback(intent)
    if existing.get("verified") is True:
        receipt = _verified_receipt(intent, existing)
        _write(path, {"version": 1, "observation": current, "intent": intent,
                      "receipt": receipt, "status": "verified"})
        return {"work_id": row["work_id"], "status": "verified", "reason": "reconciled",
                "effect": 0, "readback": 1, "failed": 0}
    adapter.mutate(intent)
    official = adapter.readback(intent)
    if official.get("verified") is not True:
        _write(path, {"version": 1, "observation": current, "intent": intent,
                      "status": "reconcile_unknown"})
        return {"work_id": row["work_id"], "status": "pending", "reason": "reconcile_unknown",
                "effect": 1, "readback": 0, "failed": 0}
    receipt = _verified_receipt(intent, official)
    _write(path, {"version": 1, "observation": current, "intent": intent,
                  "receipt": receipt, "status": "verified"})
    return {"work_id": row["work_id"], "status": "verified", "reason": "submitted",
            "effect": 1, "readback": 1, "failed": 0}


def _run_one(adapter: PaidAdapter, decide: Callable[[dict[str, Any]], Mapping[str, Any]],
             state_root: Path, source: Mapping[str, Any]) -> dict[str, Any]:
    row = _observation(source)
    with _item_lock(_state_path(state_root, row)):
        return _run_one_locked(adapter, decide, state_root, row)


def run_wake(*, adapter: PaidAdapter, decide: Callable[[dict[str, Any]], Mapping[str, Any]],
             state_root: Path, max_workers: int = 4) -> dict[str, Any]:
    rows = adapter.observe_active()
    if not isinstance(rows, list):
        raise ValueError("paid_inventory_invalid")
    normalized = [_observation(row) for row in rows]
    identities = [(row["provider"], row["account_id"], row["work_id"]) for row in normalized]
    if len(identities) != len(set(identities)):
        raise ValueError("paid_inventory_duplicate")
    workers = max(1, min(max_workers, len(normalized) or 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_one, adapter, decide, Path(state_root), row) for row in normalized]
        items = [future.result() for future in futures]
    return {
        "status": "ok",
        "observed": len(items),
        "effect": sum(item["effect"] for item in items),
        "readback": sum(item["readback"] for item in items),
        "failed": sum(item["failed"] for item in items),
        "pending": sum(item["status"] == "pending" for item in items),
        "items": items,
    }
