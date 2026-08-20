#!/usr/bin/env python3
"""Bounded title-learning slice.

The title slice has its own opponent, calibrated reward, and runtime weight
file.  A cycle may change exactly one blamed rule and persists it only when
held-out performance does not regress.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bounded_learning import run_bounded_cycle


SLICE = "title"
OPPONENT = "title-corpus"
REWARD = "calibrated_conversion_rank"


def run_title_cycle(
    *,
    calibration: dict[str, Any],
    blame: list[dict[str, Any]],
    proposal: dict[str, Any],
    held_out_before: float,
    held_out_after: float,
    weights_path: Path,
    rule_gate: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate and, when safe, persist one title-weight change."""
    return run_bounded_cycle(
        slice_name=SLICE,
        opponent=OPPONENT,
        reward_name=REWARD,
        weight_suffix="state/weights/title.json",
        reward_receipt=calibration,
        blame=blame,
        proposal=proposal,
        held_out_before=held_out_before,
        held_out_after=held_out_after,
        weights_path=weights_path,
        rule_gate=rule_gate,
    )
