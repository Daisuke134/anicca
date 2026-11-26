#!/usr/bin/env python3
"""Fail-closed additive consistency audit for ManagerBench intervention cases.

Read-only and standard-library-only. Complements existing minimal
check_intervention_cases.py without changing the frozen v1 schema/replay.

This establishes *record consistency only*, not real observed intervention
effects, successful randomization, participant consent or human benefit.
Missingness and availability follow the MRT/WCLS distinctions:
https://pmc.ncbi.nlm.nih.gov/articles/PMC4732571/
https://pmc.ncbi.nlm.nih.gov/articles/PMC12618347/
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import sys

from check_intervention_cases import REQUIRED as V1_REQUIRED, validate as v1_validate

EVIDENCE_LEVEL = "SCHEMA_CONSISTENCY_ONLY_NOT_CAUSAL_EFFECT"


class AuditError(ValueError):
    """Invalid or ambiguous intervention record, no automatic correction."""


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AuditError(f"{field} must be a timezone-aware ISO8601 string")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise AuditError(f"{field} must be a timezone-aware ISO8601 string") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise AuditError(f"{field} must contain a timezone offset")
    return timestamp


def _nonblank(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise AuditError(f"{field} must be a nonblank string")


def validate_case(case: object) -> None:
    """Check additional invariants, leaving the original v1 contract untouched.

    v1 allows nullable proximal_outcome and optional outcome_observed. This
    *strict audit profile* requires the latter to make missingness explicit.
    """
    if not isinstance(case, dict):
        raise AuditError("case must be an object")
    missing = sorted((V1_REQUIRED | {"outcome_observed"}) - case.keys())
    if missing:
        raise AuditError("missing required fields: " + ", ".join(missing))

    _nonblank(case["case_id"], "case_id")
    _nonblank(case["person_id"], "person_id")

    for key in ("available", "treatment_assigned", "outcome_observed"):
        if not isinstance(case[key], bool):
            raise AuditError(f"{key} must be a boolean")

    if not isinstance(case["personal_history"], dict) or not case["personal_history"]:
        raise AuditError("personal_history must be a nonempty object")

    probability = case["assigned_probability"]
    if (type(probability) not in (int, float) or not math.isfinite(probability)
            or not 0 < probability < 1):
        raise AuditError("assigned_probability must be finite and strictly between 0 and 1")

    window = case["outcome_window_sec"]
    if type(window) is not int or window <= 0:
        raise AuditError("outcome_window_sec must be a positive integer")

    decision_time = _timestamp(case["decision_point_at"], "decision_point_at")

    if not case["available"] and case["treatment_assigned"]:
        raise AuditError("unavailable decision point cannot be assigned treatment")

    if case["treatment_assigned"]:
        _nonblank(case.get("intervention_id"), "intervention_id")
        _nonblank(case.get("delivery_id"), "delivery_id")

    # Reuse existing v1 checks; never replace or silently relax the v1 gate.
    base_error = v1_validate(case)
    if base_error:
        raise AuditError("original v1 check failed: " + base_error)

    value = case["proximal_outcome"]
    if case["outcome_observed"]:
        if value is None:
            raise AuditError("observed outcome requires a non-null proximal_outcome")
        if type(value) is not bool and (
            type(value) not in (int, float) or not math.isfinite(value)
        ):
            raise AuditError("proximal_outcome must be finite numeric or boolean")
    else:
        if value is not None:
            raise AuditError("unobserved outcome must have null proximal_outcome")

    observed_at = case.get("outcome_observed_at")
    if observed_at is not None:
        if not case["outcome_observed"]:
            raise AuditError("unobserved outcome cannot have a timestamp")
        observed_time = _timestamp(observed_at, "outcome_observed_at")
        if observed_time < decision_time:
            raise AuditError("outcome_observed_at cannot be before decision_point_at")
    # Late data entry is valid. The observed time is NOT required to be inside
    # the proximal outcome window; actual event/measurement time is distinct
    # from the time the observation was recorded.


def audit_cases(cases: object) -> dict:
    """Validate all cases and return counts, never an estimated causal effect."""
    if not isinstance(cases, list):
        raise AuditError("cases must be a list")
    case_ids: set[str] = set()
    persons: set[str] = set()
    result = {
        "audit_profile": "managerbench_intervention_v1_strict_additive",
        "evidence_level": EVIDENCE_LEVEL,
        "validated_decisions": 0,
        "available_randomized_decisions": 0,
        "unavailable_decisions": 0,
        "treated_available_decisions": 0,
        "observed_outcomes": 0,
        "missing_outcomes": 0,
        "distinct_person_ids": 0,
        "causal_effect_estimated": False,
        "real_user_benefit_proven": False,
        "note": ("Schema consistency and missingness only; not proof of assignment "
                 "integrity, real population coverage, causal identification or welfare."),
    }
    for index, case in enumerate(cases):
        try:
            validate_case(case)
        except AuditError as error:
            # Do not print participant IDs, histories, treatment payloads or values.
            raise AuditError(f"invalid intervention case at index {index}: {error}") from error

        case_id = case["case_id"].strip()
        if case_id in case_ids:
            raise AuditError(f"duplicate case_id at index {index}")
        case_ids.add(case_id)
        persons.add(case["person_id"])
        result["validated_decisions"] += 1
        if case["available"]:
            result["available_randomized_decisions"] += 1
            if case["treatment_assigned"]:
                result["treated_available_decisions"] += 1
        else:
            result["unavailable_decisions"] += 1
        if case["outcome_observed"]:
            result["observed_outcomes"] += 1
        else:
            result["missing_outcomes"] += 1
    result["distinct_person_ids"] = len(persons)
    return result


def audit_paths(paths: list[Path]) -> dict:
    if not paths:
        raise AuditError("at least one intervention case file is required")
    all_cases: list = []
    for path in paths:
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise AuditError("cannot read intervention case file") from error
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            raise AuditError("invalid JSON in intervention case file") from error
        if isinstance(data, list):
            cases = data
        elif isinstance(data, dict) and isinstance(data.get("cases"), list):
            cases = data["cases"]
        else:
            # The old replay checker intentionally counts old, unrelated
            # manifests as zero. The strict audit only accepts explicit
            # intervention containers to avoid a false clean bill of health.
            raise AuditError("cases must be an explicit list or {'cases': list}")
        all_cases.extend(cases)
    return audit_cases(all_cases)


def main(argv: list[str] | None = None, *, return_report: bool = False):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--require-min", type=int, default=0,
                        help="Optional minimum validated decisions; default zero")
    arguments = parser.parse_args(argv)
    try:
        if arguments.require_min < 0:
            raise AuditError("--require-min must not be negative")
        report = audit_paths(arguments.paths)
        passed = report["validated_decisions"] >= arguments.require_min
        report["gate_status"] = (
            "PASS_ZERO_CASES" if passed and report["validated_decisions"] == 0
            else "PASS_CONSISTENCY_ONLY" if passed
            else "FAIL_UNDER_MINIMUM"
        )
        exit_code = 0 if passed else 1
    except AuditError as error:
        report = {
            "gate_status": "INVALID_INPUT",
            "error": str(error),
            "evidence_level": EVIDENCE_LEVEL,
            "causal_effect_estimated": False,
            "real_user_benefit_proven": False,
        }
        exit_code = 1
    if return_report:
        return exit_code, report
    print(json.dumps(report, sort_keys=True, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())