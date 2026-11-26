#!/usr/bin/env python3
"""Sensitivity audit of annotated stage-turn boundaries.

This is NOT a second stage PASS/FAIL gate and does not verify audio or speaker
identity. Given the JSON report from normalize_asr_turns.py, classify whether
a timing boundary judgement would survive a *hypothetical* bounded annotation
error. The caller must choose the per-endpoint error bound; none is inferred.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def classify_gap(gap_ms: int, endpoint_error_ms: int) -> dict:
    """A signed gap >= 0 is non-overlap; both endpoints may vary by +/- error."""
    if type(gap_ms) is not int:
        raise ValueError("gap_ms must be an integer")
    if type(endpoint_error_ms) is not int or endpoint_error_ms < 0:
        raise ValueError("endpoint_error_ms must be a nonnegative integer")
    low = gap_ms - 2 * endpoint_error_ms
    high = gap_ms + 2 * endpoint_error_ms
    if high < 0:
        label = "ROBUST_OVERLAP"
    elif low >= 0:
        label = "ROBUST_NONOVERLAP"
    else:
        label = "BOUNDARY_SENSITIVE"
    return {
        "nominal_gap_ms": gap_ms,
        "possible_gap_min_ms": low,
        "possible_gap_max_ms": high,
        "classification": label,
    }


def audit(report: dict, *, endpoint_error_ms: int) -> dict:
    """Audit timing robustness of an existing, independently validated ASR report."""
    if type(endpoint_error_ms) is not int or endpoint_error_ms < 0:
        raise ValueError("endpoint_error_ms must be a nonnegative integer")
    if not isinstance(report, dict):
        raise ValueError("ASR report must be a JSON object")
    timing = report.get("timing_audit")
    events = report.get("normalized_events")
    if not isinstance(timing, dict) or not isinstance(events, list):
        raise ValueError("requires timing_audit and normalized_events from ASR evaluation")
    gaps = timing.get("reply_gap_ms")
    if not isinstance(gaps, list):
        raise ValueError("timing_audit.reply_gap_ms must be a list")

    checks = []
    for i, entry in enumerate(gaps):
        if not isinstance(entry, dict) or type(entry.get("gap_ms")) is not int:
            raise ValueError(f"reply_gap_ms[{i}] must have integer gap_ms")
        checks.append({
            "kind": "ai_reply_after_dais",
            "ai_event": entry.get("ai_event"),
            "dais_event": entry.get("dais_event"),
            **classify_gap(entry["gap_ms"], endpoint_error_ms),
        })

    end_cues = []
    ai_ends = []
    for i, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"normalized_events[{i}] must be an object")
        if event.get("speaker") == "dais" and event.get("cue") == "end":
            if type(event.get("end_ms")) is not int:
                raise ValueError("end cue needs integer end_ms")
            end_cues.append(event["end_ms"])
        if event.get("speaker") == "ai" and event.get("kind", "speech") == "speech" and event.get("text", "").strip():
            if type(event.get("end_ms")) is not int:
                raise ValueError("AI speech needs integer end_ms")
            ai_ends.append(event["end_ms"])

    missing = []
    if len(end_cues) != 1:
        missing.append("exactly_one_dais_end_cue")
    if not ai_ends:
        missing.append("ai_speech")
    if not missing:
        checks.append({
            "kind": "ai_silence_at_end",
            **classify_gap(end_cues[0] - max(ai_ends), endpoint_error_ms),
        })

    labels = [c["classification"] for c in checks]
    if missing or not checks:
        overall = "NOT_ASSESSABLE"
    elif "ROBUST_OVERLAP" in labels:
        overall = "ROBUST_OVERLAP_PRESENT"
    elif "BOUNDARY_SENSITIVE" in labels:
        overall = "BOUNDARY_SENSITIVE"
    else:
        overall = "ROBUST_NONOVERLAP_FOR_TESTED_BOUNDARIES"

    return {
        "schema_version": "1.0",
        "scenario_id": report.get("scenario_id"),
        "reported_stage_gate_unchanged": report.get("gate", "UNKNOWN"),
        "endpoint_error_ms": endpoint_error_ms,
        "assumption": "independent bounded +/- error at each annotated start/end; hypothetical, NOT estimated from audio",
        "checks": checks,
        "missing": missing,
        "robustness": overall,
        "raw_audio_verified": False,
        "speaker_identity_verified": False,
        "real_world_error_bound_calibrated": False,
        "voice_reproducibility": "NOT_MEASURED",
        "phone_ai_comprehension": "NOT_MEASURED",
        "rear_intelligibility": "NOT_MEASURED",
        "audience_laughter": "NOT_MEASURED",
        "notes": "Sensitivity of literal timing boundaries only; never overrides existing hard gates.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="JSON output of normalize_asr_turns.py")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--endpoint-error-ms", type=int, required=True,
                        help="Explicit assumed error bound for EACH timestamp endpoint")
    args = parser.parse_args()
    try:
        result = audit(json.loads(args.input.read_text(encoding="utf-8")),
                       endpoint_error_ms=args.endpoint_error_ms)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    print(f"{result['robustness']}: {len(result['checks'])} boundaries, "
          f"assumed error +/-{result['endpoint_error_ms']}ms, voice=NOT_MEASURED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
