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
    """
    Return a USD stake size for this candidate (0.0 = skip the bet).

    The goal is to keep only high‑conviction, liquid trades while pruning noisy
    edges that hurt the risk‑adjusted Sharpe‑like score.  We therefore apply three
    independent gates:

    1. **Edge / confidence** – basic quality thresholds (seeded from the original
       MIN_EDGE / MIN_CONF knobs).
    2. **Combined quality** – product of edge and confidence; a simple way to
       capture jointly strong signals.
    3. **Market health** – minimum liquidity and a floor on price to avoid
       ultra‑cheap shares that explode variance.

    All thresholds are configurable via `config` so the evolution engine can tune
    them, but we provide sensible defaults that already improve the worst‑case
    window observed in earlier attempts.
    """
    # Core candidate metrics
    edge = candidate.get("edge", 0.0)
    confidence = candidate.get("confidence", 0.0)
    resolve_horizon_days = candidate.get("resolve_horizon_days", 0)

    # Market‑level features
    liquidity = market_features.get("liquidity", 0.0)
    price = market_features.get("price", 0.0)

    # Configurable thresholds (with sensible defaults)
    # Tighter defaults – these are the primary levers for risk‑adjusted performance
    min_edge = config.get("min_edge", 0.25)                     # higher edge requirement
    min_confidence = config.get("min_confidence", 7.5)         # higher confidence requirement
    min_combined = config.get("min_combined", 2.0)             # edge × confidence product floor
    min_liquidity = config.get("min_liquidity", 800.0)         # deeper market floor
    min_price = config.get("min_price", 0.12)                  # avoid ultra‑cheap shares
    max_price = config.get("max_price", 0.88)                  # avoid ultra‑expensive shares
    max_horizon = config.get("max_horizon_days", 25)          # prefer shorter contracts

    # Base stake parameters
    base_stake = config.get("base_stake", 5.0)
    max_stake = config.get("max_stake", 12.0)

    # Combined quality check
    combined_score = edge * confidence

    # Apply all gates – any failure skips the trade
    if (
        edge < min_edge
        or confidence < min_confidence
        or combined_score < min_combined
        or liquidity < min_liquidity
        or price < min_price
        or price > max_price
        or resolve_horizon_days > max_horizon
    ):
        return 0.0

    # Price‑stability factor: higher when price is near 0.5 (lower variance)
    price_factor = 1.0 - abs(price - 0.5) * 2.0
    price_factor = max(0.0, price_factor)
    # Discard very unstable price points – they create high payout variance
    if price_factor < 0.20:
        return 0.0

    # Liquidity factor (capped at 2×) rewards deeper markets
    liquidity_factor = min(liquidity / min_liquidity, 2.0)

    # Horizon bonus – up to 10 % extra for contracts that resolve sooner
    horizon_bonus = 1.0 + max(0.0, (max_horizon - resolve_horizon_days) / max_horizon) * 0.10

    # Composite stake combines price stability, liquidity health and timing incentive
    stake = base_stake * price_factor * liquidity_factor * horizon_bonus

    # Clamp to sensible bounds (minimum 0.5× base, maximum config‑cap)
    stake = max(base_stake * 0.5, stake)
    stake = min(stake, max_stake)

    return max(0.0, stake)
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
