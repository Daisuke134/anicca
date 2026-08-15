#!/usr/bin/env python3
"""Compute the B2 runner budget without crossing the next hourly wake."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def plan(
    *,
    pass_start: int,
    now: int,
    wall_limit: int,
    finalize_reserve: int,
    min_invocation: int,
) -> dict[str, Any]:
    values = (pass_start, now, wall_limit, finalize_reserve, min_invocation)
    if any(isinstance(value, bool) for value in values):
        raise ValueError("boolean_time_value")
    if pass_start < 0 or now < 0:
        raise ValueError("epoch_must_be_nonnegative")
    if wall_limit < 1 or finalize_reserve < 1 or min_invocation < 1:
        raise ValueError("duration_must_be_positive")
    if finalize_reserve >= wall_limit:
        raise ValueError("finalize_reserve_must_be_below_wall_limit")

    deadline_epoch = pass_start + wall_limit - finalize_reserve
    remaining = max(0, deadline_epoch - now)
    can_start = remaining >= min_invocation
    return {
        "version": 1,
        "pass_start_epoch": pass_start,
        "observed_at_epoch": now,
        "wall_limit_seconds": wall_limit,
        "finalize_reserve_seconds": finalize_reserve,
        "min_invocation_seconds": min_invocation,
        "deadline_epoch": deadline_epoch,
        "remaining_seconds": remaining,
        "can_start": can_start,
        "runner_timeout_seconds": remaining if can_start else 0,
        "reason": "within_deadline" if can_start else "next_hour_deadline",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--pass-start", type=int, required=True)
    plan_parser.add_argument("--now", type=int, required=True)
    plan_parser.add_argument("--wall-limit", type=int, required=True)
    plan_parser.add_argument("--finalize-reserve", type=int, required=True)
    plan_parser.add_argument("--min-invocation", type=int, required=True)
    plan_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = plan(
            pass_start=args.pass_start,
            now=args.now,
            wall_limit=args.wall_limit,
            finalize_reserve=args.finalize_reserve,
            min_invocation=args.min_invocation,
        )
    except ValueError as error:
        print(json.dumps({"ok": False, "error": str(error)}, separators=(",", ":")))
        return 2
    _atomic_write(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0 if payload["can_start"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
