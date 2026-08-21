#!/usr/bin/env python3
"""Article-body learning slice with body-specific evidence and weights."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bounded_learning import run_bounded_cycle
from article_body_opponents import validate_body_comparison


SLICE = "article-body"
OPPONENT = "article-body-corpus"
REWARD = "engaged_read_then_conversion"


def run_article_body_cycle(
    *,
    reward_receipt: dict[str, Any],
    blame: list[dict[str, Any]],
    proposal: dict[str, Any],
    held_out_before: float,
    held_out_after: float,
    weights_path: Path,
    rule_gate: dict[str, Any],
    comparison_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist one body-only change when body reward and held-out agree."""

    if reward_receipt.get("status") == "scorable":
        for field in ("engaged_read", "downstream_conversion"):
            if not isinstance(reward_receipt.get(field), (int, float)):
                raise ValueError(f"body reward requires numeric {field}")
        validate_body_comparison(comparison_receipt)

    return run_bounded_cycle(
        slice_name=SLICE,
        opponent=OPPONENT,
        reward_name=REWARD,
        weight_suffix="state/weights/article-body.json",
        reward_receipt=reward_receipt,
        blame=blame,
        proposal=proposal,
        held_out_before=held_out_before,
        held_out_after=held_out_after,
        weights_path=weights_path,
        rule_gate=rule_gate,
    )
