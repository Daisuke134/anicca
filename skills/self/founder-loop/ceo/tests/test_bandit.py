"""test_bandit.py — RED (Phase 2a, feature claude-p-ceo-loop).
PROP-CEO-002/PROP-CEO-013b (REQ-CEO-010 compute_reward + B8 call-site contract),
PROP-CEO-003 (REQ-CEO-013 cold_start_state), REQ-CEO-011 (LinUCB select_scores, Mahoraga
`LinUCBRouter.compute_scores`/`_init_agent` copy+tweak — d=2 identity-A cold start makes the UCB
math hand-computable), Thompson update() bookkeeping (Mahoraga `ThompsonSamplingRouter.update`
copy+tweak, deterministic — no np.random sampling exercised here).

ceo/bandit.py does not exist yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from bandit import (  # noqa: E402  RED: does not exist yet
    ThompsonSamplingRouter,
    cold_start_state,
    compute_reward,
    select_scores,
)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from allocator import realized_profit_usd  # noqa: E402  RED: does not exist yet (PROP-CEO-013b wiring)

P = 0
F = 0


def chk(name, got, want):
    global P, F
    if got == want:
        print(f"  ok {name} ({got})")
        P += 1
    else:
        print(f"  FAIL {name} want={want} got={got}")
        F += 1


def chk_true(name, cond):
    chk(name, bool(cond), True)


# ---------- PROP-CEO-002 (REQ-CEO-010): compute_reward zero-division safety + lambda penalty ----------
chk("lambda=0, spend=0, earn=5.0 -> 5.0 (no division at all)", compute_reward(5.0, 0.0, 0.0), 5.0)
chk("lambda=0, spend=2.0, earn=10.0 -> 5.0 (earn/spend)", compute_reward(10.0, 2.0, 0.0), 5.0)
chk("lambda=0, spend=0, earn=0 -> 0 (never 0/0)", compute_reward(0.0, 0.0, 0.0), 0.0)
chk("lambda=0.5, spend=2.0, earn=10.0 -> 4.0 (base 5.0 - 0.5*2.0)", compute_reward(10.0, 2.0, 0.5), 4.0)

# ---------- PROP-CEO-013b (B8): compute_reward call-site contract mirrors PROP-CEO-007's M4 pattern.
# JPY-denominated loop (gig/affiliate fixture): raw ledger amount is 6000 JPY, jpy_usd_rate=150.0.
# realized_profit_usd() converts to 40.0 USD -- THIS converted value, not the raw 6000, must be the
# value that reaches compute_reward's first argument (realized_earn_usdc). INV-CEO-1.
jpy_entries = [{"amount": 0, "currency": "usd"}, {"amount": 6000, "currency": "jpy"}]
fx = {"jpy_usd_rate": 150.0}
converted = realized_profit_usd(jpy_entries, fx)
chk("B8: realized_profit_usd(6000 JPY @150) -> 40.0 USD (the value compute_reward must receive)", converted, 40.0)
reward_from_converted = compute_reward(converted, 0.0, 0.0)
chk("B8: compute_reward(realized_earn_usdc=converted 40.0, spend=0, lambda=0) -> 40.0 (not 6000)", reward_from_converted, 40.0)
chk_true("B8: the raw JPY amount 6000 was NOT what compute_reward saw", reward_from_converted != 6000)

# ---------- PROP-CEO-003 (REQ-CEO-013): cold_start_state, Mahoraga _init_agent same-value cold start
# (identity A, prior*ones(d,1) b) — no persisted state file exists yet for this loop/arm.
cs2 = cold_start_state(2, 0.5)
chk("cold_start_state(d=2, prior=0.5): A is 2x2 identity", cs2["A"], [[1.0, 0.0], [0.0, 1.0]])
chk("cold_start_state(d=2, prior=0.5): b is prior*ones(2,1)", cs2["b"], [[0.5], [0.5]])
cs3 = cold_start_state(3, 0.9)
chk("cold_start_state(d=3, prior=0.9): A is 3x3 identity", cs3["A"], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
chk("cold_start_state(d=3, prior=0.9): b is prior*ones(3,1)", cs3["b"], [[0.9], [0.9], [0.9]])

# ---------- REQ-CEO-011: LinUCB select_scores(context, arms, alpha) — UCB only, no state mutation.
# Both arms cold-started (A=I) so the math is hand-computable: theta=A^-1 b=b (since A=I),
# exploit = context . theta, explore_sq = context . A^-1 . context = ||context||^2 (A=I), explore = alpha*sqrt(explore_sq).
arms = {"clip": cold_start_state(2, 0.5), "gig": cold_start_state(2, 1.0)}
scores = select_scores([1.0, 0.0], arms, alpha=1.0)
chk_true("select_scores returns a dict with both arm keys", set(scores.keys()) == {"clip", "gig"})
chk("select_scores clip: exploit = [1,0].[0.5,0.5] = 0.5", round(scores["clip"]["exploit"], 4), 0.5)
chk("select_scores clip: explore = 1.0*sqrt(1.0) = 1.0 (A=I, context norm 1)", round(scores["clip"]["explore"], 4), 1.0)
chk("select_scores clip: ucb = exploit+explore = 1.5", round(scores["clip"]["ucb"], 4), 1.5)
chk("select_scores gig: exploit = [1,0].[1.0,1.0] = 1.0 (higher prior -> higher exploit)", round(scores["gig"]["exploit"], 4), 1.0)
chk("select_scores gig: ucb = 1.0+1.0 = 2.0 (gig ranks above clip)", round(scores["gig"]["ucb"], 4), 2.0)
chk_true("select_scores: no book-keeping mutation is required to call this twice with the same result",
         select_scores([1.0, 0.0], arms, alpha=1.0)["gig"]["ucb"] == scores["gig"]["ucb"])
chk("select_scores({}) -> {} for empty arms (mirrors Mahoraga compute_scores empty-agents behaviour)", select_scores([1.0, 0.0], {}, alpha=1.0), {})

# ---------- Thompson update() bookkeeping (deterministic half — no np.random.beta sampling here) ----------
th = ThompsonSamplingRouter(success_threshold=0.5)
th.update(None, "clip", 0.9)  # reward > threshold -> alpha += 1
chk("Thompson.update reward>threshold: alpha[clip] = 1.0(prior) + 1.0 = 2.0", th.alpha["clip"], 2.0)
chk("Thompson.update reward>threshold: beta[clip] stays at prior 1.0", th.beta_["clip"], 1.0)
th.update(None, "clip", 0.1)  # reward <= threshold -> beta += 1
chk("Thompson.update reward<=threshold: beta[clip] = 1.0 + 1.0 = 2.0", th.beta_["clip"], 2.0)
chk("Thompson.update reward<=threshold: alpha[clip] unchanged at 2.0", th.alpha["clip"], 2.0)

print(f"=== test_bandit: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
