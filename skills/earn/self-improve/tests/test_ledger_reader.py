"""Close-loop Gap 1 tests: `lib/ledger_reader.py` reads the REAL realized-P&L ledger
(`earn-ledger.jsonl`) read-only, mirroring `skills/_shared/lib/ledger.mjs::isProfitable` exactly.

Fixture rows below mirror `ledger.mjs`'s own module-docstring examples: a real EVM-confirmed
profitable row, a real Solana-confirmed profitable row, a narrate/self-report row with no tx (must
be excluded), a swap row (asset rotation, must be excluded even though net_usdc > 0), and a
negative-net row (must be excluded). This is the SAME rule the real earn system's GATE-0 uses to
decide "1 profitable wake" — this module must never diverge from it.
"""
import json

from lib import ledger_reader

EVM_PROFITABLE = {
    "ts": 1720000000,
    "wallet": "0xabc",
    "source": "x402-endpoint",
    "task": "widget-sale",
    "earn_usdc": 5.0,
    "cost_usdc": 1.0,
    "net_usdc": 4.0,
    "tx": "0xdeadbeef",
    "status": "0x1",
    "external": True,
}

SOL_PROFITABLE = {
    "ts": 1720000100,
    "wallet": "SoLaNaWaLLeT",
    "source": "promote-fun-payout",
    "task": "clip-reward",
    "earn_usdc": 3.5,
    "cost_usdc": 0.5,
    "net_usdc": 3.0,
    "sig": "5abc...sig",
    "confirmed": True,
    "external": True,
}

NARRATE_ONLY = {
    "ts": 1720000200,
    "source": "discovery-narrate",
    "task": "scouted a bounty",
    "earn_usdc": 10.0,
    "cost_usdc": 0.0,
    "net_usdc": 10.0,
    # no tx/status, no sig/confirmed, no external — self-reported only
}

SWAP_ROW = {
    "ts": 1720000300,
    "source": "swap-eth-usdc",
    "task": "rotate gas to usdc",
    "earn_usdc": 20.0,
    "cost_usdc": 1.0,
    "net_usdc": 19.0,
    "tx": "0xswap",
    "status": "0x1",
    "external": True,  # even if somehow marked external, swap sources are excluded
}

NEGATIVE_NET_ROW = {
    "ts": 1720000400,
    "source": "x402-endpoint",
    "task": "refunded",
    "earn_usdc": 1.0,
    "cost_usdc": 5.0,
    "net_usdc": -4.0,
    "tx": "0xrefund",
    "status": "0x1",
    "external": True,
}

PENDING_TX_ROW = {
    "ts": 1720000500,
    "source": "x402-endpoint",
    "task": "pending",
    "earn_usdc": 5.0,
    "cost_usdc": 1.0,
    "net_usdc": 4.0,
    "tx": "0xpending",
    "status": "0x0",  # reverted/pending, not confirmed 0x1
    "external": True,
}

ALL_ROWS = [EVM_PROFITABLE, SOL_PROFITABLE, NARRATE_ONLY, SWAP_ROW, NEGATIVE_NET_ROW, PENDING_TX_ROW]


def _write_jsonl(tmp_path, rows, filename="earn-ledger.jsonl"):
    path = tmp_path / filename
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return str(path)


def test_is_profitable_true_for_real_evm_confirmed_row():
    assert ledger_reader.is_profitable(EVM_PROFITABLE) is True


def test_is_profitable_true_for_real_solana_confirmed_row():
    assert ledger_reader.is_profitable(SOL_PROFITABLE) is True


def test_is_profitable_false_for_narrate_only_row_no_tx():
    assert ledger_reader.is_profitable(NARRATE_ONLY) is False


def test_is_profitable_false_for_swap_row_even_if_net_positive_and_external():
    assert ledger_reader.is_profitable(SWAP_ROW) is False


def test_is_profitable_false_for_negative_net_row():
    assert ledger_reader.is_profitable(NEGATIVE_NET_ROW) is False


def test_is_profitable_false_for_unconfirmed_tx_status():
    assert ledger_reader.is_profitable(PENDING_TX_ROW) is False


def test_is_profitable_false_for_none_or_empty():
    assert ledger_reader.is_profitable(None) is False
    assert ledger_reader.is_profitable({}) is False


def test_read_ledger_missing_file_returns_empty_list(tmp_path):
    missing_path = str(tmp_path / "does-not-exist.jsonl")
    assert ledger_reader.read_ledger(missing_path) == []


def test_read_ledger_skips_blank_and_malformed_lines(tmp_path):
    path = tmp_path / "messy.jsonl"
    path.write_text(
        json.dumps(EVM_PROFITABLE) + "\n"
        "\n"  # blank line
        "not valid json at all\n"
        "[1, 2, 3]\n"  # valid JSON but not an object -> skipped
        + json.dumps(SOL_PROFITABLE) + "\n",
        encoding="utf-8",
    )

    rows = ledger_reader.read_ledger(str(path))

    assert len(rows) == 2
    assert rows[0]["net_usdc"] == 4.0
    assert rows[1]["net_usdc"] == 3.0


def test_realized_summary_on_sparse_real_shaped_ledger(tmp_path):
    path = _write_jsonl(tmp_path, ALL_ROWS)

    summary = ledger_reader.realized_summary(path)

    assert summary["total_rows"] == len(ALL_ROWS)
    # Only EVM_PROFITABLE (+4.0) and SOL_PROFITABLE (+3.0) count -> 2 rows, 7.0 net.
    assert summary["profitable_row_count"] == 2
    assert summary["realized_net_usd"] == 7.0


def test_realized_summary_missing_ledger_degrades_to_all_zero(tmp_path):
    missing_path = str(tmp_path / "no-such-ledger.jsonl")

    summary = ledger_reader.realized_summary(missing_path)

    assert summary["total_rows"] == 0
    assert summary["profitable_row_count"] == 0
    assert summary["realized_net_usd"] == 0.0


def test_realized_summary_empty_ledger_file_degrades_to_all_zero(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")

    summary = ledger_reader.realized_summary(str(path))

    assert summary["total_rows"] == 0
    assert summary["profitable_row_count"] == 0
    assert summary["realized_net_usd"] == 0.0


def test_realized_summary_window_excludes_rows_outside_ts_range(tmp_path):
    path = _write_jsonl(tmp_path, ALL_ROWS)

    # Window that only covers EVM_PROFITABLE's ts (1720000000..1720000050)
    summary = ledger_reader.realized_summary(path, window_start_ts=1720000000, window_end_ts=1720000050)

    assert summary["profitable_row_count"] == 1
    assert summary["realized_net_usd"] == 4.0


def test_realized_summary_default_path_points_at_the_real_earn_ledger_location():
    assert ledger_reader.DEFAULT_LEDGER_PATH.endswith("skills/earn/state/earn-ledger.jsonl")
