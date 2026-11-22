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


def _merged_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Coalesce touching/overlapping labels into continuous annotated intervals."""
    merged: list[tuple[int, int]] = []
    for start, end in sorted((a, b) for a, b in intervals if b > a):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _merged_interval_ms(intervals: list[tuple[int, int]]) -> int:
    """Union duration; multiple simultaneous laughter labels must not double-count."""
    return sum(end - start for start, end in _merged_intervals(intervals))


def measure(events: list[dict], *, max_reply_gap_ms: int | None = None,
            min_duration_ms: int | None = None,
            max_duration_ms: int | None = None,
            max_ai_entry_laughter_ms: int | None = None,
            max_second_ai_onset_ms: int | None = None) -> dict:
    """Measure annotated turn gaps/overlap; no default timing threshold is imposed.

    The caller supplies recording-relative start_ms/end_ms for every event.
    A negative gap indicates that AI began before Dais finished speaking.
    Gap metrics pair an AI reply only with a new Dais utterance since the last AI.
    """
    max_reply_gap_ms = _optional_limit("max_reply_gap_ms", max_reply_gap_ms)
    min_duration_ms = _optional_limit("min_duration_ms", min_duration_ms)
    max_duration_ms = _optional_limit("max_duration_ms", max_duration_ms)
    max_ai_entry_laughter_ms = _optional_limit("max_ai_entry_laughter_ms", max_ai_entry_laughter_ms)
    max_second_ai_onset_ms = _optional_limit("max_second_ai_onset_ms", max_second_ai_onset_ms)
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
    second_ai_onset_ms = None  # First expected absurd diagnosis, NOT a measured laugh.
    ai_turn_count = 0
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
            ai_turn_count += 1
            if ai_turn_count == 2 and stage_start is not None:
                second_ai_onset_ms = start - stage_start
                if max_second_ai_onset_ms is not None and second_ai_onset_ms > max_second_ai_onset_ms:
                    violations.append({"event": idx, "reason": "second_ai_onset_exceeds_target",
                                       "onset_ms": second_ai_onset_ms})
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

    # Event order alone cannot detect audio that continues after Dais's end cue:
    # an AI utterance can start legitimately before the cue and finish afterward.
    # Stage-end silence is a hard contract, unlike opt-in laugh timing thresholds.
    post_end_ai_audio = []
    if stage_end is not None:
        for idx, event in enumerate(events):
            if event["speaker"] != "ai" or event.get("kind", "speech") != "speech":
                continue
            if not event["text"].strip():
                continue
            spill = event["end_ms"] - max(stage_end, event["start_ms"])
            if spill > 0:
                post_end_ai_audio.append((max(stage_end, event["start_ms"]), event["end_ms"]))
                violations.append({
                    "event": idx, "reason": "ai_audio_after_end_cue", "spillover_ms": spill,
                })

    # Descriptive only unless a predeclared entry threshold is supplied.
    # This examines time annotations, never audio waveforms or laughter intensity.
    laughter = [
        (idx, event["start_ms"], event["end_ms"])
        for idx, event in enumerate(events)
        if event["speaker"] == "audience" and event.get("kind", "speech") == "laughter"
    ]
    # Continuous audience laughter may span multiple overlapping annotations.
    # If a label begins AFTER AI entry but extends laughter already active at
    # entry, it still belongs to the same uninterrupted laughter episode.
    continuous_laughter = _merged_intervals([(start, end) for _, start, end in laughter])
    ai_laughter_overlaps = []
    for ai_idx, ai in enumerate(events):
        if ai["speaker"] != "ai" or ai.get("kind", "speech") != "speech" or not ai["text"].strip():
            continue
        start, end = ai["start_ms"], ai["end_ms"]
        all_intersections = [(max(start, l_start), min(end, l_end))
                             for _, l_start, l_end in laughter]
        # Only laughter already underway when AI began can trigger the optional
        # entry gate. Laughter starting mid-sentence is not an AI entry error.
        entry_intersections = [(start, min(end, l_end))
                               for l_start, l_end in continuous_laughter
                               if l_start <= start < l_end]
        overlap_ms = _merged_interval_ms(all_intersections)
        entry_ms = _merged_interval_ms(entry_intersections)
        if overlap_ms:
            ai_laughter_overlaps.append({
                "ai_event": ai_idx,
                "overlap_ms": overlap_ms,
                "entry_during_laughter_ms": entry_ms,
                "laughter_events": [i for i, l_start, l_end in laughter
                                   if max(start, l_start) < min(end, l_end)],
            })
        if max_ai_entry_laughter_ms is not None and entry_ms > max_ai_entry_laughter_ms:
            violations.append({
                "event": ai_idx,
                "reason": "ai_enters_active_audience_laughter",
                "entry_overlap_ms": entry_ms,
            })

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
        "second_ai_onset_ms": second_ai_onset_ms,
        "second_ai_onset_is_laughter": "NOT_MEASURED",
        "ai_audio_after_end_total_ms": _merged_interval_ms(post_end_ai_audio),
        "ai_audio_after_end_event_count": len(post_end_ai_audio),
        "annotated_audience_laughter_events": len(laughter),
        "ai_laughter_overlaps": ai_laughter_overlaps,
        "ai_laughter_overlap_total_ms": sum(r["overlap_ms"] for r in ai_laughter_overlaps),
        "ai_entries_during_laughter": sum(r["entry_during_laughter_ms"] > 0 for r in ai_laughter_overlaps),
        "thresholds_ms": {
            "max_reply_gap_ms": max_reply_gap_ms, "min_duration_ms": min_duration_ms,
            "max_duration_ms": max_duration_ms,
            "max_ai_entry_laughter_ms": max_ai_entry_laughter_ms,
            "max_second_ai_onset_ms": max_second_ai_onset_ms,
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
    parser.add_argument("--max-ai-entry-laughter-ms", type=int,
                        help="Opt-in max ms of existing audience laughter at AI entry; unset=report-only")
    parser.add_argument("--max-second-ai-onset-ms", type=int,
                        help="Opt-in deadline for the second AI turn onset (proxy, not laughter)")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
            raise ValueError("input must be an object containing events list")
        report = measure(
            payload["events"], max_reply_gap_ms=args.max_reply_gap_ms,
            min_duration_ms=args.min_duration_ms, max_duration_ms=args.max_duration_ms,
            max_ai_entry_laughter_ms=args.max_ai_entry_laughter_ms,
            max_second_ai_onset_ms=args.max_second_ai_onset_ms,
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
