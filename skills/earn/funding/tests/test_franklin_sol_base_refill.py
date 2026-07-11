import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from franklin_sol_base_refill import (  # noqa: E402
    STEP,
    USDC_BASE,
    resolve_live_flag,
    run_refill,
)
from lib.erc20 import ERC20_TRANSFER_TOPIC0  # noqa: E402
from lib.ledger import append_ledger, build_row, read_ledger  # noqa: E402

FRANKLIN_ROW = {
    "id": "Franklin",
    "walletAddress": {
        "solana": "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9",
        "evm": "0x3EcCAD24794ca298D25378E9902A251322ea8749",
    },
}

FILL_TX_HASH = "0xfeedfeedfeedfeedfeedfeedfeedfeedfeedfeedfeedfeedfeedfeedfeedfeed"


def _pad_topic(addr: str) -> str:
    return "0x" + addr.lower().replace("0x", "").rjust(64, "0")


def _transfer_log(*, token_address: str, to_address: str, amount_units: int) -> dict:
    """A single ERC-20 Transfer(address,address,uint256) log matching
    `lib.erc20.parse_erc20_transfer_amount`'s expected shape."""
    return {
        "address": token_address,
        "topics": [
            ERC20_TRANSFER_TOPIC0,
            _pad_topic("0x1111111111111111111111111111111111111111"),  # from (arbitrary)
            _pad_topic(to_address),
        ],
        "data": hex(amount_units),
    }


def _fill_receipt(*, to_address: str, amount_units: int, status: str = "0x1") -> dict:
    return {
        "status": status,
        "logs": [_transfer_log(token_address=USDC_BASE, to_address=to_address, amount_units=amount_units)],
    }


def make_deps(tmp_path, **overrides):
    """Builds a fully-fake, injectable deps dict for run_refill() -- no real network, no real
    keys, no real ledger file outside tmp_path. `call_log` records (name, detail) tuples in
    call order so orchestration tests can assert on ordering (PROP-009) and on which effectful
    calls were reached (PROP-008/PROP-011)."""
    ledger_path = str(tmp_path / "funding-ledger.jsonl")
    call_log = []

    def append_ledger_row(row):
        call_log.append(("append_ledger", row.get("status")))
        append_ledger(ledger_path, row)

    def read_ledger_rows():
        return read_ledger(ledger_path)

    def default_quote(payload):
        call_log.append(("relay_quote", None))
        return {
            "details": {
                "currencyIn": {"amountUsd": "3.0"},
                "currencyOut": {"amountUsd": "2.9"},
            },
            "steps": [
                {
                    "items": [
                        {
                            "data": {"instructions": []},
                            "check": {"endpoint": "/intents/status/fake"},
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
        return "fakesig123"

    base_balance_calls = {"n": 0}
    balances = {"before": 0, "after": int(round(2.9 * 1e6))}

    def default_read_base_balance_units(address):
        base_balance_calls["n"] += 1
        call_log.append(("read_base_balance_units", base_balance_calls["n"]))
        return balances["before"] if base_balance_calls["n"] == 1 else balances["after"]

    def default_read_base_tx_receipt(tx_hash):
        call_log.append(("read_base_tx_receipt", tx_hash))
        return _fill_receipt(
            to_address=FRANKLIN_ROW["walletAddress"]["evm"], amount_units=int(round(2.9 * 1e6))
        )

    citizens_calls = []

    def default_read_citizens():
        citizens_calls.append(True)
        return [FRANKLIN_ROW]

    deps = {
        "is_killed": lambda: False,
        "resolve_secret": lambda: "FakeSecretBase58",
        "derive_pubkey": lambda secret: FRANKLIN_ROW["walletAddress"]["solana"],
        "read_citizens": default_read_citizens,
        "read_ledger": read_ledger_rows,
        "append_ledger": append_ledger_row,
        "read_solana_balance_usd": lambda pubkey: 13.02,
        "read_base_balance_units": default_read_base_balance_units,
        "relay_quote": default_quote,
        "poll_relay_status": default_poll,
        "read_base_tx_receipt": default_read_base_tx_receipt,
        "build_sign_submit": default_build_sign_submit,
    }
    deps.update(overrides)
    return deps, call_log, ledger_path, citizens_calls


def call_names(call_log):
    return [c[0] for c in call_log]


# --- REQ-007: dry-run-by-default ---


def test_dry_run_never_calls_build_sign_submit(tmp_path):
    deps, call_log, _, _ = make_deps(tmp_path)
    result = run_refill(deps=deps, live=False)
    assert result["ok"] is True
    assert result["dry"] is True
    assert "build_sign_submit" not in call_names(call_log)


def test_dry_run_appends_exactly_one_dry_ledger_row(tmp_path):
    deps, _, ledger_path, _ = make_deps(tmp_path)
    run_refill(deps=deps, live=False)
    rows = read_ledger(ledger_path)
    assert len(rows) == 1
    assert rows[0]["status"] == "dry"
    assert rows[0]["step"] == STEP


# --- REQ-001: fail-closed identity resolution ---


def test_no_identity_resolved_refuses_before_citizens_lookup(tmp_path):
    deps, call_log, _, citizens_calls = make_deps(tmp_path, resolve_secret=lambda: None)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert citizens_calls == []
    assert "build_sign_submit" not in call_names(call_log)


# --- FIND-006 edge case: derive_pubkey raising (undecodable secret) fails closed ---


def test_derive_pubkey_raising_refuses_with_ledger_row(tmp_path):
    def raising_derive(secret):
        raise ValueError("could not decode base58/base64")

    deps, _, ledger_path, _ = make_deps(tmp_path, derive_pubkey=raising_derive)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"


# --- FIND-003: secret-safety -- decode-failure ledger rows must never leak the raw secret ---


FAKE_SECRET = "TOTALLY_SECRET_VALUE_THAT_MUST_NEVER_APPEAR_IN_ANY_LOG_1234567890"


def test_derive_pubkey_decode_failure_ledger_row_never_contains_secret(tmp_path):
    def raising_derive(secret):
        # Simulate a decode library whose exception message embeds the raw input it failed to
        # parse -- exactly the risk FIND-003 flags.
        raise ValueError(f"invalid base58 string: {secret}")

    deps, _, ledger_path, _ = make_deps(
        tmp_path, resolve_secret=lambda: FAKE_SECRET, derive_pubkey=raising_derive
    )
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert FAKE_SECRET not in json.dumps(result)
    rows = read_ledger(ledger_path)
    assert len(rows) == 1
    assert FAKE_SECRET not in json.dumps(rows[0])


def test_build_sign_submit_decode_failure_ledger_row_never_contains_secret(tmp_path):
    def raising_build_sign_submit(secret, quote):
        raise ValueError(f"solders decode error, input was: {secret}")

    deps, _, ledger_path, _ = make_deps(
        tmp_path, resolve_secret=lambda: FAKE_SECRET, build_sign_submit=raising_build_sign_submit
    )
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert FAKE_SECRET not in json.dumps(result)
    rows = read_ledger(ledger_path)
    assert all(FAKE_SECRET not in json.dumps(r) for r in rows)


# --- REQ-002: own-citizen destination binding ---


def test_citizen_mismatch_refuses_before_relay_quote(tmp_path):
    deps, call_log, _, _ = make_deps(
        tmp_path, derive_pubkey=lambda secret: "SomeUnrelatedPubkey1111111111111111111111"
    )
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)


# --- FIND-002: citizens.json missing/unreadable/malformed must fail closed, never crash ---


def test_citizens_file_not_found_refuses_with_ledger_row(tmp_path):
    def raising_read_citizens():
        raise FileNotFoundError("~/.hermes/state/citizens.json")

    deps, call_log, ledger_path, _ = make_deps(tmp_path, read_citizens=raising_read_citizens)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)
    rows = read_ledger(ledger_path)
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"


def test_citizens_malformed_json_refuses_with_ledger_row(tmp_path):
    def raising_read_citizens():
        raise json.JSONDecodeError("Expecting value", "not json", 0)

    deps, call_log, ledger_path, _ = make_deps(tmp_path, read_citizens=raising_read_citizens)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)
    rows = read_ledger(ledger_path)
    assert rows[0]["status"] == "failed"


def test_citizens_no_matching_row_refuses(tmp_path):
    deps, call_log, _, _ = make_deps(tmp_path, read_citizens=lambda: [])
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)


# --- REQ-003: caps ---


def test_low_balance_refuses_before_relay_quote(tmp_path):
    deps, call_log, _, _ = make_deps(tmp_path, read_solana_balance_usd=lambda pubkey: 4.99)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)


# --- FIND-006: transient network error reading the live Solana balance fails closed ---


def test_read_solana_balance_raising_refuses_with_ledger_row(tmp_path):
    def raising_balance(pubkey):
        raise ConnectionError("solana rpc timeout")

    deps, call_log, ledger_path, _ = make_deps(tmp_path, read_solana_balance_usd=raising_balance)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)
    rows = read_ledger(ledger_path)
    assert rows[0]["status"] == "skipped"


# --- REQ-004: relay fee cap ---


def test_high_fee_refuses_before_signing(tmp_path):
    def bad_quote(payload):
        return {
            "details": {"currencyIn": {"amountUsd": "6.5"}, "currencyOut": {"amountUsd": "5.0"}},  # ~23% fee
            "steps": [{"items": [{"data": {"instructions": []}, "check": {"endpoint": "/x"}}]}],
        }

    deps, call_log, _, _ = make_deps(tmp_path, relay_quote=bad_quote)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "build_sign_submit" not in call_names(call_log)


# --- FIND-001: relay quote missing/malformed currencyIn/currencyOut must REFUSE, never
# fabricate a substitute value from the locally-computed requested amount ---


def test_quote_missing_currency_in_entirely_refuses(tmp_path):
    def quote_missing_currency_in(payload):
        return {
            "details": {"currencyOut": {"amountUsd": "6.45"}},  # no currencyIn key at all
            "steps": [{"items": [{"data": {"instructions": []}, "check": {"endpoint": "/x"}}]}],
        }

    deps, call_log, _, _ = make_deps(tmp_path, relay_quote=quote_missing_currency_in)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "build_sign_submit" not in call_names(call_log)


def test_quote_currency_in_null_amount_usd_refuses(tmp_path):
    def quote_null_amount(payload):
        return {
            "details": {"currencyIn": {"amountUsd": None}, "currencyOut": {"amountUsd": "6.45"}},
            "steps": [{"items": [{"data": {"instructions": []}, "check": {"endpoint": "/x"}}]}],
        }

    deps, call_log, _, _ = make_deps(tmp_path, relay_quote=quote_null_amount)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "build_sign_submit" not in call_names(call_log)


def test_quote_currency_in_wrong_type_refuses(tmp_path):
    def quote_wrong_type(payload):
        return {
            "details": {"currencyIn": "not-an-object", "currencyOut": {"amountUsd": "6.45"}},
            "steps": [{"items": [{"data": {"instructions": []}, "check": {"endpoint": "/x"}}]}],
        }

    deps, call_log, _, _ = make_deps(tmp_path, relay_quote=quote_wrong_type)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "build_sign_submit" not in call_names(call_log)


def test_quote_currency_out_missing_does_not_substitute_requested_amount(tmp_path):
    """The exact FIND-001 regression: a quote reporting currencyOut but no currencyIn at all
    must NEVER have in_usd silently backfilled with the locally-requested swap amount (which
    would fabricate a passing fee_pct even though relay never reported the input economics)."""

    def quote_missing_currency_in(payload):
        return {
            "details": {"currencyOut": {"amountUsd": "6.45"}},
            "steps": [{"items": [{"data": {"instructions": []}, "check": {"endpoint": "/x"}}]}],
        }

    deps, _, ledger_path, _ = make_deps(tmp_path, relay_quote=quote_missing_currency_in)
    result = run_refill(deps=deps, live=True, amount_usd=6.50)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    plan = rows[-1].get("plan", {})
    assert plan.get("in_usd") is None
    assert plan.get("fee_allowed") is False


# --- FIND-006: transient relay.link network error fails closed ---


def test_relay_quote_raising_refuses_with_ledger_row(tmp_path):
    def raising_quote(payload):
        raise TimeoutError("relay.link /quote timeout")

    deps, call_log, ledger_path, _ = make_deps(tmp_path, relay_quote=raising_quote)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "build_sign_submit" not in call_names(call_log)
    rows = read_ledger(ledger_path)
    assert rows[0]["status"] == "skipped"


# --- REQ-005: single in-flight guard ---


def test_unresolved_pending_blocks_new_live_run(tmp_path):
    deps, call_log, ledger_path, _ = make_deps(tmp_path)
    append_ledger(ledger_path, build_row(step=STEP, amount_usd=1.0, status="pending", tx_hash="oldsig"))
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "pending" in result["error"].lower()
    assert "relay_quote" not in call_names(call_log)


def test_unresolved_pending_does_not_block_dry_run(tmp_path):
    deps, _, ledger_path, _ = make_deps(tmp_path)
    append_ledger(ledger_path, build_row(step=STEP, amount_usd=1.0, status="pending", tx_hash="oldsig"))
    result = run_refill(deps=deps, live=False)
    assert result["ok"] is True
    assert result["dry"] is True


def test_resolved_pending_does_not_block_new_live_run(tmp_path):
    deps, _, ledger_path, _ = make_deps(tmp_path)
    append_ledger(ledger_path, build_row(step=STEP, amount_usd=1.0, status="pending", tx_hash="oldsig"))
    append_ledger(ledger_path, build_row(step=STEP, amount_usd=1.0, status="sent", tx_hash="oldsig"))
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is True


# --- REQ-006: ledger + independent on-chain verification ---


def test_live_run_verified_fill_writes_pending_then_sent(tmp_path):
    deps, _, ledger_path, _ = make_deps(tmp_path)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is True
    rows = read_ledger(ledger_path)
    assert [r["status"] for r in rows] == ["pending", "sent"]


def test_pending_row_written_before_poll_relay_status_call_order(tmp_path):
    deps, call_log, _, _ = make_deps(tmp_path)
    run_refill(deps=deps, live=True)
    names = call_names(call_log)
    assert names.index("append_ledger") < names.index("poll_relay_status")


def test_flat_balance_delta_is_recorded_as_sanity_flag_but_does_not_override_tx_verification(tmp_path):
    """FIND-004: the coarse wallet-wide balance delta is now a SECONDARY sanity check only --
    it is recorded on the ledger row for audit, but a flat/zero delta does NOT by itself flip a
    tx-receipt-verified fill to 'failed' (the tx-specific check is authoritative)."""

    def flat_balance(address):
        return 1_000_000  # identical before/after -> the coarse delta check alone would fail

    deps, _, ledger_path, _ = make_deps(tmp_path, read_base_balance_units=flat_balance)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is True
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "sent"
    assert rows[-1]["base_balance_delta_sanity_ok"] is False


# --- FIND-004: tx-specific fill verification (not just a coarse balance delta) ---


def test_correct_fill_tx_receipt_verifies_and_writes_sent(tmp_path):
    """The happy-path default fixtures already carry a matching tx receipt/Transfer log --
    this is the explicit 'correct fill verified' case FIND-004 requires."""
    deps, _, ledger_path, _ = make_deps(tmp_path)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is True
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "sent"
    assert rows[-1]["fill_tx_hash"] == FILL_TX_HASH


def test_unrelated_inflow_without_matching_tx_receipt_not_verified(tmp_path):
    """A wallet-wide balance delta CAN increase from something unrelated to this fill (a second
    concurrent invocation, another earn engine crediting the same wallet). If the relay fill
    tx's own receipt has no Transfer log naming OUR recipient, the run must NOT be marked
    verified even though the coarse balance delta alone would look fine."""

    def unrelated_receipt(tx_hash):
        return _fill_receipt(
            to_address="0x9999999999999999999999999999999999999999", amount_units=int(round(2.9 * 1e6))
        )

    deps, _, ledger_path, _ = make_deps(tmp_path, read_base_tx_receipt=unrelated_receipt)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert rows[0]["status"] == "pending"
    assert rows[-1]["status"] == "failed"


def test_short_fill_under_85_pct_refused(tmp_path):
    """A Transfer log that names our address but delivers materially less than the quote's
    expected output (< FILL_MIN_DELIVERED_PCT) must be refused/flagged, not silently accepted."""

    def short_fill_receipt(tx_hash):
        # 70% of the expected 2.9 USDC (2_900_000 units) -- below the 85% floor.
        return _fill_receipt(
            to_address=FRANKLIN_ROW["walletAddress"]["evm"],
            amount_units=int(round(2.9 * 1e6 * 0.70)),
        )

    deps, _, ledger_path, _ = make_deps(tmp_path, read_base_tx_receipt=short_fill_receipt)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "failed"


def test_tx_receipt_not_success_status_refused(tmp_path):
    def reverted_receipt(tx_hash):
        return _fill_receipt(
            to_address=FRANKLIN_ROW["walletAddress"]["evm"], amount_units=int(round(2.9 * 1e6)), status="0x0"
        )

    deps, _, ledger_path, _ = make_deps(tmp_path, read_base_tx_receipt=reverted_receipt)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "failed"


def test_relay_reports_success_but_no_tx_hash_refused(tmp_path):
    deps, _, ledger_path, _ = make_deps(
        tmp_path, poll_relay_status=lambda ep: {"status": "success", "txHashes": []}
    )
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "failed"


def test_relay_refund_writes_failed(tmp_path):
    deps, _, ledger_path, _ = make_deps(tmp_path, poll_relay_status=lambda ep: {"status": "refund"})
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert rows[-1]["status"] == "failed"


def test_confirmation_raising_after_broadcast_leaves_pending_as_only_evidence(tmp_path):
    def raising_poll(ep):
        raise RuntimeError("transient RPC failure")

    deps, _, ledger_path, _ = make_deps(tmp_path, poll_relay_status=raising_poll)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert len(rows) == 1
    assert rows[0]["status"] == "pending"
    assert "manual reconciliation" in result["error"]


# --- kill switch ---


def test_kill_switch_blocks_live_run_before_any_quote(tmp_path):
    deps, call_log, _, _ = make_deps(tmp_path, is_killed=lambda: True)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)


# --- resolve_live_flag (REQ-007 CLI edge case) ---


def test_resolve_live_flag_dry_run_wins_over_live():
    assert resolve_live_flag(live=True, dry_run=True) is False


def test_resolve_live_flag_live_only_true():
    assert resolve_live_flag(live=True, dry_run=False) is True


def test_resolve_live_flag_default_false():
    assert resolve_live_flag(live=False, dry_run=False) is False


# --- resolve_identity_secret (REQ-001 ANICCA_HOME gate, real effectful function) ---


def test_resolve_identity_secret_no_subprocess_when_anicca_home_unset(monkeypatch):
    import franklin_sol_base_refill as fsbr

    def fake_run(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called when ANICCA_HOME is unset")

    monkeypatch.setattr(fsbr.subprocess, "run", fake_run)
    env = {k: v for k, v in os.environ.items() if k != "ANICCA_HOME"}
    secret = fsbr.resolve_identity_secret(env=env)
    assert secret is None


def test_resolve_identity_secret_spawns_subprocess_when_anicca_home_set(monkeypatch):
    import franklin_sol_base_refill as fsbr

    captured = {}

    class FakeProc:
        returncode = 0
        stdout = "FakeSecretValue\n"

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env")
        return FakeProc()

    monkeypatch.setattr(fsbr.subprocess, "run", fake_run)
    env = dict(os.environ)
    env["ANICCA_HOME"] = "/tmp/fake-anicca-home-for-tests"
    secret = fsbr.resolve_identity_secret(env=env)
    assert secret == "FakeSecretValue"
    assert captured["cmd"][0] == "node"
    assert captured["cmd"][-1] == "solana"


def test_resolve_identity_secret_nonzero_exit_treated_as_unresolved(monkeypatch):
    import franklin_sol_base_refill as fsbr

    class FakeProc:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(fsbr.subprocess, "run", lambda *a, **k: FakeProc())
    env = dict(os.environ)
    env["ANICCA_HOME"] = "/tmp/fake-anicca-home-for-tests"
    assert fsbr.resolve_identity_secret(env=env) is None
