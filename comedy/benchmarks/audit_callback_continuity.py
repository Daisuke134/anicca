#!/usr/bin/env python3
"""Offline, annotated multi-turn callback chain audit. Not an ASR or humor judge."""
from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path


def normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def words(chain: dict, key: str, index: int) -> list[str]:
    value = chain.get(key)
    if (not isinstance(value, list) or not 1 <= len(value) <= 12
            or any(not isinstance(x, str) or not x.strip() or len(x) > 100 for x in value)):
        raise ValueError(f"chains[{index}].{key} must have 1..12 nonempty strings")
    return value


def audit(events: list[dict], chains: list[dict]) -> dict:
    """Check scripted callback setup -> human reaction -> payoff in a complete-turn trace."""
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a nonempty array")
    if not isinstance(chains, list) or not chains:
        raise ValueError("chains must be a nonempty array; unannotated is not PASS")
    for i, event in enumerate(events):
        if (not isinstance(event, dict) or event.get("speaker") not in
                {"dais", "ai", "audience", "staff"} or
                not isinstance(event.get("text"), str) or
                event.get("cue") not in (None, "start", "end")):
            raise ValueError(f"events[{i}] has invalid fields")
    violations = []
    checks = []

    def fail(reason: str, chain_index=None, event_index=None):
        violations.append({"reason": reason, "chain_index": chain_index,
                           "event_index": event_index})

    # Order is measurable in a complete-turn transcript; actual timing is NOT.
    first_cue = next((i for i, e in enumerate(events)
                      if e["speaker"] == "dais" and e.get("cue") == "start"), None)
    if first_cue is None:
        fail("missing_dais_start_cue")
    else:
        for i, e in enumerate(events[:first_cue]):
            if e["speaker"] == "ai" and e["text"].strip():
                fail("ai_spoke_before_start", event_index=i)
    end_cue = next((i for i, e in enumerate(events) if e.get("cue") == "end"), None)
    if end_cue is not None:
        for i in range(end_cue + 1, len(events)):
            if events[i]["speaker"] == "ai" and events[i]["text"].strip():
                fail("ai_spoke_after_end", event_index=i)

    previous_actor = None
    for i, e in enumerate(events):
        if not e["text"].strip() or e["speaker"] in ("audience", "staff"):
            continue
        if e["speaker"] == previous_actor == "ai":
            fail("consecutive_ai_turns_without_dais", event_index=i)
        previous_actor = e["speaker"]

    for ci, chain in enumerate(chains):
        if not isinstance(chain, dict):
            raise ValueError(f"chains[{ci}] must be an object")
        start = chain.get("setup_ai_event")
        callback = chain.get("callback_ai_event")
        if (type(start) is not int or type(callback) is not int or
                start < 0 or callback <= start or callback >= len(events)):
            raise ValueError(f"chains[{ci}] event indices must be ordered and in range")
        if (events[start]["speaker"] != "ai" or events[callback]["speaker"] != "ai"
                or events[start].get("cue") or events[callback].get("cue")):
            raise ValueError(f"chains[{ci}] must identify two normal AI turns")
        entity = chain.get("entity")
        if not isinstance(entity, str) or not entity.strip() or len(entity) > 100:
            raise ValueError(f"chains[{ci}].entity must be a nonempty string")
        setup_any = words(chain, "setup_any", ci)
        payoff_any = words(chain, "payoff_any", ci)
        forbidden = chain.get("forbidden_after_setup", [])
        if (not isinstance(forbidden, list) or len(forbidden) > 12 or
                any(not isinstance(x, str) or not x.strip() or len(x) > 100
                    for x in forbidden)):
            raise ValueError(f"chains[{ci}].forbidden_after_setup is invalid")

        setup_text = normalized(events[start]["text"])
        callback_text = normalized(events[callback]["text"])
        entity_normal = normalized(entity)
        has_setup_entity = entity_normal in setup_text
        has_setup = any(normalized(x) in setup_text for x in setup_any)
        has_callback_entity = entity_normal in callback_text
        has_payoff = any(normalized(x) in callback_text for x in payoff_any)
        has_dais_reaction = any(e["speaker"] == "dais" and
                                e.get("cue") is None and e["text"].strip()
                                for e in events[start + 1:callback])
        forbidden_matches = []
        for i in range(start + 1, len(events)):
            e = events[i]
            if e["speaker"] != "ai":
                continue
            t = normalized(e["text"])
            forbidden_matches.extend({"event": i, "phrase": phrase}
                                     for phrase in forbidden if normalized(phrase) in t)
        for ok, reason in [
            (has_setup_entity, "setup_missing_entity"),
            (has_setup, "setup_missing_state"),
            (has_callback_entity, "callback_missing_entity"),
            (has_payoff, "callback_missing_payoff"),
            (has_dais_reaction, "no_dais_reaction_between_beats"),
            (not forbidden_matches, "forbidden_continuity_reversal"),
        ]:
            if not ok:
                fail(reason, ci)
        checks.append({
            "chain_index": ci, "entity": entity,
            "setup_ai_event": start, "callback_ai_event": callback,
            "setup_entity_found": has_setup_entity,
            "setup_state_found": has_setup,
            "callback_entity_found": has_callback_entity,
            "payoff_found": has_payoff,
            "dais_reaction_present": has_dais_reaction,
            "forbidden_hits": forbidden_matches,
        })

    return {
        "gate": "FAIL" if violations else "PASS",
        "checks": checks, "violations": violations,
        "metric": "human_annotated_multi_turn_lexical_continuity_proxy",
        "voice": "NOT_MEASURED", "human_laughter": "NOT_MEASURED",
        "response_latency": "NOT_MEASURED", "semantic_consistency": "NOT_MEASURED",
        "warning": "String matches on human annotations and turn order only. Cannot verify voice, genuine actor reactions, actual dispatch, meaning or humor.",
    }


def run(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("source_type") != "synthetic":
        raise ValueError("Only explicitly synthetic fixtures may use this runner")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases must be a nonempty list")
    records = []
    for case in cases:
        if not isinstance(case, dict) or case.get("expected_gate") not in ("PASS", "FAIL"):
            raise ValueError("Each case needs expected_gate PASS or FAIL")
        result = audit(case["events"], case["chains"])
        records.append({"scenario_id": case.get("scenario_id"),
                        "expected_gate": case["expected_gate"],
                        "expectation_met": result["gate"] == case["expected_gate"],
                        **result})
    return {
        "source_type": "synthetic", "total_cases": len(records),
        "expectations_met": sum(x["expectation_met"] for x in records),
        "all_expectations_met": all(x["expectation_met"] for x in records),
        "cases": records, "voice": "NOT_MEASURED", "human_laughter": "NOT_MEASURED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        result = run(json.loads(args.input.read_text(encoding="utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    ok = result["all_expectations_met"]
    print(f"{'PASS' if ok else 'FAIL'}: synthetic multi-turn callback continuity")
    return int(args.strict and not ok)


if __name__ == "__main__":
    raise SystemExit(main())
