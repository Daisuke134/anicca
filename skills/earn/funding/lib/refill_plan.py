"""Pure money-safety cap/plan logic for franklin_sol_base_refill.py -- the Franklin-own-wallet
Solana USDC -> Base USDC refill (spec: .vcsdd/features/franklin-sol-base-refill/specs/
behavioral-spec.md REQ-002..007). No I/O, no network, no clock reads inside these functions
(callers always pass a live-read balance/quote/ledger snapshot in) -- fully unit-testable in
isolation, mirroring the existing `lib/caps.py`/`lib/ledger.py` purity convention in this same
skill.

These caps are deliberately separate, fixed constants from `config.json`'s
per_transfer_usd_cap/daily_usd_cap/cumulative_usd_cap (the claude-p -> Franklin PM-capital
pipeline) -- this feature moves Franklin's OWN Solana USDC to Franklin's OWN Base USDC, a
different money path with its own literal caps that are never CLI/env-overridable (mirrors
`skills/self/spawn-funding-swap/lib/driver.mjs`'s documented "fixed literals, never
process.env-overridable" precedent for money-critical constants).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

# REQ-003: amount <= $6.50 per invocation; post-swap Solana USDC balance must remain >= $5.00.
PER_INVOCATION_USD_CAP = 6.50
RESERVE_USD = 5.00
# REQ-004: refuse if relay quote's total cost (fee) exceeds 8% of the amount being swapped.
MAX_FEE_PCT = 8.0
# REQ-005/REQ-006: the ledger `step` value every row this feature writes uses.
STEP = "franklin_sol_base_refill"


@dataclass(frozen=True)
class AmountDecision:
    allowed: bool
    reason: str
    amount_usd: float


def select_refill_amount(
    *,
    balance_usd,
    requested_usd: Optional[float] = None,
    reserve_usd: float = RESERVE_USD,
    per_invocation_cap_usd: float = PER_INVOCATION_USD_CAP,
) -> AmountDecision:
    """REQ-003: derive the refill amount from a LIVE balance, never exceeding
    `per_invocation_cap_usd` and never leaving less than `reserve_usd` behind. Fails closed
    (amount_usd == 0.0) on any non-numeric input, non-positive explicit request, or when the
    live balance does not clear the reserve at all."""
    if not isinstance(balance_usd, (int, float)) or isinstance(balance_usd, bool):
        return AmountDecision(False, "balance_usd must be a number", 0.0)

    if requested_usd is not None:
        if (
            not isinstance(requested_usd, (int, float))
            or isinstance(requested_usd, bool)
            or requested_usd <= 0
        ):
            return AmountDecision(False, "requested_usd must be a positive number", 0.0)

    headroom = balance_usd - reserve_usd
    if headroom <= 0:
        return AmountDecision(
            False,
            f"balance ${balance_usd} would not leave the ${reserve_usd} reserve intact",
            0.0,
        )

    ceiling = min(headroom, per_invocation_cap_usd)
    amount = ceiling if requested_usd is None else min(requested_usd, ceiling)
    amount = round(amount, 6)

    if amount <= 0:
        return AmountDecision(False, "no headroom available after reserve/cap", 0.0)

    return AmountDecision(True, "within caps", amount)


@dataclass(frozen=True)
class FeeDecision:
    allowed: bool
    reason: str
    fee_pct: Optional[float]


def evaluate_relay_fee(*, in_usd, out_usd, max_fee_pct: float = MAX_FEE_PCT) -> FeeDecision:
    """REQ-004: `fee_pct = (in_usd - out_usd) / in_usd * 100`. Refuses when fee_pct exceeds
    `max_fee_pct`, or when the quote's amounts are missing/non-numeric/non-positive (cannot
    verify economics at all -> fail closed, never assume a quote is fine)."""
    if not isinstance(in_usd, (int, float)) or isinstance(in_usd, bool) or in_usd <= 0:
        return FeeDecision(False, "quote missing/invalid currencyIn amountUsd", None)
    if not isinstance(out_usd, (int, float)) or isinstance(out_usd, bool):
        return FeeDecision(False, "quote missing/invalid currencyOut amountUsd", None)

    fee_usd = max(0.0, in_usd - out_usd)
    fee_pct = fee_usd / in_usd * 100

    if fee_pct > max_fee_pct:
        return FeeDecision(
            False, f"relay fee {fee_pct:.3f}% exceeds cap {max_fee_pct}%", fee_pct
        )
    return FeeDecision(True, "within fee cap", fee_pct)


@dataclass(frozen=True)
class CitizenMatch:
    ok: bool
    reason: str
    citizen_id: Optional[str]
    base_address: Optional[str]


def assert_own_citizen_row(
    *, citizens: Sequence[Mapping], derived_solana_pubkey: str
) -> CitizenMatch:
    """REQ-002: the ONLY way this feature learns a Base destination address -- looks up the
    citizens.json row whose walletAddress.solana equals the pubkey ACTUALLY derived from the
    resolved signing secret (never a hardcoded/display address). Fails closed on zero matches,
    on more than one match (ambiguous -- never "pick the first"), and on a matched row with no
    walletAddress.evm at all."""
    if not derived_solana_pubkey:
        return CitizenMatch(False, "no derived Solana pubkey to match", None, None)

    matches = [
        c
        for c in citizens
        if isinstance(c, Mapping)
        and isinstance(c.get("walletAddress"), Mapping)
        and c["walletAddress"].get("solana") == derived_solana_pubkey
    ]

    if len(matches) == 0:
        return CitizenMatch(
            False,
            f"no citizens.json row has walletAddress.solana == {derived_solana_pubkey}",
            None,
            None,
        )
    if len(matches) > 1:
        return CitizenMatch(
            False,
            f"{len(matches)} citizens.json rows match {derived_solana_pubkey} (ambiguous, refusing)",
            None,
            None,
        )

    row = matches[0]
    citizen_id = row.get("id")
    base_address = row.get("walletAddress", {}).get("evm")
    if not base_address:
        return CitizenMatch(
            False, f"matched citizen {citizen_id} has no walletAddress.evm", citizen_id, None
        )

    return CitizenMatch(True, "matched own citizens.json row", citizen_id, base_address)


def has_unresolved_pending(*, ledger_rows: Sequence[Mapping], step: str = STEP) -> bool:
    """REQ-005: single in-flight guard. A row is "unresolved pending" if it has status
    'pending' for `step` and no LATER row of the same step/tx identifier reaches a terminal
    status ('sent' or 'failed'). A pending row with no tx identifier at all always blocks (it
    can never be matched to a later terminal row, so it can never be proven resolved).
    Order-independent: scans the whole ledger, not just the tail."""
    pending_ids = set()
    terminal_ids = set()
    untracked_pending = 0

    for row in ledger_rows:
        if not isinstance(row, Mapping) or row.get("step") != step:
            continue
        status = row.get("status")
        tx_id = row.get("tx_hash")
        if status == "pending":
            if tx_id:
                pending_ids.add(tx_id)
            else:
                untracked_pending += 1
        elif status in ("sent", "failed"):
            if tx_id:
                terminal_ids.add(tx_id)

    if untracked_pending > 0:
        return True
    return len(pending_ids - terminal_ids) > 0


def build_refill_plan(
    *,
    sender_solana: str,
    recipient_base: str,
    amount_usd: float,
    balance_usd: float,
    cap_decision: AmountDecision,
    fee_decision: Optional[FeeDecision] = None,
    extra: Optional[Mapping] = None,
) -> dict:
    """Pure assembly of the plan object logged before any signing (REQ-006/REQ-007). Never
    mutates `extra` (matches `lib/ledger.py`'s `build_row` non-mutation contract)."""
    plan = {
        "sender_solana": sender_solana,
        "recipient_base": recipient_base,
        "amount_usd": amount_usd,
        "balance_usd": balance_usd,
        "cap_allowed": cap_decision.allowed,
        "cap_reason": cap_decision.reason,
        "fee_pct": fee_decision.fee_pct if fee_decision is not None else None,
        "fee_allowed": fee_decision.allowed if fee_decision is not None else None,
        "fee_reason": fee_decision.reason if fee_decision is not None else None,
    }
    if extra:
        plan = {**plan, **extra}
    return plan
