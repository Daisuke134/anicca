import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from franklin_sol_base_refill import STEP, resolve_live_flag, run_refill  # noqa: E402
from lib.ledger import append_ledger, build_row, read_ledger  # noqa: E402

FRANKLIN_ROW = {
    "id": "Franklin",
    "walletAddress": {
        "solana": "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9",
        "evm": "0x3EcCAD24794ca298D25378E9902A251322ea8749",
    },
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
        return {"status": "success"}

    def default_build_sign_submit(secret, quote):
        call_log.append(("build_sign_submit", None))
        return "fakesig123"

    base_balance_calls = {"n": 0}
    balances = {"before": 0, "after": int(round(2.9 * 1e6))}

    def default_read_base_balance_units(address):
        base_balance_calls["n"] += 1
        call_log.append(("read_base_balance_units", base_balance_calls["n"]))
        return balances["before"] if base_balance_calls["n"] == 1 else balances["after"]

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


# --- REQ-002: own-citizen destination binding ---


def test_citizen_mismatch_refuses_before_relay_quote(tmp_path):
    deps, call_log, _, _ = make_deps(
        tmp_path, derive_pubkey=lambda secret: "SomeUnrelatedPubkey1111111111111111111111"
    )
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)


# --- REQ-003: caps ---


def test_low_balance_refuses_before_relay_quote(tmp_path):
    deps, call_log, _, _ = make_deps(tmp_path, read_solana_balance_usd=lambda pubkey: 4.99)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    assert "relay_quote" not in call_names(call_log)


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


def test_relay_success_but_no_balance_delta_writes_failed_not_sent(tmp_path):
    def flat_balance(address):
        return 1_000_000  # identical before/after -> no verified delta

    deps, _, ledger_path, _ = make_deps(tmp_path, read_base_balance_units=flat_balance)
    result = run_refill(deps=deps, live=True)
    assert result["ok"] is False
    rows = read_ledger(ledger_path)
    assert rows[0]["status"] == "pending"
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
