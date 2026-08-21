"""Shared local resource guard for Affiliate owners."""

import shutil
from datetime import datetime, timezone

from provider_cli import atomic_write


RUNTIME_DISK_FLOOR_BYTES = None


def runtime_guard(state_root, floor_bytes=RUNTIME_DISK_FLOOR_BYTES):
    """Read and persist the disk floor without hiding read-only health state."""
    try:
        free_bytes = shutil.disk_usage(state_root).free
        guard_state = "CLEAR" if floor_bytes is None or free_bytes >= floor_bytes else "DISK_GUARD_BLOCKED"
        failure_type = None
    except OSError:
        free_bytes = None
        guard_state = "DISK_GUARD_UNKNOWN"
        failure_type = "DISK_USAGE_UNAVAILABLE"
    receipt = {
        "schema_version": 1,
        "receipt_type": "AFFILIATE_RUNTIME_GUARD",
        "guard": "disk",
        "state": guard_state,
        "free_bytes": free_bytes,
        "floor_bytes": floor_bytes,
        "failure_type": failure_type,
        "receipt_persist_state": "PERSISTED",
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        atomic_write(state_root / "runtime-guard.json", receipt)
    except OSError:
        # A full volume must not turn a read-only health/ledger wake into an
        # untyped crash; the in-memory result remains redacted and truthful.
        receipt["receipt_persist_state"] = "PERSIST_FAILED"
    return receipt
