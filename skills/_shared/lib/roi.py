"""roi — token cost calc + kill-switch.

PROP-B2-cost-formula (required:true, Tier 1) — REQ-B2 closed-form per-model rates.
PROP-B4-killswitch (required:true, Tier 1) — REQ-B4 cumulative cost > 5× earned
  AND age > 7-day grace.
PROP-B5-rolling (Tier 1) + PROP-B6-estimate (Tier 1).
"""
from __future__ import annotations

from dataclasses import dataclass


_DEFAULT_GRACE_SECONDS = 7 * 86400
_ESTIMATE_PENALTY = 2.0


@dataclass(frozen=True)
class BreakdownEntry:
    model_id: str
    tokens_in: int
    tokens_out: int


def compute_token_cost_jpy(
    *,
    model_breakdown: list[dict | BreakdownEntry],
    rates_input: dict[str, float],
    rates_output: dict[str, float],
    fx_usdjpy: float,
    token_source: str = "measured",
) -> float:
    """Closed-form per-model token cost per REQ-B2.

    token_cost_jpy = FX_USDJPY × Σ_each [(tokens_in/1M)*rate_input[model_id]
                                       + (tokens_out/1M)*rate_output[model_id]]

    Multiplied by 2.0 when token_source == 'estimated' (REQ-B6 conservative penalty).
    Raises ValueError on unknown model_id (REQ-B2: refuse silent zero on unknown model).
    """
    usd_total = 0.0
    for entry in model_breakdown:
        if isinstance(entry, BreakdownEntry):
            model_id, tin, tout = entry.model_id, entry.tokens_in, entry.tokens_out
        else:
            model_id = entry["model_id"]
            tin = int(entry.get("tokens_in", 0))
            tout = int(entry.get("tokens_out", 0))
        if model_id not in rates_input or model_id not in rates_output:
            raise ValueError(
                f"unknown model_id {model_id!r} not in rate table — refuse to write row"
            )
        usd_total += (tin / 1_000_000) * rates_input[model_id]
        usd_total += (tout / 1_000_000) * rates_output[model_id]
    cost = usd_total * fx_usdjpy
    if token_source == "estimated":
        cost *= _ESTIMATE_PENALTY
    return cost


def kill_switch_tripped(
    *,
    cum_cost_jpy: float,
    cum_earned_jpy: int,
    age_seconds: int,
    multiplier: int = 5,
    grace_seconds: int = _DEFAULT_GRACE_SECONDS,
) -> bool:
    """INV-11 token kill-switch.

    Returns True iff age_seconds >= grace_seconds AND cum_cost_jpy > multiplier * cum_earned_jpy.
    During grace (age < grace_seconds): always False (FIND-001 fix: brand-new slot is
    never killed on first pass with cum_earned_jpy=0).

    The dimensional intent is encoded in the param names (cum_*_jpy): both values are
    JPY amounts. Raw token counts must NOT be passed; the caller must convert tokens →
    JPY cost first via compute_token_cost_jpy.
    """
    if age_seconds < grace_seconds:
        return False
    return cum_cost_jpy > multiplier * cum_earned_jpy


def rolling_window(
    *,
    rows: list[dict],
    window_seconds: int,
    now_ts: int,
    data_floor_seconds: int = 86400,
) -> float | None:
    """Sum (jpy_earned − token_cost_jpy) over rows with ts in [now − window, now].

    Returns None if first row is younger than data_floor_seconds — preventing
    misleading partial-window numbers from gating SELF-SCALE decisions (REQ-B5).
    """
    if not rows:
        return None
    first_ts = min(int(r["ts"]) for r in rows)
    if (now_ts - first_ts) < data_floor_seconds:
        return None
    lo = now_ts - window_seconds
    total = 0.0
    for r in rows:
        ts = int(r["ts"])
        if lo <= ts <= now_ts:
            total += float(r.get("jpy_earned", 0)) - float(r.get("token_cost_jpy", 0))
    return total
