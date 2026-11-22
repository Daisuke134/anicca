#!/usr/bin/env python3
"""Aggregate repeated annotated stage runs without pretending to verify real audio."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from validate_stage_dialogue import validate as validate_dialogue

CONDITION_FIELDS = (
    "stage_id", "model_id", "model_version", "skill_blob_sha",
    "script_blob_sha", "input_profile", "audio_profile", "source_type",
)
SOURCE_TYPES = {"synthetic", "audio_annotated"}
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def _nonempty(record: dict, field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value


def audit(data: dict) -> dict:
    """Check transcript gates separately for each declared protocol and provenance."""
    if not isinstance(data, dict):
        raise ValueError("input must be an object")
    experiment_id = _nonempty(data, "experiment_id")
    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("runs must be a nonempty list")

    seen_ids: set[str] = set()
    groups: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    item_results: list[dict] = []

    for idx, run in enumerate(runs):
        if not isinstance(run, dict):
            raise ValueError(f"runs[{idx}] must be an object")
        run_id = _nonempty(run, "run_id")
        if run_id in seen_ids:
            raise ValueError(f"duplicate run_id: {run_id}")
        seen_ids.add(run_id)

        conditions = tuple(_nonempty(run, key) for key in CONDITION_FIELDS)
        attributes = dict(zip(CONDITION_FIELDS, conditions))
        if attributes["source_type"] not in SOURCE_TYPES:
            raise ValueError(f"{run_id}: unsupported source_type")
        for key in ("skill_blob_sha", "script_blob_sha"):
            if not GIT_SHA.fullmatch(attributes[key]):
                raise ValueError(f"{run_id}: {key} must be a 40-digit Git SHA")
        evidence = run.get("recording_ref")
        if attributes["source_type"] == "audio_annotated":
            if not isinstance(evidence, str) or not evidence.strip():
                raise ValueError(f"{run_id}: audio_annotated requires recording_ref")
            _nonempty(run, "annotator_id")
        elif evidence is not None:
            raise ValueError(f"{run_id}: synthetic runs must not claim recording_ref")

        result = validate_dialogue(run.get("events"))
        item = {
            "run_id": run_id, "source_type": attributes["source_type"],
            "gate": result["gate"], "violations": result["violations"],
            "audio_verified_by_tool": False,
            "laughter": "NOT_MEASURED",
            "phone_ai_comprehension": "NOT_MEASURED",
            "rear_intelligibility": "NOT_MEASURED",
        }
        groups[conditions].append(item)
        item_results.append(item)

    summaries = []
    for signature, items in sorted(groups.items()):
        declared = dict(zip(CONDITION_FIELDS, signature))
        passed = sum(item["gate"] == "PASS" for item in items)
        source = declared["source_type"]
        summaries.append({
            "conditions": declared,
            "total": len(items),
            "passed": passed,
            "failed": len(items) - passed,
            "gate_pass_fraction": passed / len(items),
            "evidence_level": (
                "SYNTHETIC_FIXTURE_ONLY" if source == "synthetic"
                else "SELF_REPORTED_AUDIO_ANNOTATIONS_NOT_AUDIO_VERIFIED"
            ),
            "run_ids": [item["run_id"] for item in items],
        })

    homogeneous = len(groups) == 1 and len(runs) >= 2
    has_audio_annotations = any(run["source_type"] == "audio_annotated" for run in item_results)
    return {
        "experiment_id": experiment_id,
        "trial_count": len(runs),
        "condition_group_count": len(groups),
        "repeatability_comparison": (
            "SAME_DECLARED_CONDITIONS_ONLY" if homogeneous else "NOT_COMPARABLE"
        ),
        "voice_reproducibility": (
            "AUDIO_ANNOTATION_ONLY_NOT_VERIFIED" if has_audio_annotations
            else "NOT_MEASURED"
        ),
        "cross_model_comparison": "NOT_RUN",
        "runs": item_results,
        "groups": summaries,
        "limitations": (
            "Metadata and annotated text are self-reported. This script never listens to "
            "recordings, verifies speaker identity, measures loudness, or scores laughter. "
            "Trial independence and identical real-world conditions are not established."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        report = audit(json.loads(args.input.read_text(encoding="utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"stage audit: {report['trial_count']} runs, "
          f"{report['condition_group_count']} declared condition groups, "
          f"{report['repeatability_comparison']}")
    if args.strict and (
        report["repeatability_comparison"] != "SAME_DECLARED_CONDITIONS_ONLY"
        or any(item["gate"] != "PASS" for item in report["runs"])
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
