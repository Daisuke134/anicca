#!/usr/bin/env python3
"""Count and minimally validate ManagerBench intervention cases without dependencies."""
import argparse
import json
from pathlib import Path

REQUIRED = {
    "case_id", "person_id", "decision_point_at", "available", "personal_history",
    "treatment_assigned", "assigned_probability", "proximal_outcome", "outcome_window_sec",
}


def load_cases(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("cases"), list):
        return payload["cases"]
    return []  # Existing non-intervention manifests deliberately count as zero.


def validate(case):
    missing = sorted(REQUIRED - case.keys())
    p = case.get("assigned_probability")
    if missing:
        return f"missing required fields: {', '.join(missing)}"
    if isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 < p < 1:
        return "assigned_probability must be a number strictly between 0 and 1"
    if not isinstance(case["personal_history"], dict) or not case["personal_history"]:
        return "personal_history must be a non-empty object"
    if case["treatment_assigned"] and not case.get("delivery_id"):
        return "treated case requires delivery_id"
    return None


def inspect(paths):
    count, errors = 0, []
    for path in paths:
        for index, case in enumerate(load_cases(path)):
            # Only manifests explicitly using the intervention contract are counted.
            if not (isinstance(case, dict) and (REQUIRED & case.keys())):
                continue
            count += 1
            error = validate(case)
            if error:
                errors.append(f"{path}:{index}: {error}")
    return count, errors


def main():
    p = argparse.ArgumentParser()
    p.add_argument("paths", nargs="*", type=Path, default=[Path(__file__).with_name("restraint-v1.json")])
    p.add_argument("--require-min", type=int, default=0)
    args = p.parse_args()
    count, errors = inspect(args.paths)
    if errors:
        raise SystemExit("INVALID\n" + "\n".join(errors))
    if count < args.require_min:
        raise SystemExit(f"FAIL: ManagerBench intervention cases={count}; required>={args.require_min}")
    print(f"PASS: ManagerBench intervention cases={count}; invalid=0")


if __name__ == "__main__":
    main()
