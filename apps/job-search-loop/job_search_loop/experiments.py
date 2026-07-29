from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping


MIN_RESOLVED_APPLICATIONS = 10
WILSON_Z_95 = 1.959963984540054


@dataclass(frozen=True)
class ExperimentResult:
    decision: str
    reason: str
    changed_field: str | None
    baseline_interval: tuple[float, float]
    candidate_interval: tuple[float, float]


def _wilson_interval(positive: int, resolved: int) -> tuple[float, float]:
    if resolved < 0 or positive < 0 or positive > resolved:
        raise ValueError("positive and resolved counts are inconsistent")
    if resolved == 0:
        return (0.0, 1.0)
    proportion = positive / resolved
    z_squared = WILSON_Z_95**2
    denominator = 1 + z_squared / resolved
    center = (proportion + z_squared / (2 * resolved)) / denominator
    margin = (
        WILSON_Z_95
        * math.sqrt(
            proportion * (1 - proportion) / resolved
            + z_squared / (4 * resolved**2)
        )
        / denominator
    )
    return (center - margin, center + margin)


def _changed_fields(
    baseline: Mapping[str, Any], candidate: Mapping[str, Any]
) -> tuple[str, ...]:
    keys = set(baseline) | set(candidate)
    return tuple(
        sorted(key for key in keys if baseline.get(key) != candidate.get(key))
    )


def evaluate_candidate(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    baseline_resolved: int,
    baseline_positive: int,
    candidate_resolved: int,
    candidate_positive: int,
    replay_violations: int,
) -> ExperimentResult:
    baseline_interval = _wilson_interval(baseline_positive, baseline_resolved)
    candidate_interval = _wilson_interval(candidate_positive, candidate_resolved)
    changed = _changed_fields(baseline, candidate)
    changed_field = changed[0] if len(changed) == 1 else None

    if len(changed) != 1:
        return ExperimentResult(
            "rejected",
            "candidate_must_change_exactly_one_field",
            changed_field,
            baseline_interval,
            candidate_interval,
        )
    if replay_violations < 0:
        raise ValueError("replay_violations cannot be negative")
    if replay_violations:
        return ExperimentResult(
            "rejected",
            "replay_safety_violation",
            changed_field,
            baseline_interval,
            candidate_interval,
        )
    if (
        baseline_resolved < MIN_RESOLVED_APPLICATIONS
        or candidate_resolved < MIN_RESOLVED_APPLICATIONS
    ):
        return ExperimentResult(
            "inconclusive",
            "insufficient_resolved_applications",
            changed_field,
            baseline_interval,
            candidate_interval,
        )
    if candidate_interval[0] > baseline_interval[1]:
        return ExperimentResult(
            "promote",
            "candidate_interval_above_baseline",
            changed_field,
            baseline_interval,
            candidate_interval,
        )
    return ExperimentResult(
        "inconclusive",
        "confidence_intervals_overlap",
        changed_field,
        baseline_interval,
        candidate_interval,
    )


def evidence_hash(result: ExperimentResult) -> str:
    encoded = json.dumps(
        asdict(result),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
