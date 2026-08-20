#!/usr/bin/env python3
"""Stop a gig lane before it can allocate work when disk headroom is low."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Sequence


REQUIRED_KIB = 1_048_576
REQUIRED_BYTES = REQUIRED_KIB * 1024
RECEIPT_PATH = Path("state") / "disk-headroom.json"


def _state_dir() -> Path:
    return Path(os.environ.get("GIG_STATE_DIR") or (Path.home() / "gig"))


def _fsync_directory(directory: Path) -> None:
    """Flush the directory entry after replacing a receipt, then close the fd."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_fd = os.open(str(directory), flags)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _write_receipt(state_dir: Path, receipt: dict[str, object]) -> str:
    """Atomically replace the lane-wide headroom receipt and return its JSON."""
    destination = state_dir / RECEIPT_PATH
    payload = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    temporary: Path | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=".disk-headroom.", suffix=".tmp", dir=destination.parent,
        )
        temporary = Path(temporary_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        temporary = None
        _fsync_directory(destination.parent)
    except Exception as exc:  # The guard still fails closed if receipt storage is unavailable.
        print(f"gig_disk_guard: could not persist receipt: {exc}", file=sys.stderr)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    return payload


def _failure(reason: str, available_bytes: int | None) -> int:
    receipt: dict[str, object] = {
        "status": "failed",
        "failed": 1,
        "effect": 0,
        "readback": 0,
        "reason": reason,
        "required_bytes": REQUIRED_BYTES,
    }
    if available_bytes is not None:
        receipt["available_bytes"] = available_bytes
    payload = _write_receipt(_state_dir(), receipt)
    print(payload)
    return 1


def disk_headroom_ok() -> bool:
    """Return whether the gig state filesystem has the required free bytes."""
    try:
        available_bytes = int(shutil.disk_usage(_state_dir()).free)
    except Exception:
        _failure("disk_headroom_unavailable", None)
        return False
    if available_bytes < REQUIRED_BYTES:
        _failure("disk_headroom_low", available_bytes)
        return False
    return True


def main(argv: Sequence[str] | None = None) -> int:
    remaining = list(sys.argv[1:] if argv is None else argv)
    if not remaining:
        print("gig_disk_guard: missing child argv", file=sys.stderr)
        return 2

    if not disk_headroom_ok():
        return 1

    os.execvpe(remaining[0], remaining, os.environ)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
