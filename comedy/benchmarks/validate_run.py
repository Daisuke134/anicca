#!/usr/bin/env python3
"""Deterministic, offline gate checks for Comedy Agent runs (not a humor judge)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED = ("run_id", "task_id", "model", "skill_version", "skill_commit", "response")


def jsonl(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{lineno}: expected a JSON object")
        result.append(value)
    return result


def score(task: dict[str, Any], response: str) -> list[str]:
    """Return objective violations, without claiming to measure funniness."""
    issues: list[str] = []
    if task.get("kind") == "silence":
        if response.strip():
            issues.append("expected_silence")
        return issues

    if not response.strip():
        issues.append("empty_response")

    expected_prefix = task.get("expected_prefix")
    if expected_prefix and not response.strip().startswith(expected_prefix):
        issues.append("opening_or_script_prefix_mismatch")

    options = task.get("any_of", [])
    if options and not any(word in response for word in options):
        issues.append("missing_required_world_anchor")

    for phrase in task.get("forbidden", []):
        if phrase in response:
            issues.append(f"forbidden_phrase:{phrase}")
    max_chars = task.get("max_chars")
    if max_chars is not None:
        if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars <= 0:
            raise ValueError("max_chars must be a positive integer when specified")
        if len(response) > max_chars:
            issues.append("exceeds_max_chars")
    return issues


def run(tasks_path: Path, responses_path: Path) -> dict[str, Any]:
    tasks = jsonl(tasks_path)
    submissions = jsonl(responses_path)
    task_index: dict[str, dict[str, Any]] = {}
    for task in tasks:
        key = task.get("id")
        if not isinstance(key, str) or not key or key in task_index:
            raise ValueError("Task IDs must be unique nonempty strings")
        task_index[key] = task

    entries: list[dict[str, Any]] = []
    by_run: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"submitted": 0, "passed": 0, "failed": 0, "task_ids": []}
    )
    seen: set[tuple[str, str, str]] = set()

    for submission in submissions:
        missing = [field for field in REQUIRED if field not in submission]
        if missing:
            raise ValueError(f"Response record missing fields: {missing}")
        if not isinstance(submission["response"], str):
            raise ValueError("Response must be a string (even when empty)")
        task_id = submission["task_id"]
        if task_id not in task_index:
            raise ValueError(f"Unknown task_id {task_id!r}")
        group = (str(submission["run_id"]), str(submission["model"]))
        key = (group[0], group[1], str(task_id))
        if key in seen:
            raise ValueError(f"Duplicate run/model/task entry: {key}")
        seen.add(key)
        errors = score(task_index[task_id], submission["response"])
        item = {
            "run_id": group[0],
            "model": group[1],
            "task_id": task_id,
            "category": task_index[task_id].get("category"),
            "kind": task_index[task_id].get("kind"),
            "gate": "FAIL" if errors else "PASS",
            "reasons": errors,
            "funniness": "NOT_MEASURED",
        }
        entries.append(item)
        row = by_run[group]
        row["submitted"] += 1
        row["task_ids"].append(task_id)
        row["failed" if errors else "passed"] += 1

    summaries: list[dict[str, Any]] = []
    for (run_id, model), row in sorted(by_run.items()):
        summaries.append({
            "run_id": run_id,
            "model": model,
            "submitted": row["submitted"],
            "passed": row["passed"],
            "failed": row["failed"],
            "missing_tasks": sorted(set(task_index) - set(row["task_ids"])),
            "humor_score": "NOT_MEASURED",
        })
    return {
        "schema_version": "1.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "taskset": str(tasks_path),
        "responses": str(responses_path),
        "task_count": len(tasks),
        "run_summary": summaries,
        "items": entries,
        "warning": "This checks literal cues, response format, forbidden phrases, and anchors; it DOES NOT measure how funny an output is.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    base = Path(__file__).resolve().parent
    parser.add_argument("--tasks", type=Path, default=base / "taskset-v1.jsonl")
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any failed hard gate")
    args = parser.parse_args()
    try:
        report = run(args.tasks, args.responses)
    except (ValueError, FileNotFoundError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Checked {len(report['items'])} responses from "
        f"{len(report['run_summary'])} run/model groups -> {args.output}"
    )
    for row in report["run_summary"]:
        print(f"{row['run_id']} / {row['model']}: passed={row['passed']} failed={row['failed']} missing={len(row['missing_tasks'])}")
    if args.strict and any(item["gate"] == "FAIL" for item in report["items"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
