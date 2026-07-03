#!/usr/bin/env python3
"""momentum.py — PURE latency/momentum edge for Polymarket 5-min BTC up/down (no I/O, no keys).

The real Polymarket inefficiency (verified 2026-07-04: resting-book arb = $0, all pinned at $1.0010): the
5-min BTC up/down market reprices SLOWER than Binance spot. When spot has already moved this window, "up"
at close is more/less likely than the market's YES price implies → a signed edge. The effectful shell
(decide.py) fetches spot + the market YES price and calls these; lib.position_size does the sizing.
"""


def prob_up_from_return(window_return: float, k: float = 40.0) -> float:
    """Estimate P(BTC closes UP for this 5-min window) from the return SO FAR in the window.
    Logistic-ish clamp around 0.5: a bigger realized move → stronger conviction, bounded to (0,1).
    k tunes sensitivity (return is a fraction, e.g. +0.002 = +0.2%). Pure, monotonic, symmetric."""
    p = 0.5 + k * window_return
    if p < 0.01:
        return 0.01
    if p > 0.99:
        return 0.99
    return p


def momentum_edge(window_return: float, yes_price: float, k: float = 40.0) -> float:
    """Signed edge for the 'UP' YES share: our momentum-implied prob minus the market's YES price.
    Positive → buy YES (up underpriced); negative → up overpriced (buy NO / sell). 0 for a bad price."""
    if not (0.0 < yes_price < 1.0):
        return 0.0
    return prob_up_from_return(window_return, k) - yes_price


def side_and_prob(window_return: float, yes_price: float, no_price: float, k: float = 40.0):
    """Pick the side with positive edge and return (side, price, estimated_prob) or (None, None, None).
    side='UP' uses yes_price + P(up); side='DOWN' uses no_price + P(down)=1-P(up). Never returns a side
    whose edge <= 0. Prefers the larger-edge side when both are (rare)."""
    p_up = prob_up_from_return(window_return, k)
    up_edge = (p_up - yes_price) if 0.0 < yes_price < 1.0 else -1.0
    dn_edge = ((1.0 - p_up) - no_price) if 0.0 < no_price < 1.0 else -1.0
    if up_edge <= 0.0 and dn_edge <= 0.0:
        return (None, None, None)
    if up_edge >= dn_edge:
        return ("UP", yes_price, p_up)
    return ("DOWN", no_price, 1.0 - p_up)
