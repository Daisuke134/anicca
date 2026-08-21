#!/usr/bin/env python3
"""Long-form learning slice with purchase, completion, and refund evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bounded_learning import run_bounded_cycle


SLICE = "long-form"
OPPONENT = "long-form-corpus"
REWARD = "purchase_completion_refund_guarded"


def run_longform_cycle(
    *,
    reward_receipt: dict[str, Any],
    blame: list[dict[str, Any]],
    proposal: dict[str, Any],
    held_out_before: float,
    held_out_after: float,
    weights_path: Path,
    rule_gate: dict[str, Any],
) -> dict[str, Any]:
    """Persist one long-form change only when every reward guardrail passes."""

    guardrail_failure = None
    if reward_receipt.get("status") == "scorable":
        required = (
            "purchase_rate",
            "completion_rate",
            "refund_rate",
            "refund_guardrail",
        )
        for field in required:
            if not isinstance(reward_receipt.get(field), (int, float)):
                raise ValueError(f"long-form reward requires numeric {field}")
        if reward_receipt["refund_rate"] > reward_receipt["refund_guardrail"]:
            guardrail_failure = "refund_guardrail_failed"

    return run_bounded_cycle(
        slice_name=SLICE,
        opponent=OPPONENT,
        reward_name=REWARD,
        weight_suffix="state/weights/long-form.json",
        reward_receipt=reward_receipt,
        blame=blame,
        proposal=proposal,
        held_out_before=held_out_before,
        held_out_after=held_out_after,
        weights_path=weights_path,
        rule_gate=rule_gate,
        guardrail_failure_reason=guardrail_failure,
    )
