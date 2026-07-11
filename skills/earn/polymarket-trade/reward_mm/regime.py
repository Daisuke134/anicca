"""Per-market regime decision — near-verbatim port of poly-maker's
src/polymaker/strategy/regime.py (MIT, warproxxx/poly-maker).

Priority order, highest first:
  HALTED       kill switch / stale data / resolved / past halt-before window
  EVENT        active cooloff, or a fresh fair-value jump
  REDUCE_ONLY  inventory at hard cap, or inside the reduce-only end-date window
  TRENDING     persistent one-sided flow or elevated short/long vol
  QUIET        default farming posture (rewards captured here)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Regime(str, Enum):
    QUIET = "QUIET"
    TRENDING = "TRENDING"
    EVENT = "EVENT"
    REDUCE_ONLY = "REDUCE_ONLY"
    HALTED = "HALTED"


@dataclass(frozen=True, slots=True)
class RegimeInputs:
    now: float
    tick: float
    fv: float
    prev_fv: float | None
    vol_ratio: float
    flow_z: float
    inventory_util: float  # |net notional| / q_max, >=0
    hours_to_end: float | None
    sweep_flagged: bool = False
    market_resolved: bool = False
    ws_stale: bool = False
    risk_halt: bool = False
    risk_reduce_only: bool = False


@dataclass(frozen=True, slots=True)
class RegimeParams:
    """The regime-relevant slice of a strategy profile (see profiles.py)."""

    event_jump_ticks: float = 6.0
    event_cooloff_s: float = 30.0
    trend_flow_z: float = 1.8
    trend_vol_ratio: float = 3.0
    reduce_only_hours: float = 24.0
    halt_before_hours: float = 2.0


class RegimeMachine:
    """Stateful regime decider for one market (tracks the EVENT cooloff)."""

    __slots__ = ("_event_until",)

    def __init__(self) -> None:
        self._event_until: float = 0.0

    def decide(self, inp: RegimeInputs, p: RegimeParams) -> Regime:
        # 1. hard halts
        if inp.risk_halt or inp.ws_stale or inp.market_resolved:
            return Regime.HALTED
        if inp.hours_to_end is not None and inp.hours_to_end <= p.halt_before_hours:
            return Regime.HALTED

        # 2. events (sweep / jump / active cooloff)
        jump_ticks = abs(inp.fv - inp.prev_fv) / inp.tick if inp.prev_fv is not None else 0.0
        if inp.sweep_flagged or jump_ticks >= p.event_jump_ticks:
            self._event_until = inp.now + p.event_cooloff_s
            return Regime.EVENT
        if inp.now < self._event_until:
            return Regime.EVENT

        # 3. reduce-only
        if inp.risk_reduce_only or inp.inventory_util >= 1.0:
            return Regime.REDUCE_ONLY
        if inp.hours_to_end is not None and inp.hours_to_end <= p.reduce_only_hours:
            return Regime.REDUCE_ONLY

        # 4. trending
        if abs(inp.flow_z) >= p.trend_flow_z or inp.vol_ratio >= p.trend_vol_ratio:
            return Regime.TRENDING

        # 5. default
        return Regime.QUIET

    @property
    def in_cooloff(self) -> bool:
        return self._event_until > 0.0

    def cooloff_remaining(self, now: float) -> float:
        return max(0.0, self._event_until - now)
