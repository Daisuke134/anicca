#!/usr/bin/env python3
"""Wrap one immutable Writer receipt in a versioned observability event."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any


class EventError(ValueError):
    """The receipt cannot be represented without weakening its authority."""


def _timestamp(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if parsed.tzinfo is not None else None


def _latency_ms(started_at: str | None, finished_at: str | None) -> int | None:
    if started_at is None or finished_at is None:
        return None
    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    return max(0, round((finished - started).total_seconds() * 1000))


def _release_commit(run_dir: Path) -> str | None:
    path = run_dir / "git-hash.txt"
    if path.is_symlink() or not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("harness_git_hash="):
            value = line.partition("=")[2].strip()
            return value or None
    return None


def wrap_receipt(
    *, run_dir: Path, receipt_path: Path, phase: str, observed_at: str
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    if not run_dir.is_dir():
        raise EventError("run directory is missing")
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise EventError("receipt must be a regular file")
    receipt = receipt_path.resolve()
    try:
        relative = receipt.relative_to(run_dir)
    except ValueError as exc:
        raise EventError("receipt is outside run directory") from exc
    source = receipt.read_bytes()
    try:
        payload = json.loads(source)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise EventError("receipt is not a JSON object") from exc
    if not isinstance(payload, dict):
        raise EventError("receipt is not a JSON object")
    if payload.get("run_id") not in {None, run_dir.name}:
        raise EventError("receipt run_id does not match run directory")
    if _timestamp(observed_at) is None:
        raise EventError("observed_at must be timezone-aware ISO-8601")
    source_sha256 = hashlib.sha256(source).hexdigest()
    event_identity = f"{run_dir.name}\0{relative}\0{source_sha256}".encode()
    signal = payload
    attempts = payload.get("attempts")
    if (
        phase == "generation"
        and isinstance(attempts, list)
        and attempts
        and isinstance(attempts[-1], dict)
    ):
        signal = attempts[-1]
    outcome_field = next(
        (
            key
            for key in ("action", "status", "verdict", "state")
            if isinstance(signal.get(key), str)
        ),
        None,
    )
    started_at = _timestamp(signal.get("started_at"))
    finished_at = _timestamp(signal.get("finished_at"))
    return {
        "schema": "writer.observability.event",
        "version": 1,
        "event_id": hashlib.sha256(event_identity).hexdigest(),
        "run_id": run_dir.name,
        "phase": phase,
        "artifact_id": payload.get("artifact_id"),
        "language": payload.get("lang") or payload.get("language"),
        "destination": payload.get("platform") or payload.get("destination"),
        "article_sha256": payload.get("article_sha256"),
        "strategy_sha256": payload.get("strategy_sha256"),
        "release_commit": payload.get("release_commit") or _release_commit(run_dir),
        "attempt": signal.get("attempt"),
        "started_at": started_at,
        "finished_at": finished_at,
        "latency_ms": _latency_ms(started_at, finished_at),
        "outcome": (
            {"field": outcome_field, "value": signal[outcome_field]}
            if outcome_field is not None
            else None
        ),
        "reason": payload.get("reason"),
        "cost": payload.get("cost"),
        "observed_at": observed_at,
        "source_receipt": {
            "path": str(relative),
            "sha256": source_sha256,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    wrap = subparsers.add_parser("wrap")
    wrap.add_argument("--run-dir", required=True, type=Path)
    wrap.add_argument("--receipt", required=True, type=Path)
    wrap.add_argument("--phase", required=True)
    wrap.add_argument("--observed-at", required=True)
    args = parser.parse_args()
    try:
        event = wrap_receipt(
            run_dir=args.run_dir,
            receipt_path=args.receipt,
            phase=args.phase,
            observed_at=args.observed_at,
        )
    except EventError as exc:
        parser.error(str(exc))
    print(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
