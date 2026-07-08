"""budget_pacer.py — Mahoraga backend/orchestrator/routing/budget_pacer.py::BudgetPacer copy+tweak
(REQ-CEO-014, M2新設). Same online primal-dual dual-ascent math on the Lagrange multiplier `lambda_`
+ the never-starve hard-limit candidate filter. This class is agent/loop-agnostic — it operates on
arbitrary string keys, same as the Mahoraga original (Mahoraga's "agent" == our "loop", no rename of
internal logic needed, only the call-site vocabulary differs).

Two distinct guard rails (same as Mahoraga):
  - Soft (`lambda_`): dual ascent grows the multiplier while the rolling-window average cost is over
    `ceiling`, floored at 0 when under. Fed into REQ-CEO-010's compute_reward() as a cost penalty.
  - Hard (`filter_agents`): any candidate whose cost estimate exceeds `hard_limit` is excluded, but
    the candidate set is NEVER emptied — falls back to the single cheapest candidate.

Persistence: tmp-write + os.replace atomic pattern (same shape as record-earn.mjs's writeCursorAtomic
and Mahoraga's own save()/load()), state file path (~/.anicca-founder/state/ceo-budget-pacer-state.json,
REQ-CEO-014) is passed in by the caller — this module does not hardcode any path."""
from __future__ import annotations

import json
import os
from collections import deque
from dataclasses import dataclass, field

DEFAULT_CEILING = 0.05
DEFAULT_WINDOW = 100
DEFAULT_HARD_LIMIT = 0.50
DEFAULT_ETA = 0.01


@dataclass
class BudgetPacer:
    ceiling: float = DEFAULT_CEILING
    window: int = DEFAULT_WINDOW
    hard_limit: float = DEFAULT_HARD_LIMIT
    eta: float = DEFAULT_ETA
    spent: deque = field(default_factory=lambda: deque(maxlen=DEFAULT_WINDOW))
    lambda_: float = 0.0

    def __post_init__(self) -> None:
        # Re-cap deque maxlen in case `window` was passed explicitly (mirrors Mahoraga).
        if self.spent.maxlen != self.window:
            self.spent = deque(self.spent, maxlen=self.window)

    # ── Dual update ──────────────────────────────────────────────────────
    def update(self, task_cost: float) -> None:
        """Append one observed company-wide weekly spend sample; one step of dual ascent on
        `lambda_` (gradient = rolling avg - ceiling, floored at 0 -- never goes negative)."""
        cost = max(0.0, float(task_cost))
        self.spent.append(cost)
        avg = sum(self.spent) / len(self.spent)
        self.lambda_ = max(0.0, self.lambda_ + self.eta * (avg - self.ceiling))

    @property
    def avg_cost(self) -> float:
        if not self.spent:
            return 0.0
        return sum(self.spent) / len(self.spent)

    # ── Hard-limit filter ────────────────────────────────────────────────
    def filter_agents(self, available: list, task_cost_estimates: dict) -> list:
        """Remove candidates whose per-task cost estimate exceeds `hard_limit`. A candidate missing
        from `task_cost_estimates` is treated as zero-cost and passes. Never empties the candidate
        set -- falls back to the single cheapest candidate if the filter would otherwise starve it."""
        if self.hard_limit <= 0.0:
            kept = [a for a in available if task_cost_estimates.get(a, 0.0) == 0.0]
            if not kept and available:
                cheapest = min(available, key=lambda a: task_cost_estimates.get(a, 0.0))
                return [cheapest]
            return kept
        kept = [a for a in available if task_cost_estimates.get(a, 0.0) <= self.hard_limit]
        if not kept and available:
            cheapest = min(available, key=lambda a: task_cost_estimates.get(a, 0.0))
            return [cheapest]
        return kept

    def to_status_dict(self) -> dict:
        return {
            "ceiling": round(self.ceiling, 4),
            "hard_limit": round(self.hard_limit, 4),
            "window": self.window,
            "eta": self.eta,
            "lambda": round(self.lambda_, 6),
            "avg_cost": round(self.avg_cost, 6),
            "n_observed": len(self.spent),
        }

    # ── Persistence (tmp-write + atomic rename, same pattern as record-earn.mjs) ──
    def save(self, path: str) -> None:
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "ceiling": self.ceiling,
                    "window": self.window,
                    "hard_limit": self.hard_limit,
                    "eta": self.eta,
                    "lambda_": self.lambda_,
                    "spent": list(self.spent),
                },
                f,
            )
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: str) -> "BudgetPacer":
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return cls()
        window = int(data.get("window", DEFAULT_WINDOW))
        spent_list = list(data.get("spent", []))[-window:]
        return cls(
            ceiling=float(data.get("ceiling", DEFAULT_CEILING)),
            window=window,
            hard_limit=float(data.get("hard_limit", DEFAULT_HARD_LIMIT)),
            eta=float(data.get("eta", DEFAULT_ETA)),
            spent=deque(spent_list, maxlen=window),
            lambda_=float(data.get("lambda_", 0.0)),
        )
