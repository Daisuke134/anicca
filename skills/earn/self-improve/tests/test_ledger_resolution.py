"""RED phase — self-improve-real-ledger, Group RL-ID (per-instance ledger path resolution,
REQ-RL1-4) and Group RL-MIR (Hyperliquid mirror-sync + is_confirmed/is_profitable split,
REQ-RL5/RL6).

Traces to behavioral-spec.md Groups RL-ID/RL-MIR, INV-RL1, EDGE-RL1/RL2/RL5a; verification-
architecture.md PROP-RL-ID1/ID2/ID3/ID5/ID7, PROP-RL-MIR1/MIR2.

`resolve_ledger_path` and `is_confirmed` do not exist yet on `lib.ledger_reader` at RED-phase
time — every test below that references them is EXPECTED TO FAIL (AttributeError, or a wrong-value
assertion against `is_profitable`'s pre-feature Hyperliquid-blind behavior) until Phase 2b
implements REQ-RL1-6. Imports of the not-yet-existing symbols are deferred INTO each test function
(rather than at module level) so a single missing attribute fails only that test, not the whole
file's collection — `lib.ledger_reader` itself already exists and already exports `is_profitable`/
`read_ledger`/`realized_summary`/`DEFAULT_LEDGER_PATH`, so module-level import of THOSE is safe.
"""
import os

from lib import ledger_reader

# --- fixture rows (mirrors test_ledger_reader.py's own fixture conventions) ---

HL_WIN = {
    "ts": 1720001000,
    "source": "hl-trade",
    "task": "hl-close BTC tid=42",
    "earn_usdc": 6.0,
    "cost_usdc": 1.0,
    "net_usdc": 5.0,
    "chain": "hyperliquid",
    "fill_tid": 42,
    "confirmed": True,
    "external": True,
}

HL_MISSING_FILL_TID = {**HL_WIN, "fill_tid": None}
HL_MISSING_CONFIRMED = {k: v for k, v in HL_WIN.items() if k != "confirmed"}
HL_WRONG_CHAIN = {**HL_WIN, "chain": "polygon"}

HL_CONFIRMED_LOSS = {
    "ts": 1720001100,
    "source": "hl-trade",
    "task": "hl-close BTC tid=43",
    "earn_usdc": 1.0,
    "cost_usdc": 6.0,
    "net_usdc": -5.0,
    "chain": "hyperliquid",
    "fill_tid": 43,
    "confirmed": True,
    "external": True,
}

EVM_CONFIRMED_LOSS = {
    "ts": 1720001200,
    "source": "x402-endpoint",
    "task": "refunded",
    "earn_usdc": 1.0,
    "cost_usdc": 6.0,
    "net_usdc": -5.0,
    "tx": "0xrefundloss",
    "status": "0x1",
    "external": True,
}

SOL_CONFIRMED_LOSS = {
    "ts": 1720001300,
    "source": "promote-fun-payout",
    "task": "clip-reward-refund",
    "earn_usdc": 1.0,
    "cost_usdc": 6.0,
    "net_usdc": -5.0,
    "sig": "5abc...lossSig",
    "confirmed": True,
    "external": True,
}


def _write_instance_ledger(tmp_path, instance_name, rows):
    """Build a `<tmp_path>/<instance_name>/skills/earn/state/earn-ledger.jsonl` — the exact
    rsync-tree-relative shape the Grounded Interface table describes for a real instance body."""
    import json

    state_dir = tmp_path / instance_name / "skills" / "earn" / "state"
    state_dir.mkdir(parents=True)
    ledger_path = state_dir / "earn-ledger.jsonl"
    with open(ledger_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return str(tmp_path / instance_name)


# --- PROP-RL-ID1 (REQ-RL1.1) ---


def test_resolve_ledger_path_honors_explicit_anicca_home_env():
    path, resolved, source = ledger_reader.resolve_ledger_path(env={"ANICCA_HOME": "/tmp/x"})

    assert path == "/tmp/x/skills/earn/state/earn-ledger.jsonl"
    assert resolved is True
    assert source == "anicca_home_env"


# --- PROP-RL-ID2 (REQ-RL1.2) ---


def test_resolve_ledger_path_file_relative_default_when_no_anicca_home():
    path, resolved, source = ledger_reader.resolve_ledger_path(env={})

    assert path.endswith(os.path.join("earn", "state", "earn-ledger.jsonl"))
    assert resolved is True
    assert source == "file_relative_default"
    # Computed relative to ledger_reader.py's OWN __file__ (self-improve/lib/ -> earn/state/),
    # never a hardcoded absolute string.
    expected_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(ledger_reader.__file__)))
    )
    assert path == os.path.join(expected_dir, "state", "earn-ledger.jsonl")


# --- PROP-RL-ID3 / INV-RL1 (the money-safety capstone: cross-instance leak is impossible) ---


def test_two_distinct_anicca_home_values_never_cross_read_each_others_ledger(tmp_path):
    inst_a_home = _write_instance_ledger(tmp_path, "instA", [{"ts": 1, "net_usdc": 111.0, "marker": "A"}])
    inst_b_home = _write_instance_ledger(tmp_path, "instB", [{"ts": 2, "net_usdc": 222.0, "marker": "B"}])

    path_a, resolved_a, _ = ledger_reader.resolve_ledger_path(env={"ANICCA_HOME": inst_a_home})
    path_b, resolved_b, _ = ledger_reader.resolve_ledger_path(env={"ANICCA_HOME": inst_b_home})

    assert resolved_a is True and resolved_b is True
    assert path_a != path_b

    rows_a = ledger_reader.read_ledger(path_a)
    rows_b = ledger_reader.read_ledger(path_b)

    assert len(rows_a) == 1 and rows_a[0]["marker"] == "A"
    assert len(rows_b) == 1 and rows_b[0]["marker"] == "B"
    # The literal leak this feature closes: instance A's resolved path must never contain
    # instance B's content, and vice versa.
    assert rows_a[0]["marker"] != "B"
    assert rows_b[0]["marker"] != "A"


# --- PROP-RL-ID5 (REQ-RL3: fresh resolution every call, never a frozen constant) ---


def test_realized_summary_resolves_fresh_per_call_no_import_time_caching(tmp_path, monkeypatch):
    inst_a_home = _write_instance_ledger(tmp_path, "instA5", [{"ts": 1, "net_usdc": 9.0, "marker": "A5"}])
    inst_b_home = _write_instance_ledger(tmp_path, "instB5", [{"ts": 2, "net_usdc": 9.0, "marker": "B5"}])

    monkeypatch.setenv("ANICCA_HOME", inst_a_home)
    summary_a = ledger_reader.realized_summary()

    monkeypatch.setenv("ANICCA_HOME", inst_b_home)
    summary_b = ledger_reader.realized_summary()

    assert summary_a["ledger_path"] != summary_b["ledger_path"]
    assert summary_a["ledger_path"].startswith(inst_a_home)
    assert summary_b["ledger_path"].startswith(inst_b_home)


# --- PROP-RL-ID7 (REQ-RL4: resolved/resolution_source keys in both branches) ---


def test_realized_summary_carries_resolved_and_resolution_source_keys(tmp_path, monkeypatch):
    inst_home = _write_instance_ledger(tmp_path, "instC7", [{"ts": 1, "net_usdc": 1.0}])

    monkeypatch.setenv("ANICCA_HOME", inst_home)
    summary_set = ledger_reader.realized_summary()
    assert summary_set["resolved"] is True
    assert summary_set["resolution_source"] == "anicca_home_env"

    monkeypatch.delenv("ANICCA_HOME", raising=False)
    summary_unset = ledger_reader.realized_summary()
    # EDGE-RL5a: this test runs from the feature's own dev worktree, which has no
    # skills/earn/state/ directory at all (gitignored) — the file-relative default STILL
    # resolves (resolved=True), it just degrades to a zero-row summary (EDGE-RL2's shape), never
    # a resolution failure.
    assert summary_unset["resolved"] is True
    assert summary_unset["resolution_source"] == "file_relative_default"


# --- PROP-RL-MIR1 (REQ-RL5: Hyperliquid disjunct mirrored from ledger.mjs::isProfitable) ---


def test_is_profitable_true_for_well_formed_hyperliquid_win():
    assert ledger_reader.is_profitable(HL_WIN) is True


def test_is_profitable_false_when_hyperliquid_fill_tid_missing():
    assert ledger_reader.is_profitable(HL_MISSING_FILL_TID) is False


def test_is_profitable_false_when_hyperliquid_confirmed_missing():
    assert ledger_reader.is_profitable(HL_MISSING_CONFIRMED) is False


def test_is_profitable_false_when_chain_is_not_hyperliquid():
    assert ledger_reader.is_profitable(HL_WRONG_CHAIN) is False


# --- PROP-RL-MIR2 (REQ-RL6: is_confirmed sees confirmed LOSSES is_profitable structurally cannot) ---


def test_is_confirmed_true_for_hyperliquid_confirmed_loss_but_is_profitable_false():
    assert ledger_reader.is_confirmed(HL_CONFIRMED_LOSS) is True
    assert ledger_reader.is_profitable(HL_CONFIRMED_LOSS) is False


def test_is_confirmed_true_for_evm_confirmed_loss_but_is_profitable_false():
    assert ledger_reader.is_confirmed(EVM_CONFIRMED_LOSS) is True
    assert ledger_reader.is_profitable(EVM_CONFIRMED_LOSS) is False


def test_is_confirmed_true_for_solana_confirmed_loss_but_is_profitable_false():
    assert ledger_reader.is_confirmed(SOL_CONFIRMED_LOSS) is True
    assert ledger_reader.is_profitable(SOL_CONFIRMED_LOSS) is False
