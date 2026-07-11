"""Pure quote construction: (market, book, inventory, params) -> quotes.

Ported (simplified — single price layer per side instead of poly-maker's
multi-layer ladder; no async, no I/O) from poly-maker's
src/polymaker/strategy/quoting.py (MIT, warproxxx/poly-maker). No I/O, no
wall-clock reads except values passed in — a pure function, unit-tested
directly with synthetic inputs in test_reward_mm.py.

Model (matches upstream):
  reservation  r  = FV - skew(inventory)
  half-spread  δ  = base + c_vol·σ + c_tox·toxicity   (clamped to the
                     Polymarket reward band while QUIET)
  YES entry bid   = r - δ   (BUY YES, post-only, USDC-collateralized)
  NO  entry bid   = (1 - r) - δ   (BUY NO; implied YES ask at r + δ)

Both legs are BUYs (bids) — Polymarket's liquidity-rewards program scores
resting bids inside the band regardless of direction, so quoting BOTH
sides as bids means BOTH legs can earn reward share simultaneously, and a
filled pair on a binary market (YES+NO=$1) merges back to USDC at locked
edge `1 - p - q` without ever crossing the spread (maker-only exit).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from reward_mm.book import BookView
from reward_mm.gamma_scan import MarketMeta
from reward_mm.profiles import StrategyProfile
from reward_mm.regime import Regime

_EPS = 1e-9


@dataclass(frozen=True, slots=True)
class Quote:
    token_id: str
    side: str  # "BUY" | "SELL"
    price: float
    size: float
    post_only: bool = True


@dataclass(frozen=True, slots=True)
class QuoteInputs:
    meta: MarketMeta
    regime: Regime
    fv: float  # YES fair value in (0,1)
    vol_short: float
    toxicity: float
    yes_view: BookView
    no_view: BookView
    profile: StrategyProfile
    pos_yes_size: float = 0.0
    pos_no_size: float = 0.0
    risk_size_scale: float = 1.0  # RiskManager output, [0,1]


def round_to_tick(price: float, tick: float, decimals: int, *, up: bool) -> float:
    n = price / tick
    n = math.ceil(n - _EPS) if up else math.floor(n + _EPS)
    p = round(n * tick, decimals)
    return min(max(p, tick), 1.0 - tick)


def compute_fair_value(microprice: float, flow_z: float, tick: float, weight: float = 0.5) -> float:
    """Nudge the microprice by bounded signed order-flow. Clamped to (tick, 1-tick)."""
    fv = microprice + weight * flow_z * tick
    return min(max(fv, tick), 1.0 - tick)


def _clamp(x: float, lo: float, hi: float) -> float:
    return min(max(x, lo), hi)


def _place_bid(target: float, view: BookView, tick: float, dec: int, fv: float, min_edge_ticks: float) -> float | None:
    """Position a BUY: join the touch or sit behind, never cross, keep min edge vs FV."""
    price = target
    price = min(price, fv - min_edge_ticks * tick)
    if view.best_bid is not None and price >= view.best_bid:
        price = view.best_bid
    if view.best_ask is not None and price >= view.best_ask:
        price = view.best_ask - tick
    p = round_to_tick(price, tick, dec, up=False)
    if p <= 0 or p >= 1:
        return None
    return p


def construct_quotes(inp: QuoteInputs) -> list[Quote]:
    m = inp.meta
    p = inp.profile
    tick = m.tick_size
    dec = m.price_decimals

    if inp.regime in (Regime.EVENT, Regime.HALTED):
        return []

    quotes: list[Quote] = []

    # ── inventory in YES-equivalent shares ────────────────────────────
    net_shares = inp.pos_yes_size - inp.pos_no_size
    q_max_shares = p.q_max_usdc / max(inp.fv, tick)
    u = _clamp(net_shares / q_max_shares, -1.0, 1.0) if q_max_shares > 0 else 0.0
    reward_floor = m.rewards_min_size * p.reward_size_mult

    skew = p.gamma * inp.vol_short * u

    # ── half-spread ─────────────────────────────────────────────────
    base = p.delta_min_ticks * tick
    delta = base + p.c_vol * inp.vol_short + p.c_tox * inp.toxicity
    reward_band = m.rewards_max_spread / 100.0
    if inp.regime == Regime.QUIET and reward_band > 0:
        delta = _clamp(delta, base, max(base, reward_band))
    delta = max(delta, tick)

    r = inp.fv - skew
    yes_bid_target = r - delta
    no_bid_target = (1.0 - r) - delta

    regime_scale = 0.5 if inp.regime == Regime.TRENDING else 1.0
    tox_scale = 1.0 / (1.0 + inp.toxicity * 10.0)
    common_scale = regime_scale * tox_scale * _clamp(inp.risk_size_scale, 0.0, 1.0)

    soft_cap = p.q_soft_frac
    add_yes = inp.regime != Regime.REDUCE_ONLY and u < soft_cap
    add_no = inp.regime != Regime.REDUCE_ONLY and u > -soft_cap

    if add_yes:
        price = _place_bid(yes_bid_target, inp.yes_view, tick, dec, inp.fv, p.min_edge_ticks)
        if price is not None:
            size = _order_size(p.base_size_usdc, price, common_scale * (1 - max(u, 0.0)), m, reward_floor)
            if size > 0:
                quotes.append(Quote(m.yes.token_id, "BUY", price, size))

    if add_no:
        no_fv = 1.0 - inp.fv
        price = _place_bid(no_bid_target, inp.no_view, tick, dec, no_fv, p.min_edge_ticks)
        if price is not None:
            size = _order_size(p.base_size_usdc, price, common_scale * (1 - max(-u, 0.0)), m, reward_floor)
            if size > 0:
                quotes.append(Quote(m.no.token_id, "BUY", price, size))

    return quotes


def _order_size(base_usdc: float, price: float, scale: float, m: MarketMeta, reward_floor: float) -> float:
    """USDC-notional sizing -> shares, bumped up to the reward-scoring
    floor when within reach (the program scores per ORDER, so a floor
    applied only to the total is worthless — same logic as poly-maker's
    _add_layers, collapsed here to a single layer)."""
    shares = (base_usdc / max(price, m.tick_size)) * max(scale, 0.0)
    shares = round(shares, 2)
    floor = max(reward_floor, m.min_order_size)
    if floor > 0 and 0.5 * floor <= shares < floor:
        shares = floor
    if shares < m.min_order_size:
        return 0.0
    return shares
