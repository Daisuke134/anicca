#!/usr/bin/env python3
"""Audit whether Comedy AI model inputs are comparable; NEVER score humor or voice."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
SETTINGS = ("modality", "temperature", "effort", "max_output_tokens")


def valid_controlled_settings(row: dict) -> bool:
    """Check metadata shape, not whether the provider truly honored the controls."""
    t = row.get("temperature")
    n = row.get("max_output_tokens")
    return (isinstance(row.get("modality"), str) and bool(row["modality"].strip())
            and isinstance(row.get("effort"), str) and bool(row["effort"].strip())
            and type(t) in (int, float) and math.isfinite(t) and 0 <= t <= 2
            and type(n) is int and n > 0)


def read_jsonl(path: Path) -> list[dict]:
    records = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}:{lineno}: malformed JSON") from e
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{lineno}: expected object")
        records.append(record)
    return records


def audit(tasks_path: Path, responses_path: Path) -> dict:
    tasks = read_jsonl(tasks_path)
    responses = read_jsonl(responses_path)
    task_ids = [row.get("id") for row in tasks]
    task_by_id = {row.get("id"): row for row in tasks}
    if not task_ids or any(not isinstance(x, str) or not x for x in task_ids) or len(set(task_ids)) != len(task_ids):
        raise ValueError("task IDs must be distinct nonempty strings")
    reasons = set()
    groups = defaultdict(list)
    seen = set()
    receipts = set()
    for row in responses:
        for key in ("task_id", "model", "run_id", "response", "sample_index"):
            if key not in row:
                raise ValueError(f"missing required response field: {key}")
        if row["task_id"] not in task_by_id or not isinstance(row["response"], str):
            raise ValueError("unknown task or non-string response")
        # A provider receipt cannot compensate for a missing creative answer.
        # Silence is the *correct* answer only for explicit silence tasks.
        if task_by_id[row["task_id"]].get("kind") == "silence":
            if row["response"].strip():
                reasons.add("unexpected_silence_response")
        elif not row["response"].strip():
            reasons.add("empty_non_silence_response")
        if not isinstance(row["model"], str) or not row["model"].strip():
            raise ValueError("invalid model name")
        if type(row["sample_index"]) is not int or row["sample_index"] < 1:
            raise ValueError("sample_index must be a positive integer")
        key = (row["model"], row["task_id"], row["sample_index"])
        if key in seen:
            reasons.add("duplicate_model_task_sample")
        seen.add(key)
        groups[row["model"]].append(row)
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in ("model_version", "skill_commit", "skill_blob_sha")) or "NOT_AVAILABLE" in str(row.get("model_version")):
            reasons.add("missing_version_or_skill_sha")
        elif not SHA.fullmatch(row["skill_commit"]) or not SHA.fullmatch(row["skill_blob_sha"]):
            reasons.add("invalid_skill_sha")
        if any(k not in row or row.get(k) is None or str(row.get(k)).startswith("NOT_") for k in SETTINGS):
            reasons.add("missing_generation_setting")
        if not valid_controlled_settings(row):
            reasons.add("invalid_generation_setting")
        if row.get("invocation_source") != "provider_api":
            reasons.add("no_verified_independent_invocation")
        receipt = row.get("provider_receipt")
        if not isinstance(receipt, str) or not receipt.strip():
            reasons.add("missing_provider_receipt")
        elif receipt in receipts:
            reasons.add("duplicate_provider_receipt")
        else:
            receipts.add(receipt)
    if len(groups) < 2:
        reasons.add("fewer_than_two_models")
    per_model = {}
    for model, items in sorted(groups.items()):
        # Equal coverage *across* models is not enough: both models can have
        # the same accidental missing repeat in one task and pass pairwise checks.
        by_task = {task: set() for task in task_ids}
        for r in items:
            by_task[r["task_id"]].add(r["sample_index"])
        if len({len(indices) for indices in by_task.values()}) != 1:
            reasons.add("uneven_task_sample_counts")
        for indices in by_task.values():
            if indices and indices != set(range(1, max(indices) + 1)):
                reasons.add("noncontiguous_sample_indices")
        coverage = {(r["task_id"], r["sample_index"]) for r in items}
        per_model[model] = {
            "responses": len(items), "unique_task_samples": len(coverage),
            "task_count": len({r["task_id"] for r in items}),
            "independent_api_receipts": sum(r.get("invocation_source") == "provider_api"
                                            and bool(r.get("provider_receipt")) for r in items),
        }
    if groups:
        all_keys = [set((r["task_id"], r["sample_index"]) for r in items) for items in groups.values()]
        if any(s != all_keys[0] for s in all_keys[1:]):
            reasons.add("unequal_task_sample_coverage")
        if any({task for task, sample in s} != set(task_ids) for s in all_keys):
            reasons.add("incomplete_task_coverage")
        versions = {(r.get("model"), r.get("model_version")) for r in responses}
        if len(versions) != len(groups):
            reasons.add("multiple_versions_within_model")
        if len({(r.get("skill_commit"), r.get("skill_blob_sha")) for r in responses}) > 1:
            reasons.add("skill_version_mismatch")
        if len({json.dumps({k: r.get(k) for k in SETTINGS}, sort_keys=True, ensure_ascii=False)
                for r in responses}) > 1:
            reasons.add("generation_settings_mismatch")
    else:
        reasons.add("no_submissions")
    return {
        "schema_version": "1.0",
        "taskset_sha256": hashlib.sha256(tasks_path.read_bytes()).hexdigest(),
        "response_count": len(responses),
        "models": per_model,
        "comparison_setup": "NOT_COMPARABLE" if reasons else "COMPARISON_INPUTS_AUDITED",
        "reasons": sorted(reasons),
        "humor_quality": "NOT_MEASURED",
        "voice_reproducibility": "NOT_MEASURED",
        "receipt_authenticity": "NOT_VERIFIED",
        "warning": "Metadata consistency only. Receipt strings are not authenticated; no performance ranking.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.tasks, args.responses)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    print(result["comparison_setup"] + ": " + ",".join(result["reasons"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
