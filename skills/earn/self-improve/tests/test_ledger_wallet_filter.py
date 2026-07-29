"""RED phase — ledger-uniqueness (REQ-003/004): wallet-based row filtering for
lib.ledger_reader, and a non-breaking `own_wallets=None` opt-in on `realized_summary`/
`confirmed_net_series`.

Traces to behavioral-spec.md REQ-003/REQ-004; verification-architecture.md
PROP-LU-007/008/009/010.

`ledger_reader.filter_own_wallet_rows` and the `own_wallets` keyword parameter on
`realized_summary`/`confirmed_net_series` do NOT exist yet at RED-phase time — every test below
that references them is EXPECTED TO FAIL (AttributeError, or a TypeError for an unexpected
keyword argument) until Phase 2b implements REQ-003. Imports of the not-yet-existing symbol are
deferred into each test function (mirrors test_ledger_resolution.py's own convention) so a
single missing attribute fails only that test, not the whole file's collection.

Money-safety: every fixture in this file is a synthetic, hand-built ledger written under
pytest's own `tmp_path`. No test reads or writes any path under
`/home/life-manager/.anicca-founder/`, `/home/life-manager/.blockrun/`, or any other live instance home.
"""
import json
import os

from hypothesis import given, strategies as st

from lib import ledger_reader

# Mirrors skills/self/founder-loop/record-earn.mjs:39's SHARED blacklist — the exact
# contamination class found live in .anicca-founder/skills/earn/state/earn-ledger.jsonl.
AUTOMATON_PRE_ROTATION = "0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21"
AUTOMATON_POST_ROTATION = "0xb9dd3b67921b354c656523d6851537988f31dd56"
FOUNDER_WALLET = "0x810f6d61f7606deee2657d3083e150a222bc29c5"

OWN_WIN = {
    "ts": 1720001000, "source": "x402", "task": "own", "earn_usdc": 6.0, "cost_usdc": 1.0,
    "net_usdc": 5.0, "wallet": FOUNDER_WALLET, "tx": "0xown", "status": "0x1", "external": True,
}
FOREIGN_WIN = {
    "ts": 1720001100, "source": "hl-trade", "task": "foreign", "earn_usdc": 101.0, "cost_usdc": 1.0,
    "net_usdc": 100.0, "wallet": AUTOMATON_PRE_ROTATION, "chain": "hyperliquid", "fill_tid": 7,
    "confirmed": True, "external": True,
}
WALLETLESS_NARRATE = {
    "ts": 1720001200, "source": "cook", "task": "explore", "earn_usdc": 0, "cost_usdc": 0, "net_usdc": 0,
}


def _write_jsonl(tmp_path, rows, filename="earn-ledger.jsonl"):
    p = tmp_path / filename
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return str(p)


# --- PROP-LU-007 (REQ-003): filter_own_wallet_rows mirrors REQ-002's JS semantics ---


def test_filter_own_wallet_rows_keeps_own_and_walletless_excludes_foreign():
    rows = [OWN_WIN, FOREIGN_WIN, WALLETLESS_NARRATE]
    kept = ledger_reader.filter_own_wallet_rows(rows, FOUNDER_WALLET)
    assert kept == [OWN_WIN, WALLETLESS_NARRATE]


def test_filter_own_wallet_rows_case_insensitive():
    rows = [{**OWN_WIN, "wallet": FOUNDER_WALLET.upper()}]
    kept = ledger_reader.filter_own_wallet_rows(rows, FOUNDER_WALLET.lower())
    assert kept == rows


def test_filter_own_wallet_rows_none_own_wallets_excludes_every_walleted_row():
    rows = [OWN_WIN, WALLETLESS_NARRATE]
    kept = ledger_reader.filter_own_wallet_rows(rows, None)
    assert kept == [WALLETLESS_NARRATE]


def test_filter_own_wallet_rows_empty_list_input_returns_empty_list():
    assert ledger_reader.filter_own_wallet_rows([], FOUNDER_WALLET) == []


def test_filter_own_wallet_rows_accepts_a_list_of_multiple_own_wallets():
    second_own = "0xSecondOwnWallet"
    rows = [OWN_WIN, {**FOREIGN_WIN, "wallet": second_own}, {**FOREIGN_WIN, "wallet": AUTOMATON_POST_ROTATION}]
    kept = ledger_reader.filter_own_wallet_rows(rows, [FOUNDER_WALLET, second_own])
    assert [r["wallet"] for r in kept] == [FOUNDER_WALLET, second_own]


@given(
    rows=st.lists(
        st.fixed_dictionaries({
            "ts": st.integers(),
            "wallet": st.one_of(st.none(), st.sampled_from([FOUNDER_WALLET, AUTOMATON_PRE_ROTATION, AUTOMATON_POST_ROTATION])),
        })
    )
)
def test_filter_own_wallet_rows_property_surviving_walleted_rows_match_own_wallet(rows):
    kept = ledger_reader.filter_own_wallet_rows(rows, FOUNDER_WALLET)
    for row in kept:
        if row.get("wallet") is not None:
            assert row["wallet"].lower() == FOUNDER_WALLET.lower()


@given(
    rows=st.lists(st.fixed_dictionaries({"ts": st.integers(), "tag": st.just("walletless")}))
)
def test_filter_own_wallet_rows_property_walletless_rows_always_preserved_order_stable(rows):
    kept = ledger_reader.filter_own_wallet_rows(rows, FOUNDER_WALLET)
    assert kept == rows


# --- PROP-LU-010 (REQ-004): no write/delete file API in the new function ---


def test_filter_own_wallet_rows_source_has_no_write_api():
    import inspect

    src = inspect.getsource(ledger_reader.filter_own_wallet_rows)
    for forbidden in ("open(", ".write(", "os.remove", "os.unlink", "shutil.move"):
        assert forbidden not in src, f"filter_own_wallet_rows must never call {forbidden!r}"


# --- PROP-LU-008 (REQ-003): own_wallets=None is byte-identical to pre-feature behavior ---


def test_realized_summary_own_wallets_none_is_identical_to_pre_feature_behavior(tmp_path):
    ledger_path = _write_jsonl(tmp_path, [OWN_WIN, FOREIGN_WIN, WALLETLESS_NARRATE])

    baseline = ledger_reader.realized_summary(ledger_path)
    with_none = ledger_reader.realized_summary(ledger_path, own_wallets=None)

    assert with_none == baseline
    assert baseline["realized_net_usd"] == 105.0
    assert baseline["profitable_row_count"] == 2


def test_confirmed_net_series_own_wallets_none_is_identical_to_pre_feature_behavior(tmp_path):
    ledger_path = _write_jsonl(tmp_path, [OWN_WIN, FOREIGN_WIN, WALLETLESS_NARRATE])

    baseline = ledger_reader.confirmed_net_series(ledger_path)
    with_none = ledger_reader.confirmed_net_series(ledger_path, own_wallets=None)

    assert with_none == baseline
    assert len(baseline) == 2  # OWN_WIN + FOREIGN_WIN are both is_confirmed; narrate is not


# --- PROP-LU-009 (REQ-003): own_wallets=[X] scopes the sum to own+walletless only ---


def test_realized_summary_own_wallets_scopes_to_own_and_walletless_only(tmp_path):
    ledger_path = _write_jsonl(tmp_path, [OWN_WIN, FOREIGN_WIN, WALLETLESS_NARRATE])

    scoped = ledger_reader.realized_summary(ledger_path, own_wallets=[FOUNDER_WALLET])

    assert scoped["realized_net_usd"] == 5.0
    assert scoped["profitable_row_count"] == 1
    unfiltered = ledger_reader.realized_summary(ledger_path)
    assert scoped["realized_net_usd"] <= unfiltered["realized_net_usd"]


def test_realized_summary_own_wallets_empty_list_excludes_every_walleted_row(tmp_path):
    ledger_path = _write_jsonl(tmp_path, [OWN_WIN, FOREIGN_WIN, WALLETLESS_NARRATE])

    scoped = ledger_reader.realized_summary(ledger_path, own_wallets=[])

    assert scoped["realized_net_usd"] == 0.0
    assert scoped["profitable_row_count"] == 0


def test_confirmed_net_series_own_wallets_scopes_to_own_and_walletless_only(tmp_path):
    ledger_path = _write_jsonl(tmp_path, [OWN_WIN, FOREIGN_WIN, WALLETLESS_NARRATE])

    scoped = ledger_reader.confirmed_net_series(ledger_path, own_wallets=[FOUNDER_WALLET])

    assert scoped == [(OWN_WIN["ts"], OWN_WIN["net_usdc"])]


# --- REQ-004: read-only, never mutates the on-disk fixture ---


def test_realized_summary_with_own_wallets_never_mutates_the_fixture_file(tmp_path):
    ledger_path = _write_jsonl(tmp_path, [OWN_WIN, FOREIGN_WIN, WALLETLESS_NARRATE])
    before_mtime = os.path.getmtime(ledger_path)
    before_size = os.path.getsize(ledger_path)

    ledger_reader.realized_summary(ledger_path, own_wallets=[FOUNDER_WALLET])

    assert os.path.getmtime(ledger_path) == before_mtime
    assert os.path.getsize(ledger_path) == before_size
