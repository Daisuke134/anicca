#!/usr/bin/env python3
"""Prune terminal article runs while never deleting a deferred Zenn queue item."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


PROTECTED = {"waiting", "pending", "live-recorded"}


def is_protected(run_dir: Path) -> bool:
    generation = run_dir / "gates/generation-state.json"
    # ponytail: retain every generation state; narrow only when archive growth
    # is measured and a durable external archive proof can authorize deletion.
    if generation.exists() or generation.is_symlink():
        return True
    # A duplicate-media quarantine is the durable proof that its repair queue
    # items must never be retried.  Retention may not delete that proof while
    # the queue still points at the run.
    quarantine = run_dir / "gates/run-quarantine.json"
    if quarantine.is_file() and not quarantine.is_symlink():
        return True
    # A non-terminal quality receipt is owned by the same-run recovery worker.
    # Retention must not erase the drafts and evidence before that worker can
    # apply its bounded revision or publish decision.
    quality = run_dir / "gates/quality-self-heal.json"
    if quality.is_file() and not quality.is_symlink():
        try:
            value = json.loads(quality.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return True
        if not isinstance(value, dict) or value.get("action") not in {"complete", "closed"}:
            return True
    artifact = run_dir / "gates/zenn-deferred.json"
    if not artifact.is_file():
        return False
    try:
        value = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    return not isinstance(value, dict) or value.get("status") in PROTECTED


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", required=True, type=Path)
    parser.add_argument("--keep", type=int, default=30)
    args = parser.parse_args()
    if args.keep < 1:
        parser.error("--keep must be positive")
    if not args.runs_root.is_dir():
        return 0

    runs = sorted(path for path in args.runs_root.iterdir() if path.is_dir())
    protected = {path for path in runs if is_protected(path)}
    terminal = [path for path in runs if path not in protected]
    terminal_slots = max(0, args.keep - len(protected))
    delete = terminal[:-terminal_slots] if terminal_slots else terminal
    for path in delete:
        shutil.rmtree(path)
    print(json.dumps({
        "before": len(runs),
        "after": len(runs) - len(delete),
        "protected": len(protected),
        "deleted": [path.name for path in delete],
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
