#!/usr/bin/env python3
"""Feed unfinished publisher observations into the Writer Agent repair queue."""

from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import writer_incident_queue as incidents  # noqa: E402
import writer_observability_slo as observability  # noqa: E402


def bridge(*, state_root: Path, run_id: str, observed_at: str) -> dict[str, Any]:
    state_root = state_root.resolve()
    control_dir = state_root / "self-heal"
    control_dir.mkdir(parents=True, exist_ok=True)
    manifest = control_dir / f"replay-{run_id}.manifest.json"
    manifest.write_text(
        json.dumps({
            "schema": "writer.observability.replay-cases",
            "version": 1,
            "cases": [{
                "execution_id": f"publisher-repair:{run_id}",
                "run_id": run_id,
                "checkpoint": "gates/publication-state.json",
            }],
        }),
        encoding="utf-8",
    )
    replay = observability.replay(manifest, state_root, observed_at)
    destination_work = [
        row for row in replay["slo_work"]
        if str(row.get("phase", "")).startswith("destination:")
    ]
    replay = {**replay, "slo_work": destination_work,
              "slo_work_count": len(destination_work)}
    replay_path = control_dir / f"replay-{run_id}.json"
    observability._atomic(replay_path, replay)  # pylint: disable=protected-access

    queue_path = control_dir / "incident-queue.json"
    lock_path = control_dir / ".incident-queue.json.lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        queue = incidents._read(queue_path)  # pylint: disable=protected-access
        incidents.ingest(queue, replay, observed_at)
        incidents._atomic(queue_path, queue)  # pylint: disable=protected-access
    return {"run_id": run_id, "enqueued": len(destination_work),
            "queue": str(queue_path), "replay": str(replay_path)}


def bridge_all(*, state_root: Path, observed_at: str) -> dict[str, Any]:
    state_root = state_root.resolve()
    results = []
    skipped = []
    for path in sorted(state_root.glob("runs/*/gates/publication-state.json")):
        run_id = path.parents[1].name
        try:
            results.append(bridge(state_root=state_root, run_id=run_id,
                                  observed_at=observed_at))
        except (OSError, ValueError, RuntimeError, observability.TraceError,
                json.JSONDecodeError) as exc:
            skipped.append({"run_id": run_id, "reason": str(exc)})
    return {"runs": len(results),
            "enqueued": sum(row["enqueued"] for row in results),
            "results": results, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--observed-at", required=True)
    args = parser.parse_args()
    result = (
        bridge(state_root=args.state_root, run_id=args.run_id,
               observed_at=args.observed_at)
        if args.run_id
        else bridge_all(state_root=args.state_root, observed_at=args.observed_at)
    )
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
