#!/usr/bin/env python3
"""Offline lexical proxy for *immediate* improv uptake. Never scores humor or audio."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


def norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


# Narrow Japanese denial proxy. Not a semantic parser or proof that an action happened.
NEGATED_ACTION_SUFFIX = re.compile(
    r"^(?:すること)?[のをにはがも]?(?:まだ)?"
    r"(?:しません|しない|していません|しておりません|してない|していない|"
    r"できません|できない|できていません|中止しました|取り消しました|"
    r"ません|ない)"
)


def action_mentions(text: str, actions: list[str]) -> tuple[list[str], list[str]]:
    """Separate affirmative-looking lexical mentions from explicit denials."""
    present, denied = [], []
    for action in actions:
        needle = norm(action)
        positions = [m.end() for m in re.finditer(re.escape(needle), text)]
        if not positions:
            continue
        if any(not NEGATED_ACTION_SUFFIX.match(text[pos:]) for pos in positions):
            present.append(action)
        else:
            denied.append(action)
    return present, denied


def terms(event: dict, key: str, index: int) -> list[str]:
    value = event.get(key)
    if (not isinstance(value, list) or not value or len(value) > 12
            or any(not isinstance(x, str) or not x.strip() or len(x) > 80 for x in value)):
        raise ValueError(f"events[{index}].{key} must be 1..12 nonempty strings")
    return value


def audit(events: list[dict]) -> dict:
    """Evaluate human-annotated complete turns, never inferred transcript semantics."""
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a nonempty list")
    for index, event in enumerate(events):
        if (not isinstance(event, dict)
                or event.get("speaker") not in {"dais", "ai", "audience", "staff"}
                or not isinstance(event.get("text"), str)
                or event.get("cue") not in (None, "start", "end")):
            raise ValueError(f"events[{index}] has an invalid speaker/text/cue")
    checks = []
    violations = []
    for index, event in enumerate(events):
        annotated = "anchor_any" in event or "action_any" in event
        if not annotated:
            continue
        if event["speaker"] != "dais" or event.get("cue") in ("start", "end"):
            raise ValueError(f"events[{index}] anchors only apply to complete Dais adlibs")
        anchors = terms(event, "anchor_any", index)
        actions = terms(event, "action_any", index)
        reply_index = None
        intervening_speech = False
        for j in range(index + 1, len(events)):
            other = events[j]
            if other.get("cue") == "end" or other["speaker"] == "dais":
                break
            if other["speaker"] in {"audience", "staff"} and other["text"].strip() and other.get("kind", "speech") == "speech":
                intervening_speech = True
            if other["speaker"] == "ai" and other["text"].strip():
                reply_index = j
                break
        matched_anchor = []
        matched_action = []
        negated_actions = []
        if reply_index is None:
            violations.append({"event": index, "reason": "missing_immediate_ai_reply"})
        else:
            text = norm(events[reply_index]["text"])
            matched_anchor = [a for a in anchors if norm(a) in text]
            matched_action, negated_actions = action_mentions(text, actions)
            if not matched_anchor:
                violations.append({"event": index, "reason": "immediate_reply_missing_anchor"})
            if not matched_action:
                reason = ("immediate_reply_only_negated_action" if negated_actions
                          else "immediate_reply_missing_action")
                violations.append({"event": index, "reason": reason})
        if intervening_speech:
            violations.append({"event": index, "reason": "intervening_third_party_speech_review"})
        checks.append({
            "dais_event": index,
            "immediate_ai_event": reply_index,
            "matched_anchors": matched_anchor,
            "matched_actions": matched_action,
            "negated_action_mentions": negated_actions,
            "third_party_speech_intervened": intervening_speech,
        })
    if not checks:
        violations.append({"event": None, "reason": "no_annotated_adlibs"})
    return {
        "gate": "PASS" if not violations else "FAIL",
        "annotated_adlibs": len(checks),
        "checks": checks,
        "violations": violations,
        "metric": "human_annotated_immediate_lexical_anchor_and_action_proxy",
        "voice": "NOT_MEASURED",
        "laughter": "NOT_MEASURED",
        "semantic_understanding": "NOT_MEASURED",
        "warning": "Lexical action and denial heuristics are incomplete; PASS is not proof of action, understanding, voice, or humor. Apply only to fully annotated turns.",
    }


def run(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("source_type") != "synthetic":
        raise ValueError("This fixture runner accepts only explicitly synthetic examples")
    if isinstance(data.get("cases"), list) and data["cases"]:
        cases = []
        for case in data["cases"]:
            actual = audit(case["events"])
            expected = case.get("expected_gate")
            if expected not in {"PASS", "FAIL"}:
                raise ValueError("Each synthetic case needs expected_gate PASS or FAIL")
            cases.append({"scenario_id": case.get("scenario_id"), "expected_gate": expected,
                          "expectation_met": expected == actual["gate"], **actual})
        return {"source_type": "synthetic", "total_cases": len(cases),
                "expectations_met": sum(c["expectation_met"] for c in cases),
                "all_expectations_met": all(c["expectation_met"] for c in cases),
                "cases": cases, "voice": "NOT_MEASURED", "laughter": "NOT_MEASURED"}
    result = audit(data["events"])
    return {"source_type": "synthetic", "scenario_id": data.get("scenario_id"), **result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        result = run(json.loads(args.input.read_text(encoding="utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    success = result.get("all_expectations_met", result.get("gate") == "PASS")
    print(f"{'PASS' if success else 'FAIL'}: synthetic anchor-uptake audit")
    return int(args.strict and not success)


if __name__ == "__main__":
    raise SystemExit(main())
