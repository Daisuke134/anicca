"""RiskManager — pre-trade gates and circuit breakers, ported (simplified,
sync, no StateStore/SQLite dependency) from poly-maker's
src/polymaker/risk/manager.py (MIT, warproxxx/poly-maker).

Consulted before every quote set. Returns a per-market decision (size
scale / reduce-only / halt) and owns the daily-loss kill switch. In paper
mode there are no real fills, so PnL bookkeeping is fed synthetically by
the caller (paper_run.py) from a local paper ledger — this class itself
has no I/O and doesn't know it's in paper mode.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RiskConfig:
    daily_loss_kill_usdc: float = 20.0
    max_order_error_rate: float = 0.5
    max_market_notional_usdc: float = 200.0
    max_event_group_loss_usdc: float = 400.0
    max_total_exposure_usdc: float = 500.0


@dataclass(frozen=True, slots=True)
class RiskDecision:
    halt: bool
    reduce_only: bool
    size_scale: float  # multiply quote sizes by this, in [0,1]
    reason: str = ""


def _headroom(current: float, cap: float) -> float:
    """1.0 well below the cap, tapering to 0 as we approach it (from 70%)."""
    if cap <= 0:
        return 1.0
    frac = current / cap
    if frac <= 0.7:
        return 1.0
    return max(0.0, (1.0 - frac) / 0.3)


@dataclass
class RiskManager:
    cfg: RiskConfig = field(default_factory=RiskConfig)
    _net_cash: float = 0.0  # cumulative signed cash from fills (+sell, -buy)
    _day_start_equity: float = 0.0
    _killed: bool = False
    _order_attempts: int = 0
    _order_errors: int = 0
    _marks: dict = field(default_factory=dict)  # token_id -> fair value
    _positions: dict = field(default_factory=dict)  # token_id -> {"size", "avg_price"}

    # ── PnL bookkeeping (paper ledger, see paper_run.py) ─────────────────
    def note_fill(self, side: str, price: float, size: float) -> None:
        self._net_cash += (price * size) * (1 if side == "SELL" else -1)

    def update_mark(self, token_id: str, fv: float) -> None:
        self._marks[token_id] = fv

    def set_position(self, token_id: str, size: float, avg_price: float) -> None:
        self._positions[token_id] = {"size": size, "avg_price": avg_price}

    def _inventory_value(self) -> float:
        total = 0.0
        for tok, pos in self._positions.items():
            if pos["size"] > 0:
                total += pos["size"] * self._marks.get(tok, pos["avg_price"])
        return total

    @property
    def equity(self) -> float:
        return self._net_cash + self._inventory_value()

    @property
    def daily_pnl(self) -> float:
        return self.equity - self._day_start_equity

    def reset_day(self) -> None:
        self._day_start_equity = self.equity

    def note_order_result(self, ok: bool) -> None:
        self._order_attempts += 1
        if not ok:
            self._order_errors += 1

    @property
    def error_rate(self) -> float:
        return self._order_errors / self._order_attempts if self._order_attempts >= 20 else 0.0

    # ── global kill switch ──────────────────────────────────────────────
    def global_halt(self) -> tuple[bool, str]:
        if self._killed:
            return True, "manual_kill"
        if self.daily_pnl <= -self.cfg.daily_loss_kill_usdc:
            return True, f"daily_loss {self.daily_pnl:.2f}"
        if self.error_rate >= self.cfg.max_order_error_rate:
            return True, f"error_rate {self.error_rate:.2f}"
        return False, ""

    def kill(self) -> None:
        self._killed = True

    # ── per-market evaluation ───────────────────────────────────────────
    def evaluate(self, yes_token: str, no_token: str, *, ws_stale: bool = False) -> RiskDecision:
        halted, why = self.global_halt()
        if halted:
            return RiskDecision(True, False, 0.0, why)
        if ws_stale:
            return RiskDecision(True, False, 0.0, "book_stale")

        market_notional = self._market_notional(yes_token, no_token)
        total_exposure = self._total_exposure()

        if market_notional >= self.cfg.max_market_notional_usdc:
            return RiskDecision(False, True, 1.0, "market_cap")
        if total_exposure >= self.cfg.max_total_exposure_usdc:
            return RiskDecision(False, True, 1.0, "total_exposure_cap")

        scale = min(
            _headroom(market_notional, self.cfg.max_market_notional_usdc),
            _headroom(total_exposure, self.cfg.max_total_exposure_usdc),
        )
        return RiskDecision(False, False, scale, "")

    def _market_notional(self, yes_token: str, no_token: str) -> float:
        total = 0.0
        for tok in (yes_token, no_token):
            pos = self._positions.get(tok, {"size": 0.0, "avg_price": 0.5})
            total += pos["size"] * self._marks.get(tok, pos["avg_price"])
        return total

    def _total_exposure(self) -> float:
        total = 0.0
        for tok, pos in self._positions.items():
            if pos["size"] > 0:
                total += pos["size"] * self._marks.get(tok, pos["avg_price"])
        return total
