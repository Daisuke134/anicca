"""Orchestration tests for franklin_sol_base_refill.py's `--gas-eth` mode (run_gas_refill),
spec: .vcsdd/features/franklin-sol-base-refill/specs/behavioral-spec.md REQ-GAS-001..005.

Mirrors tests/test_franklin_sol_base_refill.py's fully-fake, injectable `deps` convention (no
real network/RPC/subprocess calls, no real keys, no real ledger file outside tmp_path) -- kept
in a separate file (many-small-files convention) since the USDC-mode suite is already large and
gas mode's deps shape genuinely differs (no read_citizens, native-balance reads instead of
ERC-20 balance/Transfer-log reads).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from franklin_sol_base_refill import (  # noqa: E402
    GAS_STEP,
    STEP,
    resolve_live_flag,
    run_gas_refill,
)
from lib.ledger import append_ledger, build_row, read_ledger  # noqa: E402

RECIPIENT = "0x1F5b17f41524B02a4ee4d99D4158c86C942e43f3"
SENDER_PUBKEY = "FakeSenderPubkey1111111111111111111111111"
FILL_TX_HASH = "0xdeaddeaddeaddeaddeaddeaddeaddeaddeaddeaddeaddeaddeaddeaddeaddead"
EXPECTED_WEI = 700_000_000_000_000  # ~0.0007 ETH, arbitrary but realistic for a $2.xx gas top-up


def make_gas_deps(tmp_path, **overrides):
    ledger_path = str(tmp_path / "funding-ledger.jsonl")
    call_log = []

    def append_ledger_row(row):
        call_log.append(("append_ledger", row.get("status")))
        append_ledger(ledger_path, row)

    def read_ledger_rows():
        return read_ledger(ledger_path)

    def default_quote(payload):
        call_log.append(("relay_quote", payload.get("destinationCurrency")))
        return {
            "details": {
                "currencyIn": {"amountUsd": "3.0"},
                "currencyOut": {"amountUsd": "2.8", "amount": str(EXPECTED_WEI)},
            },
            "steps": [
                {
                    "items": [
                        {
                            "data": {"instructions": []},
                            "check": {"endpoint": "/intents/status/fake-gas"},
                        }
                    ]
                }
            ],
        }

    def default_poll(check_endpoint):
        call_log.append(("poll_relay_status", check_endpoint))
        return {"status": "success", "txHashes": [FILL_TX_HASH]}

    def default_build_sign_submit(secret, quote):
        call_log.append(("build_sign_submit", None))
        return "fakegassig456"

    def default_read_base_tx_receipt(tx_hash):
        call_log.append(("read_base_tx_receipt", tx_hash))
        return {"status": "0x1", "logs": []}  # native transfers emit no Transfer log

    native_balance_calls = {"n": 0}
    native_balances = {"before": 0, "after": EXPECTED_WEI}

    def default_read_base_native_balance_wei(address):
        native_balance_calls["n"] += 1
        call_log.append(("read_base_native_balance_wei", native_balance_calls["n"]))
        return native_balances["before"] if native_balance_calls["n"] == 1 else native_balances["after"]

    deps = {
        "is_killed": lambda: False,
        "resolve_secret": lambda: "FakeSecretBase58",
        "derive_pubkey": lambda secret: SENDER_PUBKEY,
        "read_ledger": read_ledger_rows,
        "append_ledger": append_ledger_row,
        "read_solana_balance_usd": lambda pubkey: 6.44,
        "read_base_native_balance_wei": default_read_base_native_balance_wei,
        "relay_quote": default_quote,
        "poll_relay_status": default_poll,
        "read_base_tx_receipt": default_read_base_tx_receipt,
        "build_sign_submit": default_build_sign_submit,
    }
    deps.update(overrides)
    return deps, call_log, ledger_path


def call_names(call_log):
    return [c[0] for c in call_log]


# --- dry-run-by-default (mirrors REQ-007) ---


def test_gas_dry_run_never_calls_build_sign_submit(tmp_path):
    deps, call_log, _ = make_gas_deps(tmp_path)
    result = run_gas_refill(deps=deps, live=False, recipient=RECIPIENT)
    assert result["ok"] is True
    assert result["dry"] is True
    assert "build_sign_submit" not in call_names(call_log)


def test_gas_dry_run_appends_exactly_one_dry_ledger_row_with_gas_step(tmp_path):
    deps, _, ledger_path = make_gas_deps(tmp_path)
    run_gas_refill(deps=deps, live=False, recipient=RECIPIENT)
    rows = read_ledger(ledger_path)
    assert len(rows) == 1
    assert rows[0]["status"] == "dry"
    assert rows[0]["step"] == GAS_STEP
    assert rows[0]["step"] != STEP


# --- REQ-GAS-002: recipient is required, no default ---


def test_gas_missing_recipient_refuses_before_any_network_call(tmp_path):
    deps, call_log, ledger_path = make_gas_deps(tmp_path)
    result = run_gas_refill(deps=deps, live=True, recipient=None)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)
    assert "build_sign_submit" not in call_names(call_log)
    rows = read_ledger(ledger_path)
    assert rows[0]["status"] == "failed"
    assert "recipient" in result["error"].lower()


def test_gas_malformed_recipient_refuses(tmp_path):
    deps, call_log, _ = make_gas_deps(tmp_path)
    result = run_gas_refill(deps=deps, live=True, recipient="not-an-address")
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)


def test_gas_dry_run_also_requires_recipient(tmp_path):
    """Dry-run must not silently proceed with no recipient either -- REQ-GAS-002 applies
    regardless of --live."""
    deps, call_log, _ = make_gas_deps(tmp_path)
    result = run_gas_refill(deps=deps, live=False, recipient=None)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)


# --- REQ-GAS-001: identity resolution ---


def test_gas_no_identity_resolved_refuses(tmp_path):
    deps, call_log, _ = make_gas_deps(tmp_path, resolve_secret=lambda: None)
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)


FAKE_SECRET = "TOTALLY_SECRET_GAS_MODE_VALUE_THAT_MUST_NEVER_APPEAR_IN_ANY_LOG"


def test_gas_derive_pubkey_decode_failure_ledger_row_never_contains_secret(tmp_path):
    def raising_derive(secret):
        raise ValueError(f"invalid base58 string: {secret}")

    deps, _, ledger_path = make_gas_deps(
        tmp_path, resolve_secret=lambda: FAKE_SECRET, derive_pubkey=raising_derive
    )
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    assert FAKE_SECRET not in json.dumps(result)
    rows = read_ledger(ledger_path)
    assert FAKE_SECRET not in json.dumps(rows[0])


def test_gas_build_sign_submit_decode_failure_never_leaks_secret(tmp_path):
    def raising_build_sign_submit(secret, quote):
        raise ValueError(f"solders decode error, input was: {secret}")

    deps, _, ledger_path = make_gas_deps(
        tmp_path, resolve_secret=lambda: FAKE_SECRET, build_sign_submit=raising_build_sign_submit
    )
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    assert FAKE_SECRET not in json.dumps(result)
    rows = read_ledger(ledger_path)
    assert all(FAKE_SECRET not in json.dumps(r) for r in rows)


# --- caps: $3.00/invocation, $3.00 reserve, 12% max fee (deliberately separate from USDC mode) ---


def test_gas_low_balance_refuses_before_relay_quote(tmp_path):
    deps, call_log, _ = make_gas_deps(tmp_path, read_solana_balance_usd=lambda pubkey: 2.99)
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)


def test_gas_high_fee_over_12pct_refuses_before_signing(tmp_path):
    def bad_quote(payload):
        return {
            "details": {
                "currencyIn": {"amountUsd": "3.0"},
                "currencyOut": {"amountUsd": "2.5", "amount": str(EXPECTED_WEI)},  # ~16.7% fee
            },
            "steps": [{"items": [{"data": {"instructions": []}, "check": {"endpoint": "/x"}}]}],
        }

    deps, call_log, _ = make_gas_deps(tmp_path, relay_quote=bad_quote)
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    assert "build_sign_submit" not in call_names(call_log)


def test_gas_fee_within_12pct_but_over_8pct_still_allowed_confirms_independent_cap(tmp_path):
    """A 10% fee is refused under the USDC mode's default 8% cap but must be ALLOWED here --
    confirms the two modes' fee caps never accidentally share state."""

    def ten_pct_fee_quote(payload):
        return {
            "details": {
                "currencyIn": {"amountUsd": "3.0"},
                "currencyOut": {"amountUsd": "2.7", "amount": str(EXPECTED_WEI)},  # 10% fee
            },
            "steps": [
                {
                    "items": [
                        {"data": {"instructions": []}, "check": {"endpoint": "/intents/status/fake-gas"}}
                    ]
                }
            ],
        }

    deps, _, ledger_path = make_gas_deps(tmp_path, relay_quote=ten_pct_fee_quote)
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is True
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "sent"


def test_gas_quote_missing_currency_out_amount_wei_refuses_before_signing(tmp_path):
    """REQ-GAS-004: if the quote's raw wei output can't be extracted, the run must refuse
    BEFORE broadcasting -- there would be no expected value to verify delivery against."""

    def quote_missing_wei_amount(payload):
        return {
            "details": {
                "currencyIn": {"amountUsd": "3.0"},
                "currencyOut": {"amountUsd": "2.8"},  # no "amount" (raw wei) field at all
            },
            "steps": [
                {
                    "items": [
                        {"data": {"instructions": []}, "check": {"endpoint": "/intents/status/fake-gas"}}
                    ]
                }
            ],
        }

    deps, call_log, ledger_path = make_gas_deps(tmp_path, relay_quote=quote_missing_wei_amount)
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    assert "build_sign_submit" not in call_names(call_log)
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "skipped"


# --- single in-flight guard (REQ-GAS-005 / mirrors REQ-005), independent of USDC-mode step ---


def test_gas_unresolved_pending_blocks_new_live_run(tmp_path):
    deps, call_log, ledger_path = make_gas_deps(tmp_path)
    append_ledger(ledger_path, build_row(step=GAS_STEP, amount_usd=1.0, status="pending", tx_hash="oldgassig"))
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    assert "pending" in result["error"].lower()
    assert "relay_quote" not in call_names(call_log)


def test_gas_unresolved_usdc_mode_pending_does_not_block_gas_run(tmp_path):
    """A pending USDC-mode (`franklin_sol_base_refill`) row must never block a gas-mode run --
    the two steps' single-in-flight guards are independent."""
    deps, _, ledger_path = make_gas_deps(tmp_path)
    append_ledger(ledger_path, build_row(step=STEP, amount_usd=1.0, status="pending", tx_hash="oldusdcsig"))
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is True


# --- REQ-GAS-004: independent native-ETH balance-delta verification before "sent" ---


def test_gas_correct_fill_writes_pending_then_sent(tmp_path):
    deps, _, ledger_path = make_gas_deps(tmp_path)
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is True
    rows = read_ledger(ledger_path)
    assert [r["status"] for r in rows] == ["pending", "sent"]
    assert rows[-1]["delivered_wei"] == EXPECTED_WEI


def test_gas_pending_row_written_before_poll_relay_status_call_order(tmp_path):
    deps, call_log, _ = make_gas_deps(tmp_path)
    run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    names = call_names(call_log)
    assert names.index("append_ledger") < names.index("poll_relay_status")


def test_gas_short_fill_under_85_pct_refused(tmp_path):
    # first call = before (0), second call = after -- only 70% of expected delivered
    calls = {"n": 0}

    def flaky(address):
        calls["n"] += 1
        return 0 if calls["n"] == 1 else int(round(EXPECTED_WEI * 0.70))

    deps, _, ledger_path = make_gas_deps(tmp_path, read_base_native_balance_wei=flaky)
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "failed"


def test_gas_flat_balance_delta_refused(tmp_path):
    """No ERC-20 Transfer log exists for a native transfer, so an unrelated/absent delta must
    itself refuse -- there is no secondary tx-specific signal to fall back on for native ETH."""
    deps, _, ledger_path = make_gas_deps(tmp_path, read_base_native_balance_wei=lambda addr: 1_000_000)
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "failed"


def test_gas_tx_receipt_not_success_status_refused(tmp_path):
    deps, _, ledger_path = make_gas_deps(
        tmp_path, read_base_tx_receipt=lambda tx_hash: {"status": "0x0", "logs": []}
    )
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "failed"


def test_gas_relay_reports_success_but_no_tx_hash_refused(tmp_path):
    deps, _, ledger_path = make_gas_deps(
        tmp_path, poll_relay_status=lambda ep: {"status": "success", "txHashes": []}
    )
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "failed"


def test_gas_relay_refund_writes_failed(tmp_path):
    deps, _, ledger_path = make_gas_deps(tmp_path, poll_relay_status=lambda ep: {"status": "refund"})
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "failed"


def test_gas_confirmation_raising_after_broadcast_leaves_pending_as_only_evidence(tmp_path):
    def raising_poll(ep):
        raise RuntimeError("transient RPC failure")

    deps, _, ledger_path = make_gas_deps(tmp_path, poll_relay_status=raising_poll)
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert len(rows) == 1
    assert rows[0]["status"] == "pending"
    assert "manual reconciliation" in result["error"]


# --- kill switch ---


def test_gas_kill_switch_blocks_live_run_before_any_quote(tmp_path):
    deps, call_log, _ = make_gas_deps(tmp_path, is_killed=lambda: True)
    result = run_gas_refill(deps=deps, live=True, recipient=RECIPIENT)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)


# --- resolve_live_flag reuse sanity (already covered exhaustively for USDC mode; gas mode uses
# the identical CLI dispatch, no separate pure function needed) ---


def test_gas_mode_dry_run_wins_over_live_flag_reused_from_usdc_mode():
    assert resolve_live_flag(live=True, dry_run=True) is False
