#!/usr/bin/env python3
"""Offline composite gate for annotated injury-stage text: NEVER audio/humor proof."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from validate_stage_dialogue import validate as stage_gate
from audit_callback_continuity import audit as callback_gate
from audit_adlib_anchors import audit as adlib_gate


def evaluate(events: list[dict], chains: list[dict], *, require_adlib: bool = False) -> dict:
    """Require ALL requested gates; do not mistake an unrequested gate for PASS."""
    if not isinstance(require_adlib, bool):
        raise ValueError("require_adlib must be boolean")
    stage = stage_gate(events, require_turn_coverage=True)
    callbacks = callback_gate(events, chains)
    annotated = any(isinstance(e, dict) and
                    ("anchor_any" in e or "action_any" in e) for e in events)
    if require_adlib and not annotated:
        raise ValueError("require_adlib requires at least one annotated Dais turn")
    adlib = adlib_gate(events) if annotated else None
    status = {"script_and_cues": stage["gate"],
              "multi_turn_callback": callbacks["gate"],
              "adlib_uptake": adlib["gate"] if adlib is not None else "NOT_REQUESTED"}
    return {
        "gate": "PASS" if all(v in ("PASS", "NOT_REQUESTED") for v in status.values()) else "FAIL",
        "component_gates": status,
        "stage": stage, "callback": callbacks, "adlib": adlib,
        "source_scope": "human_annotated_complete_turn_text_only",
        "real_voice": "NOT_MEASURED", "speech_recognition": "NOT_MEASURED",
        "phone_ai_recognition": "NOT_MEASURED", "audience_laughter": "NOT_MEASURED",
        "warning": "PASS only joins lexical/turn-order proxies. It does not certify speaker identity, delivery, meaning or humor.",
    }


def run(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("source_type") != "synthetic":
        raise ValueError("Only explicit synthetic fixtures accepted; audio is out of scope")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases must be nonempty")
    records = []
    for i, case in enumerate(cases):
        if not isinstance(case, dict) or case.get("expected_gate") not in ("PASS", "FAIL"):
            raise ValueError(f"cases[{i}] needs expected_gate PASS or FAIL")
        actual = evaluate(case["events"], case["chains"],
                          require_adlib=case.get("require_adlib", False))
        records.append({"scenario_id": case.get("scenario_id", f"case-{i}"),
                        "expected_gate": case["expected_gate"],
                        "expectation_met": actual["gate"] == case["expected_gate"], **actual})
    return {"source_type": "synthetic", "total_cases": len(records),
            "expectations_met": sum(int(x["expectation_met"]) for x in records),
            "all_expectations_met": all(x["expectation_met"] for x in records),
            "cases": records, "real_voice": "NOT_MEASURED",
            "audience_laughter": "NOT_MEASURED", "model_comparison": "NOT_COMPARABLE"}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()
    try:
        report = run(json.loads(args.input.read_text(encoding="utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        p.exit(2, f"ERROR: {exc}\n")
    print(f"{'PASS' if report['all_expectations_met'] else 'FAIL'}: {report['expectations_met']}/{report['total_cases']} synthetic expectations met")
    return int(args.strict and not report["all_expectations_met"])


if __name__ == "__main__":
    raise SystemExit(main())
