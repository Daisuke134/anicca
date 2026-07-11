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

# REQ-GAS-002: gas-ETH mode (Solana USDC -> Base NATIVE ETH, funding an arbitrary --recipient,
# e.g. the x402 facilitator's own signer wallet, rather than Franklin's own citizens.json-bound
# Base address). Deliberately separate, smaller, fixed literals from the USDC-mode caps above --
# gas top-ups are small by design and relay's fee% runs structurally higher on small transfers
# (fixed solver/gas overhead is a bigger fraction of a small amount), so the fee ceiling is
# wider but the absolute per-invocation amount is much smaller. Never CLI/env-overridable, same
# convention as PER_INVOCATION_USD_CAP/RESERVE_USD/MAX_FEE_PCT above.
GAS_STEP = "franklin_gas_eth_refill"
GAS_PER_INVOCATION_USD_CAP = 3.00
GAS_RESERVE_USD = 3.00
GAS_MAX_FEE_PCT = 12.0
# The minimum fraction of the quote's expected native-ETH output that the independent
# eth_getBalance delta must show as delivered before a gas-ETH run is recorded "sent" -- same
# rationale/value as USDC mode's FILL_MIN_DELIVERED_PCT (relay solver credit timing/rounding can
# land a few % short of the quoted estimate without it being a materially underfilled top-up).
GAS_FILL_MIN_DELIVERED_PCT = 85.0
# relay.link's documented sentinel for "the chain's native currency" in `/quote` requests
# (verified live 2026-07-11 against docs.relay.link's own Get Quote example request/response:
# `originCurrency`/`destinationCurrency`: "0x0000000000000000000000000000000000000000" swaps a
# chain's native ETH -- https://docs.relay.link/references/api/get-quote and
# .../get-quote-v2, identical request/response shape on both). Base's chain id is 8453
# (BASE_CHAIN_ID, already defined in franklin_sol_base_refill.py).
NATIVE_ETH_BASE = "0x0000000000000000000000000000000000000000"


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


def is_valid_evm_address(candidate) -> Optional[str]:
    """REQ-GAS-002: pure, deterministic parse of a fixed on-chain machine format (a hex EVM
    address string) -- NOT a judgment call (see rules/building-effective-ai-agents.md's
    judgment-regex vs fixed-format-parsing distinction). Used to fail closed on a missing/
    malformed `--recipient` BEFORE any network call, since gas-ETH mode has no citizens.json
    binding to derive/validate the destination address from -- the CLI argument IS the sole
    source of truth and must be checked directly.

    Returns the NORMALIZED (`.strip()`-ped, lower-cased) address string on success, or `None`
    on any validation failure -- never a bare bool (impl iteration-3 FIND-003 fix). Validating a
    stripped local copy but returning only `True`/`False` let every downstream caller keep using
    the ORIGINAL, unstripped/mixed-case argument, so a whitespace-padded or differently-cased but
    otherwise well-formed `--recipient` would pass validation yet reach the relay payload/signing
    call/ledger rows verbatim, unnormalized. Callers MUST bind the RETURN VALUE (never the
    original candidate) to every downstream use. No EIP-55 checksum verification is performed --
    lower-casing intentionally discards any checksum casing information; this is a documented,
    accepted residual (REQ-GAS-002 acceptance criteria / FIND-005), not an oversight."""
    if not isinstance(candidate, str):
        return None
    c = candidate.strip()
    if not c.startswith("0x") or len(c) != 42:
        return None
    try:
        int(c[2:], 16)
    except ValueError:
        return None
    return c.lower()


@dataclass(frozen=True)
class NativeDeliveryDecision:
    verified: bool
    reason: str
    delivered_wei: int
    min_required_wei: int


def evaluate_native_delivery(
    *,
    balance_before_wei,
    balance_after_wei,
    expected_wei,
    min_delivered_pct: float = GAS_FILL_MIN_DELIVERED_PCT,
) -> NativeDeliveryDecision:
    """REQ-GAS-004: the independent on-chain verification for a NATIVE-ETH gas top-up. Unlike
    the USDC leg (an ERC-20 `Transfer` event log to parse via `parse_erc20_transfer_amount` in
    `lib/erc20.py`), a plain native-currency transfer emits NO event log at all -- there is no
    finer-grained on-chain signal available than the recipient's own `eth_getBalance` delta, so
    the delta itself IS the tx-specific evidence here (mirrors the USDC leg's FILL_MIN_DELIVERED_PCT
    floor, applied to the delta instead of a parsed Transfer amount). Pure (no I/O) -- callers
    always pass in already-read before/after balances and the quote's expected raw output.
    Fails closed on any non-int input, a non-positive `expected_wei` (impl iteration-3
    FIND-002 fix -- see below), a non-positive delta, or a delta below `min_delivered_pct` of
    `expected_wei`."""
    for name, val in (
        ("balance_before_wei", balance_before_wei),
        ("balance_after_wei", balance_after_wei),
        ("expected_wei", expected_wei),
    ):
        if not isinstance(val, int) or isinstance(val, bool):
            return NativeDeliveryDecision(False, f"{name} must be an int (wei)", 0, 0)

    # FIND-002 (impl iteration-3): expected_wei <= 0 must be a REFUSAL, not a bypass. The
    # previous `min_required = 0 if expected_wei <= 0 else ...` shape made the 85% floor a
    # no-op whenever expected_wei was zero/negative, so ANY positive balance delta -- even
    # 1 wei -- fell through to "verified: True". There is no expected output to verify
    # delivery against when expected_wei is non-positive, so this must fail closed exactly
    # like the non-int type check above, never silently compute min_required=0.
    if expected_wei <= 0:
        return NativeDeliveryDecision(
            False,
            f"expected_wei must be a positive int (wei), got {expected_wei} -- cannot verify "
            "delivery against a non-positive expected output",
            0,
            0,
        )

    delivered = balance_after_wei - balance_before_wei
    min_required = int(round(expected_wei * (min_delivered_pct / 100)))

    if delivered <= 0:
        return NativeDeliveryDecision(
            False,
            f"recipient Base native-ETH balance did not increase (delta={delivered} wei)",
            delivered,
            min_required,
        )
    if delivered < min_required:
        return NativeDeliveryDecision(
            False,
            f"delivered {delivered} wei < required {min_required} wei "
            f"({min_delivered_pct}% of expected {expected_wei} wei)",
            delivered,
            min_required,
        )
    return NativeDeliveryDecision(
        True, "balance delta meets minimum delivered threshold", delivered, min_required
    )
