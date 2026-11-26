#!/usr/bin/env python3
"""Offline eligibility audit for multi-model Comedy AI comparisons; never judges humor.

A complete, matching *declared* run is at most CONDITIONALLY_COMPARABLE:
provider receipts cannot be cryptographically verified by this offline tool.
"""
from __future__ import annotations

import argparse
import hashlib
from collections import defaultdict
import json
from pathlib import Path
import re
import sys

from validate_run import jsonl

SHA40 = re.compile(r"^[a-f0-9]{40}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
INDEPENDENT_SOURCES = {"independent_provider_api", "independent_connected_model_call"}
UNKNOWN = {"", "UNKNOWN", "NOT_EXPOSED", "NOT_MEASURED", "NOT_AVAILABLE", "UNVERIFIED"}


def known(value: object) -> bool:
    return (isinstance(value, (str, int, float))
            and str(value).strip() not in UNKNOWN
            and not re.search(r"(?:UNKNOWN|UNVERIFIED|NOT_EXPOSED|NOT_MEASURED)", str(value), re.I))


def audit(tasks: list[dict], responses: list[dict]) -> dict:
    """Check provenance, task coverage, declared settings; never assert actual API execution."""
    task_ids = [task.get("id") for task in tasks]
    if not task_ids or any(not isinstance(t, str) or not t for t in task_ids):
        raise ValueError("tasks require nonempty string IDs")
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("duplicate task ID")
    task_kinds = {task["id"]: task.get("kind") for task in tasks}
    # A task_id alone cannot prove that two models received identical prompts.
    # The task manifest is the local reference, but the provider input is still
    # unverified without an independently captured request/receipt.
    task_prompt_digests = {}
    missing_manifest_prompts = []
    for task in tasks:
        prompt = task.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            missing_manifest_prompts.append(task["id"])
        else:
            task_prompt_digests[task["id"]] = hashlib.sha256(
                prompt.encode("utf-8")).hexdigest()
    if any(not isinstance(row, dict) for row in responses):
        raise ValueError("each response must be an object")

    by_model: dict[str, list[dict]] = defaultdict(list)
    for row in responses:
        model = row.get("model")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("response has missing model")
        by_model[model].append(row)

    reasons = []
    if missing_manifest_prompts:
        reasons.append("MISSING_CANONICAL_TASK_PROMPT")
    if len(by_model) < 2:
        reasons.append("FEWER_THAN_TWO_EXECUTED_MODELS")

    model_rows = []
    matched_sets = []
    sha_sets = set()
    modes = set()
    settings = set()
    for model, rows in sorted(by_model.items()):
        issues = []
        pairs = set()
        for r in rows:
            task = r.get("task_id")
            candidate = r.get("candidate")
            if task not in task_ids:
                issues.append("UNKNOWN_TASK")
            else:
                claimed_digest = r.get("task_prompt_sha256")
                if not isinstance(claimed_digest, str) or not SHA256.fullmatch(claimed_digest):
                    issues.append("MISSING_TASK_PROMPT_SHA256")
                elif (task in task_prompt_digests
                      and claimed_digest != task_prompt_digests[task]):
                    issues.append("TASK_PROMPT_SHA256_MISMATCH")
            if not isinstance(candidate, str) or not candidate.strip():
                issues.append("MISSING_CANDIDATE_ID")
            pair = (task, candidate)
            if pair in pairs:
                issues.append("DUPLICATE_TASK_CANDIDATE")
            pairs.add(pair)
            response_text = r.get("response")
            if not isinstance(response_text, str):
                issues.append("MISSING_RESPONSE_TEXT")
            elif task in task_kinds:
                if task_kinds[task] == "silence" and response_text.strip():
                    issues.append("UNEXPECTED_RESPONSE_TO_SILENCE")
                elif task_kinds[task] != "silence" and not response_text.strip():
                    issues.append("EMPTY_NON_SILENCE_RESPONSE")
            if r.get("invocation_source") not in INDEPENDENT_SOURCES:
                issues.append("NO_INDEPENDENT_MODEL_INVOCATION")
            if not known(r.get("provider_receipt")):
                issues.append("NO_PROVIDER_EXECUTION_RECEIPT")
            if not known(r.get("model_version")):
                issues.append("UNKNOWN_MODEL_BUILD")
            if not SHA40.fullmatch(str(r.get("skill_blob_sha", ""))):
                issues.append("MISSING_SKILL_BLOB_SHA")
            if r.get("modality") not in ("text", "voice"):
                issues.append("UNKNOWN_MODALITY")
            if not known(r.get("temperature")) or not known(r.get("effort")):
                issues.append("UNKNOWN_INFERENCE_SETTINGS")
            if r.get("fixed_benchmark") is True and r.get("task_origin") == "NEW_ORIGINAL_INTERNAL_DEV":
                issues.append("TASK_ORIGIN_CONTRADICTION")
            if r.get("publish") is True:
                issues.append("PUBLICATION_MUST_BE_OFF")
            sha_sets.add(str(r.get("skill_blob_sha", "")))
            modes.add(r.get("modality"))
            settings.add((str(r.get("temperature")), str(r.get("effort"))))
        # Matching pair sets across models alone can hide the same omission
        # in every model. Require multiple candidates for EACH task.
        candidate_counts = {
            task_id: sum(pair_task == task_id for pair_task, _ in pairs)
            for task_id in task_ids
        }
        if any(count < 2 for count in candidate_counts.values()):
            issues.append("LESS_THAN_TWO_CANDIDATES_PER_TASK")
        if len(set(candidate_counts.values())) > 1:
            issues.append("UNEQUAL_CANDIDATES_PER_TASK")
        if len({str(r.get("model_version")) for r in rows}) != 1:
            issues.append("MIXED_MODEL_BUILDS")
        if len({str(r.get("skill_blob_sha")) for r in rows}) != 1:
            issues.append("MIXED_SKILL_BLOBS")
        if any(task not in {t for t, _ in pairs} for task in task_ids):
            issues.append("MISSING_TASKS")
        if len({str(r.get("candidate")) for r in rows}) < 2:
            issues.append("LESS_THAN_TWO_CANDIDATES")
        matched_sets.append(pairs)
        model_rows.append({
            "model": model,
            "declared_model_version": rows[0].get("model_version"),
            "responses": len(rows),
            "task_count": len({task for task, _ in pairs}),
            "candidates_per_task": candidate_counts,
            "issues": sorted(set(issues)),
            "independent_execution": "NOT_VERIFIED" if not issues else "NOT_ESTABLISHED",
        })

    if len(matched_sets) > 1 and any(pairset != matched_sets[0] for pairset in matched_sets[1:]):
        reasons.append("UNBALANCED_TASK_CANDIDATE_COVERAGE")
    if len(sha_sets) > 1:
        reasons.append("SKILL_SHA_MISMATCH")
    if len(modes) > 1:
        reasons.append("MODALITY_MISMATCH")
    if len(settings) > 1:
        reasons.append("INFERENCE_SETTINGS_MISMATCH")
    if any(m["issues"] for m in model_rows):
        reasons.append("MODEL_PROVENANCE_OR_COVERAGE_GAPS")

    conditional = not reasons
    return {
        "schema_version": "1.0",
        "comparison_eligibility": (
            "CONDITIONALLY_COMPARABLE_RECEIPTS_UNVERIFIED" if conditional else "NOT_COMPARABLE"
        ),
        "reasons": sorted(set(reasons)),
        "task_count": len(task_ids),
        "prompt_fingerprint_policy": "sha256_exact_utf8_of_manifest_prompt",
        "task_prompt_digest_coverage": len(task_prompt_digests),
        "task_prompt_digest_missing_manifest_ids": missing_manifest_prompts,
        "response_count": len(responses),
        "models": model_rows,
        "actual_provider_receipts_verified": False,
        "funniness": "NOT_MEASURED",
        "audience_laughter": "NOT_MEASURED",
        "voice_stage_reproducibility": "NOT_MEASURED",
        "publication_enabled": False,
        "auto_reply_enabled": False,
        "warning": (
            "Offline audit of self-declared metadata only. Conditional eligibility is NOT "
            "verified execution, fairness proof, a model ranking, or a humor measurement. "
            "A matching prompt SHA only verifies agreement with local self-declared "
            "metadata; the actual sent provider request and receipts remain unverified. "
            "Provider receipts and sampling settings require independent verification."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tasks", type=Path, required=True)
    p.add_argument("--responses", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()
    try:
        result = audit(jsonl(args.tasks), jsonl(args.responses))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"{result['comparison_eligibility']}: {result['response_count']} responses")
    return int(args.strict and result["comparison_eligibility"] == "NOT_COMPARABLE")


if __name__ == "__main__":
    raise SystemExit(main())
