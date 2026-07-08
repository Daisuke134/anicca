"""bandit.py — Mahoraga backend/orchestrator/routing/strategies/{linucb,thompson}.py copy+tweak
(REQ-CEO-010/011/013). LinUCB is expressed as module-level PURE functions (`cold_start_state`,
`select_scores`) operating on plain JSON-serialisable dict state (`{"A": [[...]], "b": [[...]]}`)
rather than a stateful class wrapping numpy arrays -- this matches verification-architecture.md's
purity-boundary split (Tier1 pure function vs Tier2 persistence) and keeps the persisted
`ceo-bandit-state.json` shape trivially JSON-round-trippable without a custom encoder.

Thompson sampling keeps Mahoraga's original stateful-class shape (`ThompsonSamplingRouter`) because
its `update()` bookkeeping (`alpha`/`beta_` dicts) IS the state, same as Mahoraga's own router --
only `select_agent`'s `np.random.beta` sampling is left untested here per team-lead's scope note
("Thompson update() bookkeeping ... deterministic — no np.random sampling exercised here")."""
from __future__ import annotations

import json
import os

import numpy as np


# ---------- REQ-CEO-013: cold-start (Mahoraga LinUCBRouter._init_agent, first-arm branch) ----------
def cold_start_state(d: int, prior: float) -> dict:
    """Identity A (d x d), b = prior * ones(d, 1). Returned as plain nested lists (JSON-safe)."""
    identity = [[1.0 if i == j else 0.0 for j in range(d)] for i in range(d)]
    b = [[float(prior)] for _ in range(d)]
    return {"A": identity, "b": b}


# ---------- REQ-CEO-011: select_scores (Mahoraga LinUCBRouter.compute_scores copy+tweak) ----------
def select_scores(context, arms: dict, alpha: float = 1.0) -> dict:
    """UCB score per arm: theta = A^-1 b, exploit = context.theta, explore = alpha*sqrt(context.A^-1.context).
    Pure -- no state mutation, no book-keeping (`t` counter) side effect, unlike Mahoraga's
    `select_agent` which also picks a winner and mutates `self.t`. Agent (not this function) decides
    what to do with the scores (REQ-CEO-012 -- no automatic argmax-and-write here)."""
    if not arms:
        return {}
    x = np.array(context, dtype=float).reshape(-1, 1)
    scores = {}
    for name, state in arms.items():
        A = np.array(state["A"], dtype=float)
        b = np.array(state["b"], dtype=float).reshape(-1, 1)
        theta = np.linalg.solve(A, b)
        exploit = float((x.T @ theta).item())
        explore_sq = float((x.T @ np.linalg.solve(A, x)).item())
        explore_sq = max(0.0, explore_sq)
        explore = float(alpha) * float(np.sqrt(explore_sq))
        scores[name] = {"exploit": exploit, "explore": explore, "ucb": exploit + explore}
    return scores


def update_arm(arms: dict, loop: str, context, reward: float, d: int, prior: float) -> dict:
    """Mahoraga LinUCBRouter.update copy+tweak, expressed as an immutable-return pure update over
    the plain-dict arms state (CLAUDE.md immutability rule -- returns a NEW arms dict, does not
    mutate the input). Cold-starts the arm first if unseen (mirrors Mahoraga's `_init_agent`)."""
    next_arms = dict(arms)
    state = next_arms.get(loop) or cold_start_state(d, prior)
    A = np.array(state["A"], dtype=float)
    b = np.array(state["b"], dtype=float).reshape(-1, 1)
    x = np.array(context, dtype=float).reshape(-1, 1)
    A = A + (x @ x.T)
    b = b + reward * x
    next_arms[loop] = {"A": A.tolist(), "b": b.tolist()}
    return next_arms


# ---------- REQ-CEO-011: persistence (tmp-write + atomic rename, same pattern as record-earn.mjs) ----------
def save_state(path: str, arms: dict) -> None:
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(arms, f)
    os.replace(tmp, path)


def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# ---------- REQ-CEO-010 (M2/B8修正): compute_reward -- zero-division-safe + Lagrange lambda penalty ----------
def compute_reward(realized_earn_usdc: float, weekly_spend_usd: float, lambda_: float) -> float:
    """`realized_earn_usdc` MUST already be the output of allocator.realized_profit_usd() at the
    call site (INV-CEO-1) -- this function itself does no currency conversion, it only computes the
    reward scalar. base = earn/spend when spend>0 else earn itself (never divides by zero);
    reward = base - lambda_ * weekly_spend_usd (Mahoraga BudgetPacer's dual variable applied as a
    soft cost penalty, REQ-CEO-014)."""
    base = (realized_earn_usdc / weekly_spend_usd) if weekly_spend_usd > 0 else realized_earn_usdc
    return base - lambda_ * weekly_spend_usd


# ---------- Thompson sampling (Mahoraga ThompsonSamplingRouter copy+tweak, stateful bookkeeping) ----------
class ThompsonSamplingRouter:
    def __init__(self, success_threshold: float = 0.5):
        self.threshold = success_threshold
        self.alpha: dict = {}
        self.beta_: dict = {}

    def select_agent(self, available_agents: list) -> str:
        if not available_agents:
            raise ValueError("available_agents must not be empty")
        samples = {
            a: float(np.random.beta(self.alpha.get(a, 1.0), self.beta_.get(a, 1.0)))
            for a in available_agents
        }
        return max(available_agents, key=lambda a: samples[a])

    def update(self, context, agent: str, reward: float) -> None:
        if agent not in self.alpha:
            self.alpha[agent] = 1.0
            self.beta_[agent] = 1.0
        if reward > self.threshold:
            self.alpha[agent] += 1.0
        else:
            self.beta_[agent] += 1.0

    def save_state(self, path: str) -> None:
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"threshold": self.threshold, "alpha": self.alpha, "beta": self.beta_}, f)
        os.replace(tmp, path)

    def load_state(self, path: str) -> None:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
        self.threshold = state["threshold"]
        self.alpha = state["alpha"]
        self.beta_ = state["beta"]
