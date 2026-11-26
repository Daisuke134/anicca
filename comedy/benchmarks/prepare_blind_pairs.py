#!/usr/bin/env python3
"""Prepare counterbalanced, offline A/B review packets; do not score humor."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from validate_run import jsonl, score

SET_TYPE = "original_development_not_fixed_benchmark"
RIGHTS = "original_internal_draft"


def prepare(tasks: list[dict], responses: list[dict], seed: str) -> dict:
    """Two variants show each answer on both sides, to separate position from quality.

    Variants must be shown to DIFFERENT raters; a rater seeing both is unblinded.
    """
    if not isinstance(seed, str) or not seed.strip():
        raise ValueError("seed must be a nonempty string")
    tasks_by_id = {}
    for task in tasks:
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id or task_id in tasks_by_id:
            raise ValueError("task id must be unique and nonempty")
        if task.get("set_type") != SET_TYPE or task.get("rights") != RIGHTS:
            raise ValueError(f"{task_id}: only rights-cleared original development tasks")
        if not isinstance(task.get("prompt"), str) or not task["prompt"].strip():
            raise ValueError(f"{task_id}: missing prompt")
        tasks_by_id[task_id] = task
    if not tasks_by_id:
        raise ValueError("at least one task required")

    pairs = defaultdict(dict)
    for row in responses:
        task_id = row.get("task_id")
        idx = row.get("sample_index")
        if task_id not in tasks_by_id:
            raise ValueError(f"unknown task_id: {task_id}")
        if type(idx) is not int or idx not in (1, 2):
            raise ValueError(f"{task_id}: sample_index must be 1 or 2")
        if idx in pairs[task_id]:
            raise ValueError(f"{task_id}: duplicate candidate index {idx}")
        answer = row.get("response")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f"{task_id}: empty answer")
        failures = score(tasks_by_id[task_id], answer)
        if failures:
            raise ValueError(f"{task_id}/{idx}: hard gate FAIL: {failures}")
        if not isinstance(row.get("skill_blob_sha"), str) or not re.fullmatch(r"[0-9a-f]{40}", row["skill_blob_sha"]):
            raise ValueError(f"{task_id}/{idx}: missing Skill blob SHA")
        pairs[task_id][idx] = row
    if set(pairs) != set(tasks_by_id) or any(set(pairs[k]) != {1, 2} for k in tasks_by_id):
        raise ValueError("each task must have exactly two candidate responses")

    # Reproducibly shuffle task order; assign candidate 1 to A for half the tasks.
    # This prevents one candidate stream always occupying the first position.
    task_ids = sorted(tasks_by_id, key=lambda k: hashlib.sha256(
        (seed + "|" + k).encode("utf-8")).hexdigest())
    packets = {"v1": [], "v2": []}
    for i, task_id in enumerate(task_ids):
        one, two = pairs[task_id][1], pairs[task_id][2]
        if one["skill_blob_sha"] != two["skill_blob_sha"]:
            raise ValueError(f"{task_id}: unequal Skill SHA")
        if one["response"] == two["response"]:
            raise ValueError(f"{task_id}: identical candidate text")
        task = tasks_by_id[task_id]
        first, second = (one, two) if i % 2 == 0 else (two, one)
        for variant, left, right in (
            ("v1", first, second), ("v2", second, first)
        ):
            packets[variant].append({
                "pair_id": task_id,
                "category": task.get("category"),
                "prompt": task["prompt"],
                "A": left["response"],
                "B": right["response"],
                "rating": {
                    "preferred": "NOT_MEASURED",
                    "allowed": ["A", "B", "TIE"],
                    "reason": "NOT_MEASURED",
                },
            })
    balance = {variant: Counter(
        "sample_1" if item["A"] == pairs[item["pair_id"]][1]["response"] else "sample_2"
        for item in items
    ) for variant, items in packets.items()}
    return {
        "schema": "offline_counterbalanced_review_v1",
        "task_set": SET_TYPE,
        "pairs": len(task_ids),
        "candidate_count": 2 * len(task_ids),
        "variants": packets,
        "position_balance": {k: dict(v) for k, v in balance.items()},
        "review_status": "NOT_MEASURED",
        "human_judgments": 0,
        "model_comparison": "NOT_ESTABLISHED",
        "constraints": [
            "Show each rater only ONE variant; never show both A/B orders to one rater.",
            "The packet hides model metadata, but publicly stored raw answers can reveal origin.",
            "Mechanical hard-gate pass and A/B position balance are NOT humor measurements.",
            "Human laughter, Voice timing, rear audibility, and phone-AI comprehension: NOT_MEASURED.",
            "No external publishing, posting, automatic replies, or contest submission.",
        ],
        "publish_enabled": False,
        "auto_reply_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", required=True, type=Path)
    parser.add_argument("--responses", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", required=True)
    args = parser.parse_args()
    try:
        report = prepare(jsonl(args.tasks), jsonl(args.responses), args.seed)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Prepared {report['pairs']} pairs x 2 orders; human ratings NOT_MEASURED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
