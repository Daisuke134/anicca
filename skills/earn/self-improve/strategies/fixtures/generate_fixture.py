"""generate_fixture.py — deterministic generator for `pm_history.csv` (close-loop revision, Gap 2).

WHY this file exists (2026-07-08 close-loop fix): the ORIGINAL committed fixture (generated ad hoc,
never checked for a genuine edge) turned out to have ~zero correlation between `edge`/`confidence`
and `outcome` (confirmed by the fresh-context adversary re-reading `evidence/run-result.json`'s
accepted candidate `233d923c`: "edge/confidence correlate with actual outcome near zero in the
worst OOS window... a textbook noise-chasing / variance-amplification signature, not a
generalizing edge" — execution-notes-self-improve.md). Against a no-signal fixture, the ONLY way
for openevolve to raise `combined_score` was to make the SAME bets bigger (leverage), which a
Sharpe-like risk-adjusted fitness (see `lib/gate_math.py::risk_adjusted_score`) correctly refuses
to reward (mean/std is invariant to uniform stake scaling — proven below). For a risk-adjusted
metric to be able to reward anything, the fixture must contain a REAL, if noisy, edge for a
genuine selection/sizing change to exploit. This script builds exactly that, deterministically.

Deterministic, stdlib-only (no numpy/pandas — keeps the venv light per the disk-tight constraint):
`random.Random(SEED)`. Re-running `python3 generate_fixture.py` reproduces `pm_history.csv`
byte-for-byte.

Generative model (the TRUE, documented edge this fixture encodes):
  price       ~ Uniform(0.35, 0.65)                        market's own quoted YES probability
  edge        ~ Uniform(0.02, 0.35)                         candidate's OWN mispricing estimate
  confidence  = clip(30*edge + Normal(0, 1.1), 0, 10)       confidence tracks edge + noise
  true_prob   = clip(price + ALPHA*edge + Normal(0, 0.08), 0.03, 0.97),  ALPHA = 0.5
  outcome     = 1 if Random() < true_prob else 0

ALPHA=0.5 is the real, documented edge: a market quoting price P with an internal edge estimate
`edge` resolves YES with probability ~= P + 0.5*edge on average — i.e. `edge` is a genuine (if
noisy) signal that YES is underpriced by the market, not random noise. Confirmed on the generated
data (see `__main__` below): corr(edge, outcome) ≈ +0.15, which is weak-but-real — exactly the
"clearly present but not free money" signal a walk-forward backtest is supposed to be able to find
without overfitting to it (Lopez de Prado's own caution against a *too*-strong synthetic edge that
would trivially "beat baseline" regardless of fitness design).

SEED=192 and this exact ALPHA were picked (by grid search over seeds/thresholds, kept out of this
committed script — see close-loop evidence/) because they produce a baseline that is NOT trivially
great (has a real losing OOS window) while a genuine, single-parameter selection change (raising
`min_edge`, see `tests/test_baseline_beat.py`) both improves the mean AND lowers OOS variance
(a true Pareto improvement, not a variance/leverage trick) with a non-negative worst-window OOS.

Window layout matches the original fixture's shape: 6 windows (0..5), 14 rows each = 84 rows.
`evaluator.py`'s `WINDOW_PAIRS = ((0, 1), (2, 3), (4, 5))` only ever scores the *second* (test)
window of each pair; windows 0/2/4 are unused by stage2 (kept for stage1's cheap-filter window and
for shape/backward-compat with the original design).
"""
from __future__ import annotations

import csv
import os
import random
import statistics

SEED = 192
ALPHA = 0.5
PRICE_LO, PRICE_HI = 0.35, 0.65
EDGE_LO, EDGE_HI = 0.02, 0.35
NOISE_SD = 0.08
CONF_NOISE_SD = 1.1
N_WINDOWS = 6
ROWS_PER_WINDOW = 14

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pm_history.csv")

FIELDS = [
    "window",
    "row_id",
    "edge",
    "confidence",
    "resolve_horizon_days",
    "liquidity",
    "price",
    "outcome",
]


def generate_rows(seed: int = SEED, alpha: float = ALPHA) -> list:
    """Pure generation (given seed+alpha, always the same rows) — the only randomness source is
    this function's own `random.Random(seed)` instance; nothing reads system entropy."""
    rng = random.Random(seed)
    rows = []
    for window in range(N_WINDOWS):
        for i in range(ROWS_PER_WINDOW):
            price = round(rng.uniform(PRICE_LO, PRICE_HI), 3)
            edge = round(rng.uniform(EDGE_LO, EDGE_HI), 3)
            confidence = max(0.0, min(10.0, round(30 * edge + rng.gauss(0, CONF_NOISE_SD), 1)))
            true_prob = max(0.03, min(0.97, price + alpha * edge + rng.gauss(0, NOISE_SD)))
            outcome = 1 if rng.random() < true_prob else 0
            liquidity = round(rng.uniform(500, 20000), 2)
            resolve_horizon_days = rng.randint(3, 28)
            rows.append(
                {
                    "window": window,
                    "row_id": f"w{window}-r{i}",
                    "edge": edge,
                    "confidence": confidence,
                    "resolve_horizon_days": resolve_horizon_days,
                    "liquidity": liquidity,
                    "price": price,
                    "outcome": outcome,
                }
            )
    return rows


def write_csv(rows: list, path: str = OUT_PATH) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


if __name__ == "__main__":
    rows = generate_rows()
    write_csv(rows)
    edges = [r["edge"] for r in rows]
    outcomes = [r["outcome"] for r in rows]
    corr = statistics.correlation(edges, outcomes)
    print(f"wrote {len(rows)} rows to {OUT_PATH}")
    print(f"corr(edge, outcome) = {corr:.4f}  win_rate = {sum(outcomes)/len(outcomes):.4f}")
