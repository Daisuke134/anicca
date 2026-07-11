"""ledger_reader.py — close-loop Gap 1 fix: the self-improve harness's OBSERVE step, reading the
REAL realized P&L ledger before every evolve run.

Read-only Python mirror of `skills/_shared/lib/ledger.mjs`'s `readLedger`/`isProfitable` semantics.
This module NEVER writes to `earn-ledger.jsonl` or any other ledger file — it only ever reads
(`open(path, "r")`), matching REQ-EV7/INV-6's "fitness computation and ledger mutation are
structurally different code paths" pattern already established for the backtest evaluator.

Why a PORT instead of calling the real `ledger.mjs` (INV-5 tension, disclosed): behavioral-spec.md's
INV-5 says "no second parallel ledger reader/writer is introduced" and names
`skills/_shared/lib/ledger.mjs` as the one shared interface. That invariant was written before this
close-loop revision needed a Python-side OBSERVE step inside a fully-Python evaluation harness
(`evaluator.py`/`run_evolve.sh` intentionally have NO subprocess/node dependency — `subprocess` is
even on `scope_guard.py`'s own DENYLIST_MODULES for the EVOLVE-BLOCK, and shelling out to `node`
from this harness's own tooling would be the first subprocess dependency it has ever had). Rather
than add a subprocess->node round trip for a single read+filter, this module re-implements
`isProfitable`'s exact boolean logic in pure Python, read-only, over the SAME ledger file path and
the SAME field semantics — this is the pragmatic, honest trade-off: a duplicated (not divergent)
read-only VIEW of one field, not a second ledger, and never a writer. If `ledger.mjs`'s
`isProfitable` semantics ever change, this file must be updated to match (checked by
`tests/test_ledger_reader.py`'s fixtures, which mirror `skills/_shared/lib/ledger.mjs`'s own
module-docstring examples: a real EVM row, a real Solana row, a narrate-only row, and a swap row).

`isProfitable` mirrored EXACTLY (skills/_shared/lib/ledger.mjs, read directly): a profitable wake
needs (1) `net_usdc > 0`, (2) NOT a swap source (`swap-eth-usdc`/`swap`/`swap-usdc-eth` — asset
rotation is never earning), (3) `external is True` (proven external inbound revenue), AND (4) a
chain-correct confirmation: EVM (`tx` present AND `status == "0x1"`) OR Solana (`sig` present AND
`confirmed is True`) OR Hyperliquid (`chain == "hyperliquid"` AND `fill_tid` present AND
`confirmed is True` — REQ-RL5, self-improve-real-ledger, mirrored from ledger.mjs's own
`hl-realized-pnl` feature, closing the drift this module's own docstring used to disclose).

Per-instance path resolution (REQ-RL1, self-improve-real-ledger, closes Gap 1's cross-instance
leak): `resolve_ledger_path()` prefers an explicit `ANICCA_HOME` (mirrors
`skills/earn/lib/resolve-identity.mjs`'s own test-injectable `{env}` convention), falling back to a
path computed relative to THIS running module's own `__file__` (the rsync-tree-relative model
`genome.mjs` already documents for `baseline-genome.json`, applied here to `earn-ledger.jsonl`) —
never a single hardcoded path. See behavioral-spec.md's "Grounded Interface" section.
"""
from __future__ import annotations

import json
import os
from typing import Optional, Tuple


def resolve_ledger_path(env: Optional[dict] = None) -> Tuple[str, bool, str]:
    """REQ-RL1: per-instance ledger path resolution, fail-closed. Priority:
    1. `env["ANICCA_HOME"]` (or `os.environ["ANICCA_HOME"]` when `env` is None), if set and
       non-empty -> `<ANICCA_HOME>/skills/earn/state/earn-ledger.jsonl`,
       resolution_source="anicca_home_env".
    2. Else -> THIS module's own `__file__`-relative path (climb from `self-improve/lib/` to
       `earn/state/` in the same tree), resolution_source="file_relative_default".
    3. `resolved=False` (path="", resolution_source="unresolved_no_file_context") ONLY when this
       process cannot determine its own module `__file__` at all (an exotic packaging context) —
       NEVER used as an excuse to fall back to another instance's hardcoded path (mirrors
       resolve-identity.mjs's R5: fail-closed, never guess another instance's identity)."""
    effective_env = env if env is not None else os.environ
    anicca_home = effective_env.get("ANICCA_HOME")
    if anicca_home:
        path = os.path.join(anicca_home, "skills", "earn", "state", "earn-ledger.jsonl")
        return path, True, "anicca_home_env"

    try:
        this_file = os.path.abspath(__file__)
    except NameError:
        return "", False, "unresolved_no_file_context"

    # this_file = <...>/skills/earn/self-improve/lib/ledger_reader.py
    # climb: lib -> self-improve -> earn
    earn_dir = os.path.dirname(os.path.dirname(os.path.dirname(this_file)))
    path = os.path.join(earn_dir, "state", "earn-ledger.jsonl")
    return path, True, "file_relative_default"


# Computed once at import time via the SAME REQ-RL1 logic (REQ-RL3) — kept for any external caller
# that references this attribute directly, and to keep the pre-existing test asserting its shape
# passing. NEVER the value `read_ledger`/`realized_summary` actually use internally when called
# with no explicit path (those resolve fresh, per call, via resolve_ledger_path() — REQ-RL3).
DEFAULT_LEDGER_PATH = resolve_ledger_path()[0]

# Mirrors skills/_shared/lib/ledger.mjs::SWAP_SOURCES verbatim.
SWAP_SOURCES = frozenset({"swap-eth-usdc", "swap", "swap-usdc-eth"})


def filter_own_wallet_rows(rows: list, own_wallets) -> list:
    """ledger-uniqueness REQ-003: wallet-based allow-list filter, mirroring
    `skills/_shared/lib/ledger.mjs::filterOwnWalletRows` exactly. Pure, read-only — never opens
    a file, never mutates `rows` or any row dict (returns a NEW list via a list comprehension).

    `own_wallets` is `None`, a single wallet string, or an iterable of wallet strings (this
    instance's own wallet address(es)). `None`/empty means "no known own wallet", so every
    walleted row is excluded (fail-closed). A row with no `wallet` key (or `wallet: None`) —
    Solana/Hyperliquid/narrate rows never stamp an EVM wallet — always passes through: it is
    never cross-instance-attributable by this check. Comparison is case-insensitive. This is an
    ALLOW-list (not the SHARED blacklist pinned in record-earn.mjs:39), so it fails closed
    against any foreign wallet, not only the three currently-pinned ones."""
    if own_wallets is None:
        wallets_list = []
    elif isinstance(own_wallets, str):
        wallets_list = [own_wallets]
    else:
        wallets_list = list(own_wallets)
    own_set = {w.lower() for w in wallets_list if isinstance(w, str) and w}

    kept = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        wallet = row.get("wallet")
        if wallet is None:
            kept.append(row)  # walletless row: always passes
            continue
        if not isinstance(wallet, str) or wallet == "":
            continue  # no proof of ownership
        if wallet.lower() in own_set:
            kept.append(row)
    return kept


def read_ledger(path: Optional[str] = None) -> list:
    """Read every JSONL line into a dict. `path=None` resolves fresh via `resolve_ledger_path()`
    (REQ-RL2/RL3: an explicit `path` always overrides; the default is NEVER a frozen constant).
    Missing file -> [] (never raises). Blank or malformed (non-JSON, or JSON that isn't an object)
    lines are skipped — mirrors `ledger.mjs::readLedger`'s own `.filter(Boolean)` / try-catch-null
    behavior exactly."""
    if path is None:
        path, _, _ = resolve_ledger_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return []
    rows = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def is_confirmed(line: Optional[dict]) -> bool:
    """REQ-RL6: IDENTICAL to `is_profitable`'s chain-correctness + non-swap + `external is True`
    checks, WITHOUT the `net_usdc > 0` requirement — so a confirmed LOSS (a redeemed losing
    Polymarket position, a closed-at-a-loss Hyperliquid fill) is still reported here, which
    `is_profitable` alone structurally cannot (it can never be True for a negative net_usdc)."""
    if not line:
        return False
    if str(line.get("source")) in SWAP_SOURCES:
        return False
    if line.get("external") is not True:
        return False
    evm_ok = bool(line.get("tx")) and line.get("status") == "0x1"
    sol_ok = bool(line.get("sig")) and line.get("confirmed") is True
    hl_ok = (
        line.get("chain") == "hyperliquid"
        and line.get("fill_tid") is not None
        and line.get("confirmed") is True
    )
    return bool(evm_ok or sol_ok or hl_ok)


def is_profitable(line: Optional[dict]) -> bool:
    """Mirrors `ledger.mjs::isProfitable` exactly: `is_confirmed(line) and net_usdc > 0`
    (REQ-RL6, DRY single source of truth for "real on-chain settlement")."""
    if not line:
        return False
    try:
        net_usdc = float(line.get("net_usdc", 0))
    except (TypeError, ValueError):
        return False
    if not (net_usdc > 0):
        return False
    return is_confirmed(line)


def confirmed_net_series(
    path: Optional[str] = None,
    window_start_ts: Optional[float] = None,
    window_end_ts: Optional[float] = None,
    own_wallets=None,
) -> list:
    """(ts, net_usdc) pairs for every `is_confirmed` row (REQ-RL6), optionally restricted to
    `[window_start_ts, window_end_ts)`. Powers REQ-RL8's `gate_math.realized_window_split` input
    and REQ-RL14's data_source row-count check. `path=None` resolves fresh (REQ-RL2/RL3, same
    convention as `read_ledger`/`realized_summary`).

    ledger-uniqueness REQ-003: `own_wallets` (default `None`) is a NEW, OPT-IN, non-breaking
    parameter. `None` (the default) applies NO filtering — behavior is byte-identical to this
    function's pre-feature implementation. When provided (a wallet string, an iterable of
    wallet strings, or `[]`), `filter_own_wallet_rows` is applied to the rows read from the
    ledger BEFORE `is_confirmed` classification, scoping the series to THIS instance's own
    wallet (+ walletless rows) and excluding contaminated foreign-wallet rows."""
    rows = read_ledger(path)
    if own_wallets is not None:
        rows = filter_own_wallet_rows(rows, own_wallets)
    series = []
    for row in rows:
        ts = row.get("ts")
        if ts is None:
            continue
        try:
            ts = float(ts)
        except (TypeError, ValueError):
            continue
        if window_start_ts is not None and ts < window_start_ts:
            continue
        if window_end_ts is not None and ts >= window_end_ts:
            continue
        if not is_confirmed(row):
            continue
        try:
            net_usdc = float(row.get("net_usdc", 0))
        except (TypeError, ValueError):
            continue
        series.append((ts, net_usdc))
    return series


def realized_summary(
    path: Optional[str] = None,
    window_start_ts: Optional[float] = None,
    window_end_ts: Optional[float] = None,
    own_wallets=None,
) -> dict:
    """The OBSERVE-step summary `run_evolve.sh` logs before every evolve run: real, ledger-derived
    realized net USD + the count of isProfitable rows, optionally restricted to
    `[window_start_ts, window_end_ts)` (unix seconds, `ledger.mjs`'s own `ts` convention — omit
    both for the ledger's full all-time history). A sparse or entirely-missing ledger degrades
    gracefully to an all-zero summary — this function never raises for a missing/empty/malformed
    ledger file (REQ-EV6-style fail-sentinel convention, applied here to a read, not a backtest).

    `path=None` (REQ-RL3) resolves FRESH via `resolve_ledger_path()` on every call — never a
    module-level constant frozen at import time — and the returned dict carries `resolved`/
    `resolution_source` (REQ-RL4) so a caller/log line can see WHICH resolution branch fired.

    ledger-uniqueness REQ-003: `own_wallets` (default `None`) is a NEW, OPT-IN, non-breaking
    parameter, identical convention to `confirmed_net_series` above — `None` never filters
    (byte-identical to pre-feature behavior); when provided, scopes `total_rows`/
    `profitable_row_count`/`realized_net_usd` to THIS instance's own wallet(s) + walletless
    rows, excluding contaminated foreign-wallet rows (the live 0xa3cdd4/0xb9dd3b67 contamination
    documented in behavioral-spec.md's Evidence trail)."""
    resolved = True
    resolution_source = "explicit_path"
    if path is None:
        path, resolved, resolution_source = resolve_ledger_path()

    rows = read_ledger(path)
    if own_wallets is not None:
        rows = filter_own_wallet_rows(rows, own_wallets)
    total_rows = len(rows)
    profitable_rows = []
    for row in rows:
        ts = row.get("ts")
        if window_start_ts is not None and (ts is None or ts < window_start_ts):
            continue
        if window_end_ts is not None and (ts is None or ts >= window_end_ts):
            continue
        if is_profitable(row):
            profitable_rows.append(row)
    realized_net_usd = sum(float(r.get("net_usdc", 0)) for r in profitable_rows)
    return {
        "ledger_path": path,
        "total_rows": total_rows,
        "profitable_row_count": len(profitable_rows),
        "realized_net_usd": round(realized_net_usd, 6),
        "resolved": resolved,
        "resolution_source": resolution_source,
    }


if __name__ == "__main__":
    # Runnable as `python3 lib/ledger_reader.py` for run_evolve.sh's OBSERVE step: prints ONE line
    # of JSON to stdout (nothing else), so a caller can log/parse it directly.
    print(json.dumps(realized_summary()))
