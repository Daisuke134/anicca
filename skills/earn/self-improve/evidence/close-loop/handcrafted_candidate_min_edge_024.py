"""pm_backtest_strategy.py — the self-contained, deterministic, backtestable openevolve program
this feature evolves.

NOT `skills/earn/polymarket-trade/pick.py` and NEVER imports/invokes it (behavioral-spec.md
"Architecture Decision" — pick.py's judgment is a live multi-model-consensus network call, not a
pure backtestable function; integrating it is out of scope this phase). The numeric-threshold
SHAPE of pick.py's knobs (MIN_EDGE/MIN_CONF) informs `score_candidate`'s seed formula below as a
design analogy only — this is a NEW artifact.

FIXED region (openevolve/scope_guard.py NEVER lets this change): the fixture loader and the
backtest harness below. EVOLVE region (the ONLY thing openevolve may rewrite): `score_candidate`.
No network call, no wallet access, no LLM call, no I/O of any kind is reachable from inside the
EVOLVE-BLOCK — `score_candidate` reads only its three plain-data arguments.
"""
from __future__ import annotations

import csv
import os

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "pm_history.csv")


def load_fixture(path: str = FIXTURE_PATH):
    """Read-only load of the historical PM fixture CSV. Never writes. Returns list[dict], one
    dict per historical candidate row: {window, row_id, edge, confidence,
    resolve_horizon_days, liquidity, price, outcome}."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                {
                    "window": int(r["window"]),
                    "row_id": r["row_id"],
                    "edge": float(r["edge"]),
                    "confidence": float(r["confidence"]),
                    "resolve_horizon_days": int(r["resolve_horizon_days"]),
                    "liquidity": float(r["liquidity"]),
                    "price": float(r["price"]),
                    "outcome": int(r["outcome"]),
                }
            )
    return rows


# EVOLVE-BLOCK-START
def score_candidate(candidate, market_features, config) -> float:
    """Return a USD stake size for this candidate (0.0 = skip the bet). This is the ONLY thing
    openevolve may rewrite. Pure function: no I/O, no network, no wallet, no LLM call — it reads
    only its three plain-data arguments and returns a number.

    `candidate` carries {edge, confidence, resolve_horizon_days} for one historical market
    opportunity. `market_features` carries {liquidity, price} (price = cost per YES share, 0..1).
    `config` carries fixed run parameters (min_edge, min_confidence, base_stake), analogous in
    SHAPE to skills/earn/lib/genome.mjs::KNOB_KEYS (MIN_EDGE/MIN_CONF), but expressed as evolvable
    CODE rather than a numeric knob list — openevolve may propose new features, different
    combination formulas, or sizing logic, not only threshold nudges."""
    edge = candidate.get("edge", 0.0)
    confidence = candidate.get("confidence", 0.0)
    min_edge = config.get("min_edge", 0.24)
    min_confidence = config.get("min_confidence", 6.0)
    base_stake = config.get("base_stake", 5.0)
    if edge < min_edge or confidence < min_confidence:
        return 0.0
    return base_stake
# EVOLVE-BLOCK-END


def _stake_for_row(row: dict, config: dict) -> float:
    candidate = {
        "edge": row["edge"],
        "confidence": row["confidence"],
        "resolve_horizon_days": row["resolve_horizon_days"],
    }
    market_features = {"liquidity": row["liquidity"], "price": row["price"]}
    stake = score_candidate(candidate, market_features, config)
    try:
        return max(0.0, float(stake or 0.0))
    except (TypeError, ValueError):
        return 0.0


def run_backtest(rows=None, config=None) -> dict:
    """Deterministic backtest over `rows` (defaults to the full fixture). Returns
    {"gross_usd", "cost_usd", "net_usd", "n_trades"}.

    Cost model mirrors skills/_shared/lib/ledger.mjs::deriveLine (earn - cost = net, REQ-GR2): for
    every row where `score_candidate` returns a positive stake, `cost_usd` accumulates the stake
    (paid regardless of outcome) and `gross_usd` accumulates the payout ONLY for winning trades
    (each YES share pays exactly $1 on resolution; shares purchased = stake / price)."""
    if rows is None:
        rows = load_fixture()
    cfg = config or {}
    gross_usd = 0.0
    cost_usd = 0.0
    n_trades = 0
    for row in rows:
        stake = _stake_for_row(row, cfg)
        if stake <= 0.0:
            continue
        price = max(1e-6, row["price"])
        shares = stake / price
        cost_usd += stake
        n_trades += 1
        if row["outcome"] == 1:
            gross_usd += shares * 1.0
    net = gross_usd - cost_usd
    return {"gross_usd": gross_usd, "cost_usd": cost_usd, "net_usd": net, "n_trades": n_trades}


if __name__ == "__main__":
    print(run_backtest())
