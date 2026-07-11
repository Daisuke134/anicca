"""Strategy parameter profiles — ported from poly-maker's config/strategy.toml
(MIT, warproxxx/poly-maker), which the upstream author tuned from LIVE
microstructure samples of real reward-eligible Polymarket markets
(2026-07-06: "newsom-mm" = Gavin Newsom 2028 Dem-nomination market;
"romania-pm" = Next PM of Romania market). We keep the same two shapes
because they cover the two real regimes poly-maker's author found:

  reward-heavy / deep book  -> "default" profile (was newsom-mm)
  reward-min / thin book    -> "thin-book" profile (was romania-pm)

These are starting points, not hardcoded truth — a loop that self-improves
should tune them from its OWN paper/live fill history, not treat these as
gospel forever. Recorded here (not invented) so the FIRST run has sane,
live-verified numbers instead of guesses.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StrategyProfile:
    name: str
    # --- fair value ---
    flow_ewma_halflife_s: float = 120.0
    # --- spread / skew ---
    gamma: float = 0.6  # inventory skew strength
    delta_min_ticks: float = 2.0  # half-spread floor, in ticks
    c_vol: float = 1.5
    c_tox: float = 3.0
    # --- vol horizons ---
    vol_short_halflife_s: float = 10.0
    vol_long_halflife_s: float = 900.0
    # --- sizing / inventory ---
    base_size_usdc: float = 100.0  # per token side, per order
    q_max_usdc: float = 200.0  # NET directional cap (YES minus NO exposure)
    q_soft_frac: float = 0.6  # stop adding at this fraction of q_max
    reward_size_mult: float = 1.5  # bump reward-eligible orders to this x the min
    min_edge_ticks: float = 1.0  # never bid above FV - min_edge*tick
    # --- regime ---
    event_jump_ticks: float = 6.0
    event_cooloff_s: float = 30.0
    trend_flow_z: float = 1.8
    trend_vol_ratio: float = 3.0
    # --- lifecycle ---
    reduce_only_hours: float = 24.0
    halt_before_hours: float = 2.0


# ported from poly-maker config/strategy.toml [profiles.newsom-mm]
# (deep, quiet book: ~$52/day reward rate, 5.5c reward band, 2-tick spread)
DEFAULT = StrategyProfile(
    name="default",
    flow_ewma_halflife_s=120.0,
    gamma=0.6,
    delta_min_ticks=2.0,
    c_vol=1.5,
    c_tox=3.0,
    vol_short_halflife_s=10.0,
    vol_long_halflife_s=900.0,
    base_size_usdc=100.0,
    q_max_usdc=200.0,
    q_soft_frac=0.6,
    reward_size_mult=1.5,
    min_edge_ticks=1.0,
    event_jump_ticks=6.0,
    event_cooloff_s=30.0,
    trend_flow_z=1.8,
    trend_vol_ratio=3.0,
    reduce_only_hours=24.0,
    halt_before_hours=2.0,
)

# ported from poly-maker config/strategy.toml [profiles.romania-pm]
# (thin/gap-prone book: floor every order to exactly the reward minimum,
# don't try to be the market's whole book; ~$257/day reward rate, 4.5c band)
THIN_BOOK = StrategyProfile(
    name="thin-book",
    flow_ewma_halflife_s=120.0,
    gamma=0.6,
    delta_min_ticks=1.0,
    c_vol=1.5,
    c_tox=3.0,
    vol_short_halflife_s=10.0,
    vol_long_halflife_s=900.0,
    base_size_usdc=22.0,  # ~the reward min at typical thin-book prices
    q_max_usdc=100.0,
    q_soft_frac=0.6,
    reward_size_mult=1.0,
    min_edge_ticks=1.0,
    event_jump_ticks=5.0,
    event_cooloff_s=30.0,
    trend_flow_z=2.6,
    trend_vol_ratio=5.0,
    reduce_only_hours=24.0,
    halt_before_hours=2.0,
)


def profile_for(liquidity_num: float) -> StrategyProfile:
    """Pick a profile by book depth. Bookkeeping (a threshold on a fetched
    number), not a market/side judgment — the market SELECTION itself
    (which markets to even consider) is gamma_scan.score_market's job."""
    return DEFAULT if liquidity_num >= 5000.0 else THIN_BOOK
