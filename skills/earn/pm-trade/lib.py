#!/usr/bin/env python3
"""pm-trade/lib.py — PURE decision math for the Polymarket earn slot (no I/O, no network, no keys).

The effectful shell (run.sh / pm-paper.py / executor) reads the live book and calls these; the MODEL
decides which market/side — these are just the arithmetic so it is testable and can never lie. Grounded
in polymarket-agent's KellyCriterion + REQ-PMTRADE (Quarter-Kelly, arb pair-cost first strategy).
"""


def edge(estimated_prob: float, market_prob: float) -> float:
    """Signed edge for a YES share: your prob minus the market's price (both 0..1)."""
    return estimated_prob - market_prob


def kelly_fraction(estimated_prob: float, price: float) -> float:
    """Full-Kelly fraction of bankroll for buying a $1-payout share at `price` when you believe `estimated_prob`.
    f* = (q - p) / (1 - p). Returns 0 for a non-favorable or degenerate bet (never negative, never for p>=1)."""
    if not (0.0 < price < 1.0) or not (0.0 <= estimated_prob <= 1.0):
        return 0.0
    f = (estimated_prob - price) / (1.0 - price)
    return f if f > 0.0 else 0.0


def position_size(estimated_prob: float, price: float, bankroll: float,
                  kelly_frac: float = 0.25, max_bet_pct: float = 0.05,
                  min_edge: float = 0.15, gas_reserve: float = 0.0) -> float:
    """USDC to stake: quarter-Kelly by default, capped at max_bet_pct of bankroll, 0 unless edge >= min_edge.
    Never stakes the gas_reserve. Returns 0.0 when no bet is warranted."""
    if bankroll <= gas_reserve or edge(estimated_prob, price) < min_edge:
        return 0.0
    usable = bankroll - gas_reserve
    frac = kelly_frac * kelly_fraction(estimated_prob, price)
    stake = frac * usable
    cap = max_bet_pct * usable
    stake = min(stake, cap)
    return stake if stake > 0.0 else 0.0


def side_won(side: str, closed_up: bool) -> bool:
    """Did the chosen side win? UP wins iff the window closed up; DOWN wins iff it closed down."""
    if side == "UP":
        return bool(closed_up)
    if side == "DOWN":
        return not bool(closed_up)
    return False


def settle_pnl(won: bool, entry_price: float, size_usdc: float) -> float:
    """Realized P&L (USDC) for a resolved Polymarket share position bought at `entry_price` for `size_usdc`.
    A winning share redeems at $1 → pnl = size*(1-p)/p; a loser → pnl = -size. Pure, no I/O."""
    if size_usdc <= 0.0 or not (0.0 < entry_price < 1.0):
        return 0.0
    if won:
        return size_usdc * (1.0 - entry_price) / entry_price
    return -size_usdc


def arb_pair_profit(ask_yes: float, ask_no: float) -> float:
    """Risk-free profit per $1 of paired YES+NO when their combined ask < $1 (one side always redeems at $1).
    Returns 0.0 when there is no arb (combined ask >= 1). This is the highest-win-rate first strategy."""
    if not (0.0 < ask_yes < 1.0) or not (0.0 < ask_no < 1.0):
        return 0.0
    profit = 1.0 - (ask_yes + ask_no)
    return profit if profit > 0.0 else 0.0
