"""Public (no-auth) CLOB order-book snapshot + microprice.

poly-maker maintains a live async WS order book
(src/polymaker/marketdata/orderbook.py) fed by the market websocket. This
port does not run a persistent WS connection (paper mode is a one-shot
scan+quote CLI, not a long-lived process yet — see paper_run.py and the
"loop 配線案" in SKILL.md for how a real WS engine would replace this).
Instead it polls Polymarket's public REST book endpoint
(`GET https://clob.polymarket.com/book?token_id=...`), which needs NO
authentication (verified live 2026-07-12) and returns the same bids/asks
poly-maker's WS book converges to. Good enough for a paper snapshot; a live
engine should upgrade this call site to the WS feed for latency.
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

CLOB_HOST = "https://clob.polymarket.com"


@dataclass(frozen=True, slots=True)
class BookView:
    best_bid: float | None
    best_ask: float | None
    bid_depth: float  # size resting at best_bid
    ask_depth: float  # size resting at best_ask


def fetch_book(token_id: str, clob_host: str = CLOB_HOST, timeout: float = 15.0) -> BookView:
    """Fetch and parse one token's live order book. Fails closed to an
    empty BookView (both sides None) on any network/parse error — callers
    must treat that as "can't quote this token right now", never a fake 0.5."""
    try:
        r = requests.get(f"{clob_host}/book", params={"token_id": token_id}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError):
        return BookView(None, None, 0.0, 0.0)

    bids = data.get("bids") or []
    asks = data.get("asks") or []
    best_bid = None
    bid_depth = 0.0
    if bids:
        best = max(bids, key=lambda b: float(b["price"]))
        best_bid = float(best["price"])
        bid_depth = float(best["size"])
    best_ask = None
    ask_depth = 0.0
    if asks:
        best = min(asks, key=lambda a: float(a["price"]))
        best_ask = float(best["price"])
        ask_depth = float(best["size"])
    return BookView(best_bid, best_ask, bid_depth, ask_depth)


def microprice(view: BookView, fallback: float = 0.5) -> float:
    """Depth-weighted microprice; falls back to plain mid, then to
    `fallback` (never crashes on a one-sided or empty book — a thin/gapped
    reward market's book can legitimately be one-sided)."""
    if view.best_bid is None and view.best_ask is None:
        return fallback
    if view.best_bid is None:
        return view.best_ask
    if view.best_ask is None:
        return view.best_bid
    total_depth = view.bid_depth + view.ask_depth
    if total_depth <= 0:
        return (view.best_bid + view.best_ask) / 2.0
    # standard depth-weighted microprice: more resting size on one side
    # (more pressure to absorb) pulls price toward the OTHER side's touch.
    return (view.best_bid * view.ask_depth + view.best_ask * view.bid_depth) / total_depth
