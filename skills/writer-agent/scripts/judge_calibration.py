#!/usr/bin/env python3
"""Compare Writer judge preference with attributable reward outcomes."""

from __future__ import annotations

import math
from typing import Any


JOIN_FIELDS = (
    "product_id",
    "run_id",
    "artifact_id",
    "variant_id",
)
STATUSES = ("scorable", "unknown", "insufficient")


class CalibrationInvariant(ValueError):
    """Judge and reward evidence cannot be compared safely."""


def _key(row: dict[str, Any]) -> tuple[str, ...]:
    values = tuple(row.get(field) for field in JOIN_FIELDS)
    if any(not isinstance(value, str) or not value for value in values):
        raise CalibrationInvariant("calibration lineage is incomplete")
    return values


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum(
        (a - left_mean) * (b - right_mean)
        for a, b in zip(left, right, strict=True)
    )
    left_scale = math.sqrt(sum((a - left_mean) ** 2 for a in left))
    right_scale = math.sqrt(sum((b - right_mean) ** 2 for b in right))
    if left_scale == 0 or right_scale == 0:
        return None
    return round(numerator / (left_scale * right_scale), 6)


def calibrate(
    judgments: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Join exact variants and compare only terminal, scorable rewards."""
    by_lineage: dict[tuple[str, ...], dict[str, Any]] = {}
    for receipt in receipts:
        lineage = _key(receipt)
        if lineage in by_lineage:
            raise CalibrationInvariant("duplicate reward receipt")
        by_lineage[lineage] = receipt
    counts = {status: 0 for status in STATUSES}
    scorable_variants: list[str] = []
    judge_scores: list[float] = []
    reward_ranks: list[float] = []

    for judgment in judgments:
        receipt = by_lineage.get(_key(judgment))
        status = (
            receipt.get("status")
            if receipt is not None
            else "insufficient"
        )
        if status not in counts:
            raise CalibrationInvariant("reward status is unsupported")
        counts[status] += 1
        if status != "scorable":
            continue
        judge_score = judgment.get("judge_score")
        reward_rank = receipt.get("reward", {}).get("rank")
        if not isinstance(judge_score, (int, float)) or not isinstance(
            reward_rank,
            (int, float),
        ):
            raise CalibrationInvariant("scorable values must be numeric")
        scorable_variants.append(str(judgment["variant_id"]))
        judge_scores.append(float(judge_score))
        reward_ranks.append(float(reward_rank))

    correlation = _correlation(judge_scores, reward_ranks)
    return {
        "reward": "calibrated_conversion_rank",
        "counts": counts,
        "scorable_variants": scorable_variants,
        "rank_correlation": correlation,
        "status": "scorable" if correlation is not None else "insufficient",
    }
