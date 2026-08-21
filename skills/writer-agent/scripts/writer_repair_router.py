#!/usr/bin/env python3
"""Route a claimed Writer incident to a versioned runbook or UNKNOWN investigation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _read(path: Path, schema: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != schema or value.get("version") != 1:
        raise ValueError(f"unsupported {schema}")
    return value


def _matches(item: dict[str, Any], match: dict[str, str]) -> bool:
    return all(str(item.get(key)) == value for key, value in match.items())


def _run_id(item: dict[str, Any]) -> str:
    # The incident's own `run_id` is the recorded identity of the run.  An
    # execution id is a worker label: `publisher-repair:daily-2026-08-07` names
    # the repair executor for run `daily-2026-08-07`, and stripping only
    # `publisher-` yields the non-existent run `repair:daily-2026-08-07`.
    # Parsing stays as a fallback for incidents recorded before `run_id`.
    recorded = str(item.get("run_id") or "")
    if recorded:
        return recorded
    occurrences = item.get("occurrences")
    if not isinstance(occurrences, list) or not occurrences:
        raise ValueError("incident has no occurrence")
    execution_id = str(occurrences[-1].get("execution_id") or "")
    if execution_id.startswith("publisher-"):
        return execution_id.removeprefix("publisher-")
    source = occurrences[-1].get("source_receipt")
    if isinstance(source, dict):
        path = str(source.get("path") or "")
        parts = Path(path).parts
        if "runs" in parts:
            index = parts.index("runs")
            if index + 1 < len(parts):
                return parts[index + 1]
    for occurrence in reversed(occurrences):
        execution = str(occurrence.get("execution_id") or "")
        if execution.startswith("publication-"):
            return execution.removeprefix("publication-")
    raise ValueError("incident occurrence does not identify a run")


def route(
    queue: dict[str, Any], registry: dict[str, Any], fingerprint: str,
    state_dir: Path, scripts: Path,
) -> dict[str, Any]:
    item = queue.get("items", {}).get(fingerprint)
    if not isinstance(item, dict):
        raise ValueError("unknown incident fingerprint")
    if item.get("state") != "CLAIMED":
        raise ValueError("incident must be CLAIMED before routing")
    candidates = [
        runbook for runbook in registry.get("runbooks", [])
        if isinstance(runbook, dict)
        and isinstance(runbook.get("match"), dict)
        and _matches(item, runbook["match"])
    ]
    if candidates:
        candidates.sort(key=lambda row: (-len(row["match"]), str(row["runbook_id"])))
        selected = candidates[0]
        run_id = _run_id(item)
        run_dir = state_dir / "runs" / run_id
        if not run_dir.is_dir():
            raise ValueError(f"run directory does not exist: {run_id}")
        replacements = {
            "{state_dir}": str(state_dir),
            "{run_dir}": str(run_dir),
            "{scripts}": str(scripts),
        }
        command = []
        for argument in selected["command"]:
            rendered = str(argument)
            for source, target in replacements.items():
                rendered = rendered.replace(source, target)
            command.append(rendered)
        return {
            "route": "KNOWN",
            "fingerprint": fingerprint,
            "runbook_id": selected["runbook_id"],
            "runbook_version": selected["version"],
            "mode": selected["mode"],
            "command": command,
            "command_sha256": hashlib.sha256("\0".join(command).encode()).hexdigest(),
            "next_action": "EXECUTE_BOUNDED_RUNBOOK",
        }
    return {
        "route": "UNKNOWN",
        "fingerprint": fingerprint,
        "classification": item.get("classification"),
        "next_action": "COLLECT_LAST_GOOD_FIRST_BAD_AND_PRIMARY_DOCS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--fingerprint", required=True)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--scripts", required=True, type=Path)
    args = parser.parse_args()
    queue = _read(args.queue, "writer.self-heal.incident-queue")
    registry = _read(args.registry, "writer.self-heal.runbooks")
    value = route(
        queue, registry, args.fingerprint,
        args.state_dir.resolve(), args.scripts.resolve(),
    )
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
