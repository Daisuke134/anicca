#!/usr/bin/env python3
"""Durable write-ahead envelope for Affiliate external effects."""

import fcntl
import hashlib
import json
import os
import tempfile
import time
import uuid
from pathlib import Path


class JobStateError(Exception):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def reject_secrets(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if any(word in str(key).lower() for word in ("password", "secret", "token", "credential")):
                raise JobStateError("job journal refuses secret-bearing fields")
            reject_secrets(item)
    elif isinstance(value, list):
        for item in value:
            reject_secrets(item)


def atomic_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(canonical(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def append(path, value):
    with path.open("a", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        stream.write(canonical(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def start_effect(state, kind, target, action, last_verified, cooldown_seconds):
    reject_secrets(action)
    reject_secrets(last_verified)
    state = state.expanduser()
    jobs = state / "jobs"
    jobs.mkdir(mode=0o700, parents=True, exist_ok=True)
    action_fingerprint = hashlib.sha256(canonical(action).encode()).hexdigest()
    job_key = hashlib.sha256(f"{kind}\0{target}\0{action_fingerprint}".encode()).hexdigest()
    lock_path = jobs / ".lock"
    with lock_path.open("a+") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        index_path = jobs / f"key-{job_key}.json"
        previous = json.loads(index_path.read_text()) if index_path.is_file() else None
        if previous and previous.get("state") == "EFFECT_STARTED":
            raise JobStateError("unresolved external effect requires reconciliation")
        sequence = int(previous.get("sequence", 0)) + 1 if previous else 1
        job_id = hashlib.sha256(f"{job_key}\0{sequence}".encode()).hexdigest()
        now = int(time.time())
        row = {
            "schema_version": 1,
            "receipt_type": "AFFILIATE_EXTERNAL_JOB",
            "run_id": str(uuid.uuid4()),
            "job_id": job_id,
            "job_key": job_key,
            "kind": kind,
            "target": target,
            "state": "EFFECT_STARTED",
            "attempt": 1,
            "sequence": sequence,
            "action_fingerprint": action_fingerprint,
            "cooldown": {"seconds": int(cooldown_seconds), "until": None},
            "last_verified_external_object": last_verified,
            "updated_at": now,
        }
        atomic_json(jobs / f"{job_id}.json", row)
        atomic_json(index_path, row)
        append(state / "job-events.jsonl", row)
        return row


def verify_effect(state, job_id, external_object):
    reject_secrets(external_object)
    state = state.expanduser()
    jobs = state / "jobs"
    path = jobs / f"{job_id}.json"
    lock_path = jobs / ".lock"
    with lock_path.open("a+") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        row = json.loads(path.read_text())
        if row.get("state") != "EFFECT_STARTED":
            raise JobStateError("job is not awaiting external verification")
        row.update(
            state="VERIFIED",
            last_verified_external_object=external_object,
            updated_at=int(time.time()),
        )
        atomic_json(path, row)
        atomic_json(jobs / f"key-{row['job_key']}.json", row)
        append(state / "job-events.jsonl", row)
        return row


def resume_effect(state, kind, target):
    """Resume exactly one unresolved effect without changing its identity."""
    state = state.expanduser()
    jobs = state / "jobs"
    if not jobs.is_dir():
        return None
    lock_path = jobs / ".lock"
    with lock_path.open("a+") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        unresolved = []
        for path in jobs.glob("key-*.json"):
            row = json.loads(path.read_text())
            if row.get("state") == "EFFECT_STARTED" and row.get("kind") == kind and row.get("target") == target:
                unresolved.append((path, row))
        if not unresolved:
            return None
        if len(unresolved) != 1:
            raise JobStateError("multiple unresolved effects require quarantine")
        index_path, row = unresolved[0]
        row.update(attempt=int(row["attempt"]) + 1, resumed=True, updated_at=int(time.time()))
        atomic_json(jobs / f"{row['job_id']}.json", row)
        atomic_json(index_path, row)
        append(state / "job-events.jsonl", row)
        return row


def unresolved_effect(state, kind, target):
    """Read exactly one unresolved effect without changing attempts or timestamps."""
    state = state.expanduser()
    jobs = state / "jobs"
    if not jobs.is_dir():
        return None
    lock_path = jobs / ".lock"
    with lock_path.open("a+") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = []
        for path in jobs.glob("key-*.json"):
            row = json.loads(path.read_text())
            if row.get("state") == "EFFECT_STARTED" and row.get("kind") == kind and row.get("target") == target:
                rows.append(row)
        if len(rows) > 1:
            raise JobStateError("multiple unresolved effects require quarantine")
        return rows[0] if rows else None


def reconcile_effect(state, kind, target, external_object):
    """Complete the one unresolved target after a fresh semantic readback."""
    reject_secrets(external_object)
    state = state.expanduser()
    jobs = state / "jobs"
    if not jobs.is_dir():
        return None
    lock_path = jobs / ".lock"
    with lock_path.open("a+") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        unresolved = []
        for path in jobs.glob("key-*.json"):
            row = json.loads(path.read_text())
            if row.get("state") == "EFFECT_STARTED" and row.get("kind") == kind and row.get("target") == target:
                unresolved.append((path, row))
        if not unresolved:
            return None
        if len(unresolved) != 1:
            raise JobStateError("multiple unresolved effects require quarantine")
        index_path, row = unresolved[0]
        row.update(
            state="VERIFIED",
            attempt=int(row["attempt"]) + 1,
            resumed=True,
            last_verified_external_object=external_object,
            updated_at=int(time.time()),
        )
        atomic_json(jobs / f"{row['job_id']}.json", row)
        atomic_json(index_path, row)
        append(state / "job-events.jsonl", row)
        return row
