#!/usr/bin/env python3
"""Offline *annotated transcript* stage gates; not a voice or humor evaluator."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

OPENING = "はい、救急指令センターです。火事ですか、救急ですか？"
SECOND = ("救急ですね。声で分かりました。右ひざがご実家に帰られています。"
          "病名は「急性ひざの里帰りスペシャル」です。帰りの切符はこちらで手配します。")
SPEAKERS = {"dais", "ai", "audience", "staff"}
THIRD_PARTY_KINDS = {"speech", "laughter", "noise"}
QUESTION_STEMS = ("住所は", "どこですか", "今どこ", "何が見え", "目印は", "教えてください", "どちらですか")


def validate(events: list[dict]) -> dict:
    """Check explicit stage cues and turn order in an annotated text transcript."""
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a nonempty list")
    violations: list[dict] = []
    started = False
    ended = False
    last_replied_to_dais = False
    ai_count = 0
    dais_turns = 0
    third_party_speech_since_dais = False
    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"events[{idx}] must be object")
        speaker, utterance, cue = event.get("speaker"), event.get("text"), event.get("cue")
        kind = event.get("kind", "speech")
        if speaker not in SPEAKERS or not isinstance(utterance, str) or cue not in (None, "start", "end"):
            raise ValueError(f"events[{idx}] invalid speaker/text/cue")
        if not isinstance(kind, str) or kind not in THIRD_PARTY_KINDS or (speaker in {"dais", "ai"} and kind != "speech"):
            raise ValueError(f"events[{idx}] invalid kind for speaker")
        if cue and speaker != "dais":
            raise ValueError(f"events[{idx}]: start/end cues must be from dais")
        if cue == "start":
            if started or ended or "痛い" not in utterance:
                violations.append({"event": idx, "reason": "invalid_start_cue"})
            else:
                started = True
                last_replied_to_dais = False
                third_party_speech_since_dais = False
                dais_turns += 1
        elif cue == "end":
            if not started or ended:
                violations.append({"event": idx, "reason": "invalid_end_cue"})
            ended = True
        elif speaker == "dais" and started and not ended and utterance.strip():
            dais_turns += 1
            last_replied_to_dais = False
            third_party_speech_since_dais = False
        elif (speaker in {"audience", "staff"} and started and not ended
              and kind == "speech" and utterance.strip()):
            third_party_speech_since_dais = True

        if speaker != "ai" or not utterance.strip():
            continue
        if not started:
            violations.append({"event": idx, "reason": "premature_ai_speech"})
            continue
        if ended:
            violations.append({"event": idx, "reason": "post_end_ai_speech"})
            continue
        if last_replied_to_dais:
            violations.append({"event": idx, "reason": "ai_without_new_dais_turn"})
        # A transcript cannot establish who caused the reply. This is a conservative
        # review flag, not proof of AI speaker misattribution.
        if third_party_speech_since_dais and not last_replied_to_dais:
            violations.append({"event": idx, "reason": "ambiguous_third_party_speech_between_dais_and_ai"})
        ai_count += 1
        last_replied_to_dais = True
        if ai_count == 1 and utterance != OPENING:
            violations.append({"event": idx, "reason": "opening_not_exact"})
        if ai_count == 2 and utterance != SECOND:
            violations.append({"event": idx, "reason": "second_not_exact"})
        if ai_count > 1 and (
            "?" in utterance or "？" in utterance
            or any(stem in utterance for stem in QUESTION_STEMS)
        ):
            violations.append({"event": idx, "reason": "interview_question_after_opening"})
        if ai_count > 2 and utterance.count("。") > 3:
            violations.append({"event": idx, "reason": "long_ai_turn_proxy"})
    if not started:
        violations.append({"event": None, "reason": "missing_start"})
    if ai_count < 2 and started:
        violations.append({"event": None, "reason": "missing_two_script_replies"})
    if not ended:
        violations.append({"event": None, "reason": "missing_end"})
    return {
        "gate": "PASS" if not violations else "FAIL", "violations": violations,
        "ai_turns": ai_count, "dais_turns": dais_turns,
        "scope": "annotated_text_transcript_only", "laughter": "NOT_MEASURED",
        "voice": "NOT_MEASURED", "phone_ai_comprehension": "NOT_MEASURED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("events"), list):
            raise ValueError("Input must be an object with events list")
        result = {"scenario_id": data.get("scenario_id"), **validate(data["events"])}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    print(f"{result['gate']}: {len(result['violations'])} violations, {result['ai_turns']} AI turns")
    return int(args.strict and result["gate"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
