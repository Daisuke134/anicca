#!/usr/bin/env python3
"""Normalize explicitly tagged ASR text fragments into complete stage turns.

No audio decoding, diarization, speaker authentication, or laughter measurement.
Missing/ambiguous turn identity raises an error rather than inventing a turn.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_stage_dialogue import validate as validate_stage
from measure_stage_timing import measure as measure_stage_timing

SPEAKERS = {"dais", "ai", "audience", "staff"}
KINDS = {"speech", "laughter", "noise"}


def normalize(events: list[dict], *, max_gap_ms: int = 250) -> list[dict]:
    """Join contiguous dais/AI speech chunks ONLY with matching explicit turn_id.

    The ASR transcription itself is not corrected. Adjacent text is joined exactly
    as provided. Third-party events cannot be crossed or silently discarded.
    """
    if type(max_gap_ms) is not int or max_gap_ms < 0:
        raise ValueError("max_gap_ms must be a nonnegative integer")
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a nonempty list")

    turns: list[dict] = []
    seen_turn_ids: set[str] = set()
    last_actor_end: dict[str, int] = {}
    prev_start = -1
    for index, original in enumerate(events):
        if not isinstance(original, dict):
            raise ValueError(f"events[{index}] must be an object")
        event = dict(original)
        speaker = event.get("speaker")
        kind = event.get("kind", "speech")
        text = event.get("text")
        cue = event.get("cue")
        start, end = event.get("start_ms"), event.get("end_ms")
        if speaker not in SPEAKERS or kind not in KINDS or not isinstance(text, str):
            raise ValueError(f"events[{index}] invalid speaker/kind/text")
        if speaker in {"dais", "ai"} and kind != "speech":
            raise ValueError(f"events[{index}] invalid actor kind")
        if cue not in (None, "start", "end") or (cue and speaker != "dais"):
            raise ValueError(f"events[{index}] invalid cue")
        if type(start) is not int or type(end) is not int or start < 0 or end < start:
            raise ValueError(f"events[{index}] invalid timestamps")
        if start < prev_start:
            raise ValueError(f"events[{index}] not sorted by start_ms")
        prev_start = start

        groupable = speaker in {"dais", "ai"} and kind == "speech"
        # A nonempty spoken fragment requires positive annotated duration.
        # Zero-length actor speech is not evidence of a completed voice turn.
        if groupable and end == start:
            raise ValueError(f"events[{index}] zero-duration actor speech")
        if groupable:
            turn_id = event.get("turn_id")
            if not isinstance(turn_id, str) or not turn_id.strip():
                raise ValueError(f"events[{index}] missing explicit turn_id")
            if not text:
                raise ValueError(f"events[{index}] empty actor ASR fragment")
            if turns and turns[-1].get("turn_id") == turn_id:
                previous = turns[-1]
                if previous["speaker"] != speaker:
                    raise ValueError(f"events[{index}] turn_id speaker conflict")
                if cue == "start" or previous.get("cue") == "end":
                    raise ValueError(f"events[{index}] invalid cue within a turn")
                if cue == "end" and previous.get("cue") == "start":
                    raise ValueError(f"events[{index}] start and end cues in one turn")
                gap = start - previous["end_ms"]
                if gap < 0 or gap > max_gap_ms:
                    raise ValueError(f"events[{index}] ambiguous fragment gap {gap}ms")
                previous["text"] += text
                previous["end_ms"] = end
                last_actor_end[speaker] = end
                previous["source_chunk_indexes"].append(index)
                previous["chunk_count"] += 1
                if cue == "end":
                    previous["cue"] = cue
                continue
            if turn_id in seen_turn_ids:
                raise ValueError(f"events[{index}] noncontiguous reused turn_id")
            # ASR may emit duplicate hypotheses with distinct turn IDs.
            # Two different turns from the same actor cannot occupy the
            # same annotated time interval. Cross-speaker overlap is legal
            # input and is handled by the separate timing gate.
            if start < last_actor_end.get(speaker, -1):
                raise ValueError(f"events[{index}] overlapping distinct {speaker} turns")
            seen_turn_ids.add(turn_id)
            last_actor_end[speaker] = end
        elif event.get("turn_id") is not None:
            raise ValueError(f"events[{index}] third-party events must not claim turn_id")

        event["source_chunk_indexes"] = [index]
        event["chunk_count"] = 1
        turns.append(event)
    return turns


def evaluate(payload: dict, *, max_gap_ms: int = 250,
             require_turn_coverage: bool = True) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise ValueError("input must contain events list")
    provenance = payload.get("provenance", "UNDECLARED")
    if provenance not in ("synthetic", "audio_annotated", "UNDECLARED"):
        raise ValueError("unsupported provenance")
    turns = normalize(payload["events"], max_gap_ms=max_gap_ms)
    audit = validate_stage(turns, require_turn_coverage=require_turn_coverage)
    # Script order alone can report PASS while AI begins before Dais finishes,
    # or AI audio persists beyond the end cue. Use the existing timestamp
    # auditor on the *normalized* turns; never infer timings from raw text.
    timing = measure_stage_timing(turns)
    return {
        "scenario_id": payload.get("scenario_id"),
        "source_provenance_claim": provenance,
        "source_chunk_count": len(payload["events"]),
        "normalized_event_count": len(turns),
        "actor_turns": sum(e["speaker"] in {"dais", "ai"} for e in turns),
        "joined_chunk_count": len(payload["events"]) - len(turns),
        "normalized_events": turns,
        "stage_gate": audit,
        "timing_gate": timing["timing_gate"],
        "timing_audit": timing,
        "gate": "PASS" if audit["gate"] == "PASS" and timing["timing_gate"] == "PASS" else "FAIL",
        "scope": "explicit_turn_id_text_and_annotated_timing_only",
        "raw_audio_verified": False,
        "speaker_identity_verified": False,
        "voice_reproducibility": "NOT_MEASURED",
        "phone_ai_comprehension": "NOT_MEASURED",
        "rear_intelligibility": "NOT_MEASURED",
        "audience_laughter": "NOT_MEASURED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-gap-ms", type=int, default=250)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        result = evaluate(json.loads(args.input.read_text(encoding="utf-8")),
                          max_gap_ms=args.max_gap_ms)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    except (ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    print(f"{result['gate']}: {result['source_chunk_count']} chunks -> "
          f"{result['normalized_event_count']} events; verified_audio=false")
    return int(args.strict and result["gate"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
