#!/usr/bin/env python3
"""Deterministic timing audit of manually annotated stage turns, NOT audio recognition."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

from validate_stage_dialogue import validate as validate_text

SPEAKERS = {"dais", "ai", "audience", "staff"}
KINDS = {"speech", "laughter", "noise"}


def _optional_limit(name: str, value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer in milliseconds")
    return value


def measure(events: list[dict], *, max_reply_gap_ms: int | None = None,
            min_duration_ms: int | None = None,
            max_duration_ms: int | None = None) -> dict:
    """Measure annotated turn gaps/overlap; no default timing threshold is imposed.

    The caller supplies recording-relative start_ms/end_ms for every event.
    A negative gap indicates that AI began before Dais finished speaking.
    Gap metrics pair an AI reply only with a new Dais utterance since the last AI.
    """
    max_reply_gap_ms = _optional_limit("max_reply_gap_ms", max_reply_gap_ms)
    min_duration_ms = _optional_limit("min_duration_ms", min_duration_ms)
    max_duration_ms = _optional_limit("max_duration_ms", max_duration_ms)
    if min_duration_ms is not None and max_duration_ms is not None and min_duration_ms > max_duration_ms:
        raise ValueError("min_duration_ms must not exceed max_duration_ms")
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a nonempty list")

    # Reuse the existing stage contract (cues, first two lines, third-party flags).
    dialogue = validate_text(events)
    previous_start = -1
    stage_start = None
    stage_end = None
    active = False
    pending_dais = None
    last_ai_end = None
    reply_gaps = []
    dais_overlaps_ai = []
    violations = []

    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"events[{idx}] must be an object")
        speaker, kind, cue = event.get("speaker"), event.get("kind", "speech"), event.get("cue")
        start, end = event.get("start_ms"), event.get("end_ms")
        if speaker not in SPEAKERS or kind not in KINDS or not isinstance(event.get("text"), str):
            raise ValueError(f"events[{idx}] invalid speaker, kind or text")
        if (type(start) is not int or type(end) is not int or start < 0 or end < start):
            raise ValueError(f"events[{idx}] invalid start_ms/end_ms")
        if start < previous_start:
            raise ValueError(f"events[{idx}] timestamps must be ordered by start_ms")
        previous_start = start

        if cue == "start":
            if stage_start is None:
                stage_start, active = start, True
            pending_dais = (idx, end)
        elif cue == "end":
            if stage_end is None:
                stage_end = end
            active = False
            pending_dais = None
        elif speaker == "dais" and kind == "speech" and event["text"].strip() and active:
            pending_dais = (idx, end)

        if speaker == "dais" and kind == "speech" and last_ai_end is not None and start < last_ai_end:
            dais_overlaps_ai.append({"event": idx, "overlap_ms": min(end, last_ai_end) - start})

        if speaker == "ai" and kind == "speech" and event["text"].strip():
            if active and pending_dais is not None:
                dais_idx, dais_end = pending_dais
                gap = start - dais_end
                reply_gaps.append({"ai_event": idx, "dais_event": dais_idx, "gap_ms": gap})
                if gap < 0:
                    violations.append({"event": idx, "reason": "ai_overlaps_dais_speech", "overlap_ms": -gap})
                elif max_reply_gap_ms is not None and gap > max_reply_gap_ms:
                    violations.append({"event": idx, "reason": "reply_gap_exceeds_target", "gap_ms": gap})
            pending_dais = None
            last_ai_end = end

    duration = None if stage_start is None or stage_end is None else stage_end - stage_start
    if duration is not None and duration < 0:
        violations.append({"event": None, "reason": "negative_stage_duration"})
    if duration is not None and min_duration_ms is not None and duration < min_duration_ms:
        violations.append({"event": None, "reason": "stage_shorter_than_target", "duration_ms": duration})
    if duration is not None and max_duration_ms is not None and duration > max_duration_ms:
        violations.append({"event": None, "reason": "stage_longer_than_target", "duration_ms": duration})
    gaps = [row["gap_ms"] for row in reply_gaps]
    ordered = sorted(gaps)
    median = statistics.median(gaps) if gaps else None
    p95 = ordered[math.ceil(0.95 * len(ordered)) - 1] if gaps else None
    timing_gate = "PASS" if not violations else "FAIL"
    return {
        "gate": "PASS" if timing_gate == "PASS" and dialogue["gate"] == "PASS" else "FAIL",
        "text_gate": dialogue["gate"],
        "text_violations": dialogue["violations"],
        "timing_gate": timing_gate,
        "timing_violations": violations,
        "reply_gap_ms": reply_gaps,
        "reply_gap_median_ms": median,
        "reply_gap_p95_nearest_rank_ms": p95,
        "ai_overlap_dais_count": sum(r["reason"] == "ai_overlaps_dais_speech" for r in violations),
        "dais_overlap_ai_events": dais_overlaps_ai,
        "stage_duration_ms": duration,
        "thresholds_ms": {
            "max_reply_gap_ms": max_reply_gap_ms, "min_duration_ms": min_duration_ms,
            "max_duration_ms": max_duration_ms,
        },
        "scope": "annotated_timestamps_and_text_only",
        "raw_audio_verified": False,
        "audience_laughter": "NOT_MEASURED",
        "phone_ai_comprehension": "NOT_MEASURED",
        "voice_delivery_quality": "NOT_MEASURED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-reply-gap-ms", type=int)
    parser.add_argument("--min-duration-ms", type=int)
    parser.add_argument("--max-duration-ms", type=int)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
            raise ValueError("input must be an object containing events list")
        report = measure(
            payload["events"], max_reply_gap_ms=args.max_reply_gap_ms,
            min_duration_ms=args.min_duration_ms, max_duration_ms=args.max_duration_ms,
        )
        report["scenario_id"] = payload.get("scenario_id")
        report["input_provenance"] = payload.get("provenance", "UNDECLARED")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    print(f"{report['gate']}: text={report['text_gate']}, timing={report['timing_gate']}, paired={len(report['reply_gap_ms'])}")
    return int(args.strict and report["gate"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
