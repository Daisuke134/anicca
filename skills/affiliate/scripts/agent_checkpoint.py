#!/usr/bin/env python3
"""Replay-safe durable checkpoints for the persistent Affiliate Agent."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from job_journal import JobStateError, atomic_json, canonical, reject_secrets


FIELDS = {
    "goal_id", "job_id", "stage", "proposed_action", "tool_attempt",
    "observation", "effect_certainty", "next_due_at",
}
CERTAINTIES = {"NO_EFFECT", "READ_ONLY_CONFIRMED", "EFFECT_CONFIRMED", "UNKNOWN"}


def _validated(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise JobStateError("checkpoint fields do not match contract")
    if not all(isinstance(value[key], str) and value[key] for key in ("goal_id", "job_id", "stage")):
        raise JobStateError("checkpoint identity is invalid")
    if not all(isinstance(value[key], dict) for key in ("proposed_action", "tool_attempt", "observation")):
        raise JobStateError("checkpoint transition is invalid")
    if value["effect_certainty"] not in CERTAINTIES:
        raise JobStateError("checkpoint effect certainty is invalid")
    if value["next_due_at"] is not None and not isinstance(value["next_due_at"], str):
        raise JobStateError("checkpoint due time is invalid")
    reject_secrets(value)
    row = {"schema_version": 1, **value}
    row["transition_id"] = hashlib.sha256(canonical(row).encode()).hexdigest()
    return row


def _verified(row: dict) -> dict:
    if not isinstance(row, dict) or row.get("schema_version") != 1:
        raise JobStateError("checkpoint is invalid")
    transition_id = row.get("transition_id")
    payload = {key: row[key] for key in FIELDS}
    expected = _validated(payload)
    if transition_id != expected["transition_id"]:
        raise JobStateError("checkpoint transition identity mismatch")
    return row


def _history(state_root: Path) -> Path:
    return state_root / "agent-checkpoints.jsonl"


def load(state_root: Path) -> dict | None:
    path = _history(state_root)
    if not path.is_file():
        return None
    valid = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            valid.append(_verified(json.loads(line)))
        except (JobStateError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise JobStateError("checkpoint history is corrupt") from error
    return valid[-1] if valid else None


def commit(state_root: Path, checkpoint: dict) -> dict:
    row = _validated(checkpoint)
    state_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = state_root / ".agent-checkpoint.lock"
    with lock_path.open("a+") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = load(state_root)
        if previous and previous["transition_id"] == row["transition_id"]:
            return previous
        history = _history(state_root)
        with history.open("a", encoding="utf-8") as stream:
            os.chmod(history, 0o600)
            stream.write(canonical(row) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        atomic_json(state_root / "agent-checkpoint-latest.json", row)
    return row


def resume(checkpoint: dict | None) -> dict:
    if checkpoint is None:
        return {"state": "START", "replay_proposed_action": False, "transition_id": None}
    checkpoint = _verified(checkpoint)
    certainty = checkpoint["effect_certainty"]
    state = "READBACK_ONLY" if certainty == "UNKNOWN" else (
        "RETRY_WHEN_DUE" if certainty == "NO_EFFECT" else "ADVANCE"
    )
    return {
        "state": state,
        "replay_proposed_action": certainty == "NO_EFFECT",
        "transition_id": checkpoint["transition_id"],
    }
