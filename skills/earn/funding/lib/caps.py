"""Pure money-safety cap logic for the claude-p -> Franklin funding pipeline. No I/O, no
network -- every function here takes plain data in and returns plain data out, so it is fully
unit-testable (see tests/test_caps.py).

Source of the rails this encodes: anicca-project docs/loop-engineering/11-parent-funding-loop.md
§3 ("MUST per-transfer cap / daily cap / cumulative cap ... 超えたら halt", "MUST reserve 保護").
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class CapDecision:
    allowed: bool
    reason: str
    amount_usd: float


def _sent_rows(history: Iterable[Mapping]) -> list[Mapping]:
    """Only rows whose status is 'sent' (a REAL, confirmed on-chain transfer) count toward
    spend totals. A 'failed'/'skipped'/'dry' row never moved money, so it must never consume
    cap headroom -- otherwise a failed attempt could wrongly block a later real transfer."""
    return [r for r in history if r.get("status") == "sent"]


def check_caps(
    *,
    amount_usd: float,
    history: Sequence[Mapping],
    config: Mapping,
    now_ts: float,
) -> CapDecision:
    """Evaluate `amount_usd` against per-transfer / daily / cumulative caps in `config`.

    `history` is the parsed funding-ledger.jsonl (list of row dicts with at least
    `ts` (epoch seconds), `amount_usd`, `status`). `config` has `per_transfer_usd_cap`,
    `daily_usd_cap`, `cumulative_usd_cap` (any of these may be None/absent to mean "no cap").
    """
    if not isinstance(amount_usd, (int, float)) or isinstance(amount_usd, bool) or amount_usd <= 0:
        return CapDecision(False, "amount_usd must be a positive number", amount_usd)

    per_cap = config.get("per_transfer_usd_cap")
    if per_cap is not None and amount_usd > per_cap:
        return CapDecision(
            False, f"amount ${amount_usd} exceeds per-transfer cap ${per_cap}", amount_usd
        )

    sent = _sent_rows(history)

    day_ago = now_ts - 86400
    daily_spent = sum(
        float(r.get("amount_usd", 0)) for r in sent if float(r.get("ts", 0)) >= day_ago
    )
    daily_cap = config.get("daily_usd_cap")
    if daily_cap is not None and daily_spent + amount_usd > daily_cap:
        return CapDecision(
            False,
            f"amount ${amount_usd} would exceed daily cap ${daily_cap} "
            f"(already spent ${daily_spent} in the last 24h)",
            amount_usd,
        )

    cumulative_spent = sum(float(r.get("amount_usd", 0)) for r in sent)
    cumulative_cap = config.get("cumulative_usd_cap")
    if cumulative_cap is not None and cumulative_spent + amount_usd > cumulative_cap:
        return CapDecision(
            False,
            f"amount ${amount_usd} would exceed cumulative cap ${cumulative_cap} "
            f"(already spent ${cumulative_spent} total)",
            amount_usd,
        )

    return CapDecision(True, "within all caps", amount_usd)


def reserve_protected_amount(*, available_usd: float, reserve_usd: float) -> float:
    """How much of `available_usd` may safely be moved while never dipping the source below
    `reserve_usd` (pm-earner's own working capital). Fails closed to 0.0, never negative."""
    if not isinstance(available_usd, (int, float)) or isinstance(available_usd, bool):
        return 0.0
    if not isinstance(reserve_usd, (int, float)) or isinstance(reserve_usd, bool):
        reserve_usd = 0.0
    return max(0.0, available_usd - reserve_usd)
