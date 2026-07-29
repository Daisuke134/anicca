#!/usr/bin/env python3
"""franklin_sol_base_refill.py -- operator-invoked, one-shot CLI: Franklin's OWN USDC (Solana
SPL) -> Franklin's OWN USDC (Base), via relay.link. The final funding step before the colony's
first on-chain loan (Franklin1 lender needs > $5.50 Base USDC).

Spec: .vcsdd/features/franklin-sol-base-refill/specs/behavioral-spec.md (REQ-001..007).
Copies the proven relay.link quote -> build+sign Solana tx (solders) -> submit -> poll
`/intents/status` pattern from `skills/earn/sol-to-usdc.py`, adapted from native-SOL input to
USDC-SPL input and from the automaton's shared wallet to Franklin's own, ANICCA_HOME-gated
identity. Reuses `skills/earn/funding/lib/{ledger,erc20,identity,kill_switch,solana_rpc}.py`
unchanged and appends to the SAME `skills/earn/state/funding-ledger.jsonl` with
`step="franklin_sol_base_refill"`.

NOT wired into any cron/loop/wake path -- operator/agent invokes this directly, one shot per
run (REQ-007). Money-critical caps ($6.50/invocation, $5.00 reserve, 8% max relay fee) are
fixed literals in `lib/refill_plan.py`, never CLI/env-overridable.

Usage:
  python3 franklin_sol_base_refill.py                    # dry-run (DEFAULT): quote + plan +
                                                           # cap evaluation only, no signing
  python3 franklin_sol_base_refill.py --live              # REAL: signs + broadcasts + verifies
  python3 franklin_sol_base_refill.py --live --amount-usd 3.0

Gas-ETH mode (REQ-GAS-001..005, added to fund an x402 facilitator's own signer wallet with Base
gas -- EIP-3009 gasless settlement has the FACILITATOR pay destination gas, so it must hold
native ETH): relays the SAME Franklin-own Solana USDC to Base NATIVE ETH (not USDC) delivered to
an explicit --recipient (never a default/citizens.json-derived address). Smaller, separate caps
($3.00/invocation, $3.00 source reserve, 12% max relay fee -- gas swaps are small so fee% runs
structurally higher). Verification differs from the USDC mode too: a native-ETH transfer emits
no ERC-20 Transfer log, so the independent on-chain proof is an `eth_getBalance` delta on the
recipient (>= 85% of the quote's expected wei output), not a parsed Transfer event.
  python3 franklin_sol_base_refill.py --gas-eth --recipient 0xFacilitatorSignerAddress...
  python3 franklin_sol_base_refill.py --gas-eth --recipient 0x... --live --amount-usd 2.0

Env: ANICCA_HOME (REQUIRED for --live and for any identity-dependent dry-run plan -- fail
closed, no shared-env fallback, see resolve_identity_secret()), SOLANA_RPC_URL, BASE_RPC_URL,
FRANKLIN_REFILL_CITIZENS_PATH (default ~/.hermes/state/citizens.json, unused in --gas-eth mode).

Output: exactly one JSON line on stdout. Exit 0 ONLY on a verified dry-run plan or a verified
live fill; non-zero otherwise.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Mapping, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lib.erc20 import (  # noqa: E402
    erc20_balance_units,
    eth_get_balance,
    eth_get_transaction_receipt,
    parse_erc20_transfer_amount,
)
from lib.identity import (  # noqa: E402
    derive_solana_pubkey_from_secret,
    keypair_from_secret_string,
    sanitized_secret_error,
)
from lib.kill_switch import is_killed  # noqa: E402
from lib.ledger import append_ledger, build_row, read_ledger  # noqa: E402
from lib.refill_plan import (  # noqa: E402
    GAS_FILL_MIN_DELIVERED_PCT,
    GAS_MAX_FEE_PCT,
    GAS_PER_INVOCATION_USD_CAP,
    GAS_RESERVE_USD,
    GAS_STEP,
    NATIVE_ETH_BASE,
    STEP,
    assert_own_citizen_row,
    build_refill_plan,
    evaluate_native_delivery,
    evaluate_relay_fee,
    has_unresolved_pending,
    is_valid_evm_address,
    select_refill_amount,
)
from lib.relay_swap import build_sign_submit_solana_tx  # noqa: E402
from lib.solana_rpc import spl_token_balance_units  # noqa: E402

REPO_ROOT = Path(os.environ.get("LIFE_MANAGER_REPO", Path(__file__).resolve().parents[3]))
LEDGER_PATH = str(REPO_ROOT / "skills/earn/state/funding-ledger.jsonl")
CITIZENS_PATH = os.environ.get(
    "FRANKLIN_REFILL_CITIZENS_PATH", os.path.expanduser("~/.hermes/state/citizens.json")
)
RESOLVE_IDENTITY_SCRIPT = os.path.normpath(
    os.path.join(HERE, "..", "lib", "resolve-identity.mjs")  # skills/earn/lib/resolve-identity.mjs
)

USDC_SOLANA_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDC_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
SOLANA_CHAIN_ID = 792703809
BASE_CHAIN_ID = 8453
SOLANA_RPC = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
BASE_RPC = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
RELAY_API = "https://api.relay.link"
# REQ-006/FIND-004: the PRIMARY fill check is tx-specific (the relay-reported fill tx's
# on-chain Transfer log to OUR address, see `parse_erc20_transfer_amount`) -- this is the
# minimum fraction of the quote's expected output that Transfer log amount must deliver to
# count as verified (relay solver credit timing/rounding can land a few % short of the quoted
# estimate; this is generous enough to absorb that without accepting a materially underfilled
# swap as "sent").
FILL_MIN_DELIVERED_PCT = 85.0
# The coarse wallet-wide balance delta is now a SECONDARY sanity check only (FIND-004): it
# cannot by itself distinguish this fill from an unrelated concurrent inflow/outflow on the
# same address, so it never gates "sent" -- it is only recorded for audit/anomaly-flagging
# alongside the tx-specific check above.
BALANCE_DELTA_TOLERANCE_PCT = 20.0


def resolve_live_flag(*, live: bool, dry_run: bool) -> bool:
    """REQ-007 edge case: `--dry-run` always wins over `--live` when both are passed. Pure,
    no I/O."""
    return bool(live) and not bool(dry_run)


def resolve_identity_secret(*, env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """REQ-001: THE sole source of the signing secret -- gated on ANICCA_HOME being explicitly
    set (fail closed, no `$HOME/.anicca` shared-default fallback), then delegates to the
    canonical `resolve-identity.mjs solana` CLI entrypoint (never a re-derived resolution
    path). No subprocess is ever spawned when the gate fails. Returns None (never raises) on
    any missing-env/subprocess/timeout failure -- callers must treat None as fail-closed
    refusal. The secret itself is never printed/logged by this function."""
    e = env if env is not None else os.environ
    if not e.get("ANICCA_HOME"):
        return None
    try:
        proc = subprocess.run(
            ["node", RESOLVE_IDENTITY_SCRIPT, "solana"],
            capture_output=True,
            text=True,
            timeout=15,
            env=dict(e),
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    secret = (proc.stdout or "").strip()
    return secret or None


def _extract_quote_usd(details: Mapping, key: str) -> Optional[float]:
    """REQ-004/FIND-001: extract a relay quote's reported `details.<key>.amountUsd` WITHOUT
    inventing a substitute value when the field is absent, non-numeric, or the wrong shape --
    returns None (never a locally-computed fallback like the requested swap amount) so
    `evaluate_relay_fee`'s fail-closed check on non-numeric input is actually exercised for the
    spec's named edge case ('missing details.currencyIn/currencyOut fields entirely: refuse')."""
    try:
        sub = details.get(key)
    except AttributeError:
        return None
    if not isinstance(sub, Mapping):
        return None
    raw = sub.get("amountUsd")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _extract_quote_raw_units(details: Mapping, key: str) -> Optional[int]:
    """REQ-GAS-004: extract a relay quote's reported `details.<key>.amount` (the RAW base-unit
    output, e.g. wei for a native-ETH `currencyOut` -- verified live 2026-07-11 against
    docs.relay.link's own Get Quote request/response example, both `/quote` and `/quote/v2`)
    WITHOUT inventing a substitute value when the field is absent, non-numeric, or the wrong
    shape -- mirrors `_extract_quote_usd`'s fail-closed contract exactly, but for the raw-unit
    amount the gas-ETH mode's native-balance-delta verification needs (unlike USDC, native ETH's
    market price is not ~1:1 with `amountUsd`, so the wei-denominated expected output cannot be
    derived from the USD figure)."""
    try:
        sub = details.get(key)
    except AttributeError:
        return None
    if not isinstance(sub, Mapping):
        return None
    raw = sub.get("amount")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _safe_append_ledger_factory(deps: Mapping[str, Callable]) -> Callable[[dict], None]:
    """Shared fail-closed ledger-append wrapper (FIND-003, impl iteration-2): a ledger-write
    failure must never crash the process with a bare, uncaught traceback -- it reports on
    stderr and exits non-zero deliberately, since there is no ledger row left to trust. Factored
    out so `run_gas_refill` gets the identical guarantee `run_refill`'s own inline copy already
    has, without touching that already-adversary-reviewed function's body."""

    def safe_append_ledger(row: dict) -> None:
        try:
            deps["append_ledger"](row)
        except Exception as exc:  # noqa: BLE001 -- fail closed, never crash bare (see docstring)
            print(
                f"FATAL: could not append ledger row (step={row.get('step')!r}, "
                f"status={row.get('status')!r}): {type(exc).__name__}",
                file=sys.stderr,
            )
            sys.exit(1)

    return safe_append_ledger


def run_refill(
    *,
    deps: Mapping[str, Callable],
    live: bool,
    amount_usd: Optional[float] = None,
) -> dict:
    """The full REQ-001..007 orchestration, over an injectable `deps` dict (never a real
    network/RPC/subprocess call directly -- see `build_default_deps()` for the production
    wiring and `tests/test_franklin_sol_base_refill.py` for the fully-fake test wiring).

    Required deps keys: is_killed, resolve_secret, derive_pubkey, read_citizens, read_ledger,
    append_ledger, read_solana_balance_usd, read_base_balance_units, relay_quote,
    poll_relay_status, read_base_tx_receipt, build_sign_submit.
    """

    # FIND-003 (impl iteration-2) / FIND-004 (impl iteration-3): a ledger-write failure
    # (disk-full/permissions on the underlying `open(path, 'a')`/`os.makedirs`) must never
    # crash the process uncaught -- `fail()` below calls this as its FIRST action on EVERY
    # refusal path, so an unguarded failure here would crash with a bare traceback at exactly
    # the moment we are trying to record a money-safety refusal, printing NO JSON line and
    # leaving NO audit trail at all -- strictly worse than every other already-fixed failure
    # mode in this module. Shares the SAME fail-closed wrapper `run_gas_refill` uses (impl
    # iteration-3 FIND-004 dedupe: this used to be a byte-for-byte-identical inline copy of
    # `_safe_append_ledger_factory`'s body kept separate to avoid re-touching this
    # already-adversary-reviewed function -- the two copies would otherwise have to be kept in
    # sync by hand forever; a single shared factory removes that drift risk with no behavior
    # change).
    safe_append_ledger = _safe_append_ledger_factory(deps)

    def fail(reason: str, extra: Optional[dict] = None, status: str = "failed") -> dict:
        row = build_row(
            step=STEP, amount_usd=amount_usd or 0, status=status, reason=reason, extra=extra or {}
        )
        safe_append_ledger(row)
        return {"ok": False, "step": STEP, "error": reason}

    try:
        killed = deps["is_killed"]()
    except Exception as exc:  # noqa: BLE001 -- FIND-003: an is_killed check failure must be
        # treated as killed=True (fail closed), never silently treated as "not killed".
        return fail(
            f"is_killed check raised, treating as killed (fail-closed): {type(exc).__name__}",
            status="skipped",
        )
    if killed:
        return fail("kill-switch present", status="skipped")

    secret = deps["resolve_secret"]()
    if not secret:
        return fail(
            "no Solana identity resolved (ANICCA_HOME gate failed or resolver returned "
            "nothing) -- fail-closed, never falling back to another instance"
        )

    try:
        sender_pubkey = deps["derive_pubkey"](secret)
    except Exception as exc:  # noqa: BLE001 -- any decode failure must fail closed, not raise
        return fail(
            sanitized_secret_error("could not derive Solana pubkey from resolved secret", exc)
        )
    if not sender_pubkey:
        return fail("resolved secret did not derive a usable Solana pubkey")

    try:
        citizens = deps["read_citizens"]()
    except Exception as exc:  # noqa: BLE001 -- REQ-002: missing/unreadable/malformed
        # citizens.json must fail closed with a ledger row, never crash uncaught.
        return fail(f"could not read citizens registry: {exc}")
    citizen_match = assert_own_citizen_row(citizens=citizens, derived_solana_pubkey=sender_pubkey)
    if not citizen_match.ok:
        return fail(f"citizens.json binding failed: {citizen_match.reason}")
    recipient_base = citizen_match.base_address

    if live:
        ledger_rows = deps["read_ledger"]()
        if has_unresolved_pending(ledger_rows=ledger_rows, step=STEP):
            return fail(
                "a previous franklin_sol_base_refill run is still pending on-chain "
                "confirmation (single in-flight guard)",
                status="skipped",
            )

    try:
        balance_usd = deps["read_solana_balance_usd"](sender_pubkey)
    except Exception as exc:  # noqa: BLE001 -- transient RPC failure must fail closed
        return fail(f"could not read live Solana USDC balance: {exc}", status="skipped")
    amount_decision = select_refill_amount(balance_usd=balance_usd, requested_usd=amount_usd)
    if not amount_decision.allowed:
        plan = build_refill_plan(
            sender_solana=sender_pubkey,
            recipient_base=recipient_base,
            amount_usd=0,
            balance_usd=balance_usd,
            cap_decision=amount_decision,
        )
        return fail(amount_decision.reason, {"plan": plan}, status="skipped")

    amount = amount_decision.amount_usd
    amount_units = int(round(amount * 1e6))

    try:
        quote = deps["relay_quote"](
            {
                "user": sender_pubkey,
                "recipient": recipient_base,
                "originChainId": SOLANA_CHAIN_ID,
                "destinationChainId": BASE_CHAIN_ID,
                "originCurrency": USDC_SOLANA_MINT,
                "destinationCurrency": USDC_BASE,
                "amount": str(amount_units),
                "tradeType": "EXACT_INPUT",
            }
        )
    except Exception as exc:  # noqa: BLE001 -- relay.link network error must fail closed
        plan = build_refill_plan(
            sender_solana=sender_pubkey,
            recipient_base=recipient_base,
            amount_usd=amount,
            balance_usd=balance_usd,
            cap_decision=amount_decision,
        )
        return fail(f"relay quote request raised: {exc}", {"plan": plan}, status="skipped")

    if quote is not None and not isinstance(quote, Mapping):
        # FIND-004 (impl iteration-2): a truthy non-Mapping quote (e.g. a JSON array, plausible
        # on a rate-limit/error response from a third-party API this feature has never
        # live-tested against) must refuse cleanly here, one level ABOVE where
        # `_extract_quote_usd`'s own AttributeError guard lives -- that inner guard never gets
        # a chance to run if `.get("details")` itself crashes first.
        plan = build_refill_plan(
            sender_solana=sender_pubkey,
            recipient_base=recipient_base,
            amount_usd=amount,
            balance_usd=balance_usd,
            cap_decision=amount_decision,
        )
        return fail(
            "relay quote returned a non-object response (malformed shape, cannot extract details)",
            {"plan": plan, "raw_quote": str(quote)[:300]},
            status="skipped",
        )
    details = (quote or {}).get("details") or {}
    if not details:
        plan = build_refill_plan(
            sender_solana=sender_pubkey,
            recipient_base=recipient_base,
            amount_usd=amount,
            balance_usd=balance_usd,
            cap_decision=amount_decision,
        )
        return fail(
            "relay quote failed or returned no details",
            {"plan": plan, "raw_quote": str(quote)[:300]},
            status="skipped",
        )

    in_usd = _extract_quote_usd(details, "currencyIn")
    out_usd = _extract_quote_usd(details, "currencyOut")
    fee_decision = evaluate_relay_fee(in_usd=in_usd, out_usd=out_usd)

    plan = build_refill_plan(
        sender_solana=sender_pubkey,
        recipient_base=recipient_base,
        amount_usd=amount,
        balance_usd=balance_usd,
        cap_decision=amount_decision,
        fee_decision=fee_decision,
        extra={"in_usd": in_usd, "out_usd": out_usd},
    )

    if not fee_decision.allowed:
        return fail(fee_decision.reason, {"plan": plan}, status="skipped")

    if not live:
        row = build_row(
            step=STEP,
            amount_usd=amount,
            status="dry",
            reason="dry-run: quote + plan + cap evaluation only, no signing/broadcast",
            from_addr=sender_pubkey,
            to_addr=recipient_base,
            extra={"plan": plan},
        )
        safe_append_ledger(row)
        return {"ok": True, "dry": True, "step": STEP, "plan": plan}

    # --- LIVE from here on ---
    try:
        step_data = (quote.get("steps") or [{}])[0]
        item = (step_data.get("items") or [{}])[0]
        check_endpoint = (item.get("check") or {}).get("endpoint")
    except Exception:  # noqa: BLE001 -- a malformed quote shape must not crash, just poll nothing
        check_endpoint = None

    try:
        base_balance_before = deps["read_base_balance_units"](recipient_base)
    except Exception as exc:  # noqa: BLE001
        return fail(
            f"could not read baseline Base USDC balance before broadcasting: {exc}",
            {"plan": plan},
            status="skipped",
        )

    try:
        signature = deps["build_sign_submit"](secret, quote)
    except Exception as exc:  # noqa: BLE001 -- nothing broadcast yet, safe to record as failed
        return fail(
            sanitized_secret_error("solana tx build/sign/submit failed", exc),
            {"plan": plan},
            status="failed",
        )

    # Finding-A pattern (money-safety adversary review, 2026-07-08, already applied to
    # bridge.py/send_to_franklin.py): the Solana tx is ALREADY broadcast at this point -- record
    # a 'pending' row with its signature BEFORE waiting for the relay fill/confirmation, so a
    # crash in the next block never leaves a real, already-broadcast transfer unlogged.
    safe_append_ledger(
        build_row(
            step=STEP,
            amount_usd=amount,
            status="pending",
            reason="solana tx broadcast, awaiting relay fill + independent Base balance confirmation",
            tx_hash=signature,
            from_addr=sender_pubkey,
            to_addr=recipient_base,
            extra={"plan": plan},
        )
    )

    try:
        relay_result = (
            deps["poll_relay_status"](check_endpoint) if check_endpoint else {"status": "unknown"}
        )
        fill_tx_hashes = (relay_result or {}).get("txHashes") or []
        fill_tx_hash = fill_tx_hashes[0] if fill_tx_hashes else None
        fill_receipt = deps["read_base_tx_receipt"](fill_tx_hash) if fill_tx_hash else None
        base_balance_after = deps["read_base_balance_units"](recipient_base)
    except Exception as exc:  # noqa: BLE001 -- the pending row above is already the audit trail
        return {
            "ok": False,
            "step": STEP,
            "error": (
                f"signature {signature} broadcast but confirmation check raised: {exc} -- "
                "needs manual reconciliation (see pending ledger row)"
            ),
            "signature": signature,
        }

    # FIND-004: PRIMARY check is tx-specific -- the relay-reported fill tx's own receipt must
    # be a success AND its USDC Transfer log must name OUR recipient address, delivering at
    # least FILL_MIN_DELIVERED_PCT of the quote's expected output. A coarse wallet-wide balance
    # delta cannot distinguish this fill from an unrelated concurrent inflow (a second
    # concurrent invocation, another earn engine crediting the same wallet, etc.) -- that delta
    # is now only a SECONDARY sanity check, recorded for audit but never itself the reason a
    # "sent" row is written.
    expected_units = int(round(out_usd * 1e6))
    min_delivered_units = (
        int(round(expected_units * (FILL_MIN_DELIVERED_PCT / 100))) if expected_units else 0
    )

    delivered_units = None
    tx_receipt_ok = False
    if fill_receipt:
        tx_receipt_ok = fill_receipt.get("status") == "0x1"
        delivered_units = parse_erc20_transfer_amount(
            logs=fill_receipt.get("logs") or [],
            token_address=USDC_BASE,
            to_address=recipient_base,
        )

    verified = (
        fill_tx_hash is not None
        and tx_receipt_ok
        and delivered_units is not None
        and (expected_units == 0 or delivered_units >= min_delivered_units)
    )

    delta_units = base_balance_after - base_balance_before
    tolerance_units = max(1, int(round(expected_units * (BALANCE_DELTA_TOLERANCE_PCT / 100))))
    balance_sanity_ok = delta_units > 0 and (
        expected_units == 0 or delta_units >= expected_units - tolerance_units
    )

    relay_status = (relay_result or {}).get("status")
    verification_extra = {
        "plan": plan,
        "relay_status": relay_status,
        "fill_tx_hash": fill_tx_hash,
        "delivered_units": delivered_units,
        "min_delivered_units": min_delivered_units,
        "base_balance_delta_units": delta_units,
        "base_balance_delta_sanity_ok": balance_sanity_ok,
    }

    if relay_status == "refund":
        row = build_row(
            step=STEP,
            amount_usd=amount,
            status="failed",
            reason="relay reported refund",
            tx_hash=signature,
            from_addr=sender_pubkey,
            to_addr=recipient_base,
            extra=verification_extra,
        )
        safe_append_ledger(row)
        return {"ok": False, "step": STEP, "error": row["reason"], "signature": signature}

    if not verified:
        row = build_row(
            step=STEP,
            amount_usd=amount,
            status="failed",
            reason=(
                "independent tx-specific fill check did not confirm the fill "
                f"(fill_tx_hash={fill_tx_hash}, receipt_status_ok={tx_receipt_ok}, "
                f"delivered={delivered_units} units, required>={min_delivered_units} units; "
                f"balance-delta sanity check: {balance_sanity_ok})"
            ),
            tx_hash=signature,
            from_addr=sender_pubkey,
            to_addr=recipient_base,
            extra=verification_extra,
        )
        safe_append_ledger(row)
        return {"ok": False, "step": STEP, "error": row["reason"], "signature": signature}

    row = build_row(
        step=STEP,
        amount_usd=amount,
        status="sent",
        reason=(
            "independently verified: relay fill tx receipt succeeded and its USDC Transfer "
            "log delivered the recipient at least the required amount"
        ),
        tx_hash=signature,
        from_addr=sender_pubkey,
        to_addr=recipient_base,
        extra=verification_extra,
    )
    safe_append_ledger(row)
    return {
        "ok": True,
        "step": STEP,
        "signature": signature,
        "amount_usd": amount,
        "plan": plan,
        "base_balance_delta_units": delta_units,
    }


def run_gas_refill(
    *,
    deps: Mapping[str, Callable],
    live: bool,
    recipient: Optional[str],
    amount_usd: Optional[float] = None,
) -> dict:
    """Gas-ETH mode (spec: behavioral-spec.md REQ-GAS-001..005) -- the same Franklin-own
    Solana-USDC source leg as `run_refill`, but swapped to Base NATIVE ETH and delivered to an
    EXPLICIT `recipient` (e.g. the x402 facilitator's own signer wallet, which needs Base ETH to
    pay destination gas for EIP-3009 gasless settlement) rather than a citizens.json-bound own
    address. There is deliberately NO default recipient and NO citizens.json lookup for this
    mode -- the caller must name the destination explicitly every time (REQ-GAS-002).

    Required deps keys (a strict subset of `run_refill`'s -- no `read_citizens`, no
    `read_base_balance_units`/ERC-20 receipt-log parsing; uses `read_base_native_balance_wei`
    instead, and reuses `read_base_tx_receipt`/`build_sign_submit`/`relay_quote`/
    `poll_relay_status` unchanged): is_killed, resolve_secret, derive_pubkey, read_ledger,
    append_ledger, read_solana_balance_usd, read_base_native_balance_wei, relay_quote,
    poll_relay_status, read_base_tx_receipt, build_sign_submit.
    """
    safe_append_ledger = _safe_append_ledger_factory(deps)

    def fail(reason: str, extra: Optional[dict] = None, status: str = "failed") -> dict:
        row = build_row(
            step=GAS_STEP, amount_usd=amount_usd or 0, status=status, reason=reason, extra=extra or {}
        )
        safe_append_ledger(row)
        return {"ok": False, "step": GAS_STEP, "error": reason}

    try:
        killed = deps["is_killed"]()
    except Exception as exc:  # noqa: BLE001 -- fail closed, treat as killed=True (mirrors run_refill)
        return fail(
            f"is_killed check raised, treating as killed (fail-closed): {type(exc).__name__}",
            status="skipped",
        )
    if killed:
        return fail("kill-switch present", status="skipped")

    # REQ-GAS-002: recipient is required and validated BEFORE any subprocess/network call --
    # gas-ETH mode has no citizens.json binding to fall back on, so a missing/malformed
    # --recipient must refuse immediately, exactly like REQ-001's ANICCA_HOME gate refuses
    # before spawning a subprocess. FIND-003 (impl iteration-3): `is_valid_evm_address` returns
    # the NORMALIZED (stripped, lower-cased) address on success -- rebind `recipient` to that
    # return value immediately so EVERY downstream use (relay payload, build_sign_submit,
    # every ledger row's to_addr) sees the SAME normalized string that was actually validated,
    # never the original raw argv value.
    normalized_recipient = is_valid_evm_address(recipient)
    if not normalized_recipient:
        return fail(
            "recipient is required in gas-ETH mode and must be a valid Base EVM address "
            "(0x + 40 hex chars) -- there is no default destination"
        )
    recipient = normalized_recipient

    secret = deps["resolve_secret"]()
    if not secret:
        return fail(
            "no Solana identity resolved (ANICCA_HOME gate failed or resolver returned "
            "nothing) -- fail-closed, never falling back to another instance"
        )

    try:
        sender_pubkey = deps["derive_pubkey"](secret)
    except Exception as exc:  # noqa: BLE001 -- any decode failure must fail closed, not raise
        return fail(
            sanitized_secret_error("could not derive Solana pubkey from resolved secret", exc)
        )
    if not sender_pubkey:
        return fail("resolved secret did not derive a usable Solana pubkey")

    if live:
        ledger_rows = deps["read_ledger"]()
        if has_unresolved_pending(ledger_rows=ledger_rows, step=GAS_STEP):
            return fail(
                "a previous franklin_gas_eth_refill run is still pending on-chain "
                "confirmation (single in-flight guard)",
                status="skipped",
            )

    try:
        balance_usd = deps["read_solana_balance_usd"](sender_pubkey)
    except Exception as exc:  # noqa: BLE001 -- transient RPC failure must fail closed
        return fail(f"could not read live Solana USDC balance: {exc}", status="skipped")
    amount_decision = select_refill_amount(
        balance_usd=balance_usd,
        requested_usd=amount_usd,
        reserve_usd=GAS_RESERVE_USD,
        per_invocation_cap_usd=GAS_PER_INVOCATION_USD_CAP,
    )
    if not amount_decision.allowed:
        plan = build_refill_plan(
            sender_solana=sender_pubkey,
            recipient_base=recipient,
            amount_usd=0,
            balance_usd=balance_usd,
            cap_decision=amount_decision,
        )
        return fail(amount_decision.reason, {"plan": plan}, status="skipped")

    amount = amount_decision.amount_usd
    amount_units = int(round(amount * 1e6))  # source leg is still Solana USDC (6 decimals)

    try:
        quote = deps["relay_quote"](
            {
                "user": sender_pubkey,
                "recipient": recipient,
                "originChainId": SOLANA_CHAIN_ID,
                "destinationChainId": BASE_CHAIN_ID,
                "originCurrency": USDC_SOLANA_MINT,
                "destinationCurrency": NATIVE_ETH_BASE,
                "amount": str(amount_units),
                "tradeType": "EXACT_INPUT",
            }
        )
    except Exception as exc:  # noqa: BLE001 -- relay.link network error must fail closed
        plan = build_refill_plan(
            sender_solana=sender_pubkey,
            recipient_base=recipient,
            amount_usd=amount,
            balance_usd=balance_usd,
            cap_decision=amount_decision,
        )
        return fail(f"relay quote request raised: {exc}", {"plan": plan}, status="skipped")

    if quote is not None and not isinstance(quote, Mapping):
        # Mirrors run_refill's FIND-004 (iteration-2) guard: a truthy non-Mapping quote must
        # refuse cleanly here, one level above _extract_quote_usd/_extract_quote_raw_units'
        # own AttributeError guards.
        plan = build_refill_plan(
            sender_solana=sender_pubkey,
            recipient_base=recipient,
            amount_usd=amount,
            balance_usd=balance_usd,
            cap_decision=amount_decision,
        )
        return fail(
            "relay quote returned a non-object response (malformed shape, cannot extract details)",
            {"plan": plan, "raw_quote": str(quote)[:300]},
            status="skipped",
        )
    details = (quote or {}).get("details") or {}
    if not details:
        plan = build_refill_plan(
            sender_solana=sender_pubkey,
            recipient_base=recipient,
            amount_usd=amount,
            balance_usd=balance_usd,
            cap_decision=amount_decision,
        )
        return fail(
            "relay quote failed or returned no details",
            {"plan": plan, "raw_quote": str(quote)[:300]},
            status="skipped",
        )

    in_usd = _extract_quote_usd(details, "currencyIn")
    out_usd = _extract_quote_usd(details, "currencyOut")
    expected_wei = _extract_quote_raw_units(details, "currencyOut")
    fee_decision = evaluate_relay_fee(in_usd=in_usd, out_usd=out_usd, max_fee_pct=GAS_MAX_FEE_PCT)

    plan = build_refill_plan(
        sender_solana=sender_pubkey,
        recipient_base=recipient,
        amount_usd=amount,
        balance_usd=balance_usd,
        cap_decision=amount_decision,
        fee_decision=fee_decision,
        extra={"in_usd": in_usd, "out_usd": out_usd, "expected_wei": expected_wei},
    )

    if not fee_decision.allowed:
        return fail(fee_decision.reason, {"plan": plan}, status="skipped")

    if not live:
        row = build_row(
            step=GAS_STEP,
            amount_usd=amount,
            status="dry",
            reason="dry-run: quote + plan + cap evaluation only, no signing/broadcast",
            from_addr=sender_pubkey,
            to_addr=recipient,
            extra={"plan": plan},
        )
        safe_append_ledger(row)
        return {"ok": True, "dry": True, "step": GAS_STEP, "plan": plan}

    # --- LIVE from here on ---
    # FIND-002 (impl iteration-3): a PRESENT-but-non-positive expected_wei (relay quirk/bug
    # returning `amount: "0"` or a negative string) must refuse here too, symmetric with the
    # `expected_wei is None` guard -- `evaluate_native_delivery` now also fails closed on
    # expected_wei <= 0, but that guard must never be the ONLY thing standing between a
    # degenerate quote and a real broadcast; refuse before signing, not just before verifying.
    if expected_wei is None or expected_wei <= 0:
        return fail(
            "relay quote missing/malformed or non-positive details.currencyOut.amount (raw "
            "wei) -- cannot independently verify native-ETH delivery, refusing before signing",
            {"plan": plan},
            status="skipped",
        )

    try:
        step_data = (quote.get("steps") or [{}])[0]
        item = (step_data.get("items") or [{}])[0]
        check_endpoint = (item.get("check") or {}).get("endpoint")
    except Exception:  # noqa: BLE001 -- a malformed quote shape must not crash, just poll nothing
        check_endpoint = None

    try:
        base_native_wei_before = deps["read_base_native_balance_wei"](recipient)
    except Exception as exc:  # noqa: BLE001
        return fail(
            f"could not read baseline Base native-ETH balance before broadcasting: {exc}",
            {"plan": plan},
            status="skipped",
        )

    try:
        signature = deps["build_sign_submit"](secret, quote)
    except Exception as exc:  # noqa: BLE001 -- nothing broadcast yet, safe to record as failed
        return fail(
            sanitized_secret_error("solana tx build/sign/submit failed", exc),
            {"plan": plan},
            status="failed",
        )

    # Finding-A pattern (money-safety adversary review, 2026-07-08), same as run_refill: the
    # Solana tx is ALREADY broadcast at this point -- record a 'pending' row with its signature
    # BEFORE waiting for the relay fill/confirmation, so a crash in the next block never leaves
    # a real, already-broadcast transfer unlogged.
    safe_append_ledger(
        build_row(
            step=GAS_STEP,
            amount_usd=amount,
            status="pending",
            reason="solana tx broadcast, awaiting relay fill + independent Base native-ETH "
            "balance confirmation",
            tx_hash=signature,
            from_addr=sender_pubkey,
            to_addr=recipient,
            extra={"plan": plan},
        )
    )

    try:
        relay_result = (
            deps["poll_relay_status"](check_endpoint) if check_endpoint else {"status": "unknown"}
        )
        fill_tx_hashes = (relay_result or {}).get("txHashes") or []
        fill_tx_hash = fill_tx_hashes[0] if fill_tx_hashes else None
        fill_receipt = deps["read_base_tx_receipt"](fill_tx_hash) if fill_tx_hash else None
        base_native_wei_after = deps["read_base_native_balance_wei"](recipient)
    except Exception as exc:  # noqa: BLE001 -- the pending row above is already the audit trail
        return {
            "ok": False,
            "step": GAS_STEP,
            "error": (
                f"signature {signature} broadcast but confirmation check raised: {exc} -- "
                "needs manual reconciliation (see pending ledger row)"
            ),
            "signature": signature,
        }

    tx_receipt_ok = bool(fill_receipt) and fill_receipt.get("status") == "0x1"
    delivery = evaluate_native_delivery(
        balance_before_wei=base_native_wei_before,
        balance_after_wei=base_native_wei_after,
        expected_wei=expected_wei,
        min_delivered_pct=GAS_FILL_MIN_DELIVERED_PCT,
    )
    verified = fill_tx_hash is not None and tx_receipt_ok and delivery.verified

    relay_status = (relay_result or {}).get("status")
    verification_extra = {
        "plan": plan,
        "relay_status": relay_status,
        "fill_tx_hash": fill_tx_hash,
        "delivered_wei": delivery.delivered_wei,
        "min_required_wei": delivery.min_required_wei,
        "native_balance_delta_verified": delivery.verified,
    }

    if relay_status == "refund":
        row = build_row(
            step=GAS_STEP,
            amount_usd=amount,
            status="failed",
            reason="relay reported refund",
            tx_hash=signature,
            from_addr=sender_pubkey,
            to_addr=recipient,
            extra=verification_extra,
        )
        safe_append_ledger(row)
        return {"ok": False, "step": GAS_STEP, "error": row["reason"], "signature": signature}

    if not verified:
        row = build_row(
            step=GAS_STEP,
            amount_usd=amount,
            status="failed",
            reason=(
                "independent native-ETH balance-delta check did not confirm the fill "
                f"(fill_tx_hash={fill_tx_hash}, receipt_status_ok={tx_receipt_ok}, "
                f"delivery: {delivery.reason})"
            ),
            tx_hash=signature,
            from_addr=sender_pubkey,
            to_addr=recipient,
            extra=verification_extra,
        )
        safe_append_ledger(row)
        return {"ok": False, "step": GAS_STEP, "error": row["reason"], "signature": signature}

    row = build_row(
        step=GAS_STEP,
        amount_usd=amount,
        status="sent",
        reason=(
            "independently verified: relay fill tx receipt succeeded and the recipient's "
            "Base native-ETH balance increased by at least the required fraction of the "
            "quoted output"
        ),
        tx_hash=signature,
        from_addr=sender_pubkey,
        to_addr=recipient,
        extra=verification_extra,
    )
    safe_append_ledger(row)
    return {
        "ok": True,
        "step": GAS_STEP,
        "signature": signature,
        "amount_usd": amount,
        "plan": plan,
        "delivered_wei": delivery.delivered_wei,
    }


def build_default_deps() -> dict:
    """Production wiring -- the only place this file makes real subprocess/RPC/relay calls."""
    import requests

    def resolve_secret():
        return resolve_identity_secret()

    def read_citizens():
        with open(CITIZENS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def read_ledger_rows():
        return read_ledger(LEDGER_PATH)

    def append(row: dict):
        append_ledger(LEDGER_PATH, row)

    def read_solana_balance_usd(pubkey: str) -> float:
        units = spl_token_balance_units(SOLANA_RPC, pubkey, USDC_SOLANA_MINT)
        return units / 1e6

    def read_base_balance_units(address: str) -> int:
        return erc20_balance_units(BASE_RPC, USDC_BASE, address)

    def relay_quote(payload: dict) -> dict:
        return requests.post(f"{RELAY_API}/quote", json=payload, timeout=30).json()

    def poll_relay_status(check_endpoint: str) -> dict:
        url = f"{RELAY_API}{check_endpoint}"
        status = {"status": "timeout"}
        for _ in range(60):
            time.sleep(3)
            status = requests.get(url, timeout=30).json()
            if status.get("status") in ("success", "refund"):
                break
        return status

    def read_base_tx_receipt(tx_hash: str):
        return eth_get_transaction_receipt(BASE_RPC, tx_hash)

    def read_base_native_balance_wei(address: str) -> int:
        """REQ-GAS-004: gas-ETH mode's independent verification read -- raw wei balance of
        `address`'s Base NATIVE ETH (not an ERC-20 token), read before and after broadcast."""
        return eth_get_balance(BASE_RPC, address)

    def build_sign_submit(secret: str, quote: dict) -> str:
        return build_sign_submit_solana_tx(secret, quote, SOLANA_RPC)

    return {
        "is_killed": lambda: is_killed(HERE),
        "resolve_secret": resolve_secret,
        "derive_pubkey": derive_solana_pubkey_from_secret,
        "read_citizens": read_citizens,
        "read_ledger": read_ledger_rows,
        "append_ledger": append,
        "read_solana_balance_usd": read_solana_balance_usd,
        "read_base_balance_units": read_base_balance_units,
        "read_base_native_balance_wei": read_base_native_balance_wei,
        "relay_quote": relay_quote,
        "poll_relay_status": poll_relay_status,
        "read_base_tx_receipt": read_base_tx_receipt,
        "build_sign_submit": build_sign_submit,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="sign + broadcast + verify for real")
    parser.add_argument(
        "--dry-run", action="store_true", help="explicit no-op override; always wins over --live"
    )
    parser.add_argument("--amount-usd", type=float, default=None)
    parser.add_argument(
        "--gas-eth",
        action="store_true",
        help=(
            "gas-ETH mode: relay Franklin's own Solana USDC -> Base NATIVE ETH to --recipient "
            "(e.g. an x402 facilitator's own signer wallet that needs Base ETH for destination "
            "gas), instead of the default USDC -> USDC refill mode"
        ),
    )
    parser.add_argument(
        "--recipient",
        type=str,
        default=None,
        help=(
            "REQUIRED with --gas-eth: the Base EVM address to receive native ETH. There is no "
            "default -- must be passed explicitly every invocation."
        ),
    )
    args = parser.parse_args()

    live = resolve_live_flag(live=args.live, dry_run=args.dry_run)
    deps = build_default_deps()
    if args.gas_eth:
        result = run_gas_refill(
            deps=deps, live=live, recipient=args.recipient, amount_usd=args.amount_usd
        )
    else:
        result = run_refill(deps=deps, live=live, amount_usd=args.amount_usd)
    print(json.dumps(result))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
