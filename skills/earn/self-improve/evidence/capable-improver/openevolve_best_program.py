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
    # core candidate signals
    edge = candidate.get("edge", 0.0)
    confidence = candidate.get("confidence", 0.0)
    horizon = candidate.get("resolve_horizon_days", 0)

    # market‑level signals
    price = market_features.get("price", 0.0)          # cost per YES share (0…1)
    liquidity = market_features.get("liquidity", 0.0)

    # configurable thresholds (with stricter defaults)
    min_edge = config.get("min_edge", 0.18)
    min_confidence = config.get("min_confidence", 7.0)
    min_liquidity = config.get("min_liquidity", 0.4)   # avoid very illiquid markets
    max_price = config.get("max_price", 0.85)          # avoid overpriced contracts
    # Require a stronger combined conviction before taking a bet.
    # Raising the default from 1.2 → 1.5 cuts many low‑signal trades that tend to
    # increase variance without adding much upside.
    min_combined = config.get("min_combined", 1.5)    # edge × confidence must exceed this
    max_horizon = config.get("max_horizon_days", 30) # discard very long‑horizon bets
    base_stake = config.get("base_stake", 5.0)

    # extra knobs for adaptive sizing
    max_confidence = config.get("max_confidence", 30.0)   # expected upper bound for confidence
    edge_weight = config.get("edge_weight", 0.25)          # influence of edge in stake scaling
    conf_weight = config.get("conf_weight", 0.45)          # influence of confidence in stake scaling
    price_weight = config.get("price_weight", 0.25)        # penalty weight for high price
    horizon_weight = config.get("horizon_weight", 0.15)  # penalty weight for long horizons

    # ---- selection logic -------------------------------------------------
    # 1️⃣ Basic quality filters
    if edge < min_edge or confidence < min_confidence:
        return 0.0
    # 2️⃣ Market health filters
    # Market health filters – enforce basic liquidity and price sanity.
    if liquidity < min_liquidity or price > max_price:
        return 0.0
    # Extra strict price ceiling – contracts that are too expensive tend to
    # compress upside (price near 1 means you buy very few shares).  The
    # default 0.7 is tighter than the generic max_price (0.85) but can be
    # overridden via the `strict_max_price` knob.
    strict_max_price = config.get("strict_max_price", 0.7)
    # Additional liquidity tightening factor (default 1.5× the base min_liquidity)
    min_liquidity_factor = config.get("min_liquidity_factor", 1.5)
    if liquidity < min_liquidity * min_liquidity_factor:
        return 0.0
    # Additional price tightening factor (default 0.9 of strict_max_price)
    price_strict_factor = config.get("price_strict_factor", 0.9)
    if price > strict_max_price * price_strict_factor:
        return 0.0
    # 3️⃣ Combined conviction filter – higher edge * confidence signals stronger
    #    opportunities and helps cut noisy, low‑signal trades that inflate variance.
    if (edge * confidence) < min_combined:
        return 0.0
    # 4️⃣ Horizon filter – avoid bets that resolve too far in the future
    if horizon > max_horizon:
        return 0.0

    # ---- adaptive stake calculation ---------------------------------------
    # Normalize edge and confidence to [0, 1] ranges (capped to avoid extreme scaling)
    # Normalise edge more aggressively – using *2 gives a higher multiplier for
    # edges that clear the minimum threshold, encouraging stronger signals.
    edge_norm = min(edge / (min_edge * 2), 1.0)                     # more aggressive scaling
    conf_norm = min(confidence / max_confidence, 1.0)               # 0‑1 relative to an expected max

    # Price penalisation: cheaper contracts are preferable; the closer price is to max_price,
    # the larger the penalty. When price == max_price the factor becomes 0.
    price_factor = max(0.0, (max_price - price) / max_price)       # 0‑1

    # Horizon factor: shorter horizons are preferred.
    horizon_factor = max(0.0, (max_horizon - horizon) / max_horizon)  # 0‑1

    # Combine the normalized signals into a multiplier.
    # Base 0.4 ensures we never go below 40 % of the base stake on a valid trade.
    multiplier = (
        0.4
        + edge_weight * edge_norm
        + conf_weight * conf_norm
    )
    # Apply price and horizon penalties multiplicatively.
    multiplier *= (1.0 - price_weight * (1.0 - price_factor))
    multiplier *= (1.0 - horizon_weight * (1.0 - horizon_factor))

    # Cap multiplier to avoid runaway stakes.
    multiplier = min(multiplier, 1.5)

    # Final stake respects the base_stake and the calculated multiplier.
    stake = base_stake * multiplier
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
