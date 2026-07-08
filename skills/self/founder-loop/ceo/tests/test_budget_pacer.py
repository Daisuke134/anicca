"""test_budget_pacer.py — RED (Phase 2a, feature claude-p-ceo-loop).
Team-lead scope: "BudgetPacerのLagrange dual-ascent（lambda_ 更新）" (REQ-CEO-014, M2新設).
Mahoraga `BudgetPacer` (backend/orchestrator/routing/budget_pacer.py) copy+tweak into
ceo/budget_pacer.py — same dataclass API, in-memory only (no disk save()/load() exercised here,
that's a Tier2 concern; this is the pure dual-ascent math + hard-limit filter, unit-testable with
explicit constructor args bypassing env resolution).

ceo/budget_pacer.py does not exist yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from budget_pacer import BudgetPacer  # noqa: E402  RED: does not exist yet

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


# ---------- dual ascent: lambda_ starts at 0, grows when rolling avg cost exceeds ceiling ----------
bp = BudgetPacer(ceiling=1.0, window=10, hard_limit=5.0, eta=0.1)
chk("BudgetPacer() cold: lambda_ starts at 0.0", bp.lambda_, 0.0)

bp.update(2.0)  # cost 2.0 > ceiling 1.0 -> positive gradient -> lambda_ grows
chk_true("after 1 over-ceiling update, lambda_ > 0 (dual ascent moved)", bp.lambda_ > 0.0)
first_lambda = bp.lambda_

bp.update(2.0)
chk_true("a second over-ceiling update keeps lambda_ non-decreasing while still over ceiling", bp.lambda_ >= first_lambda)

bp_under = BudgetPacer(ceiling=10.0, window=10, hard_limit=50.0, eta=0.1)
bp_under.update(9.9)  # cost 9.9, ceiling 10.0 -- under ceiling but not by much (avg 9.9 < 10.0 -> negative gradient, but max(0,...) floors it)
chk("under-ceiling single update: lambda_ floored at 0.0 (max(0, lambda_ + eta*(avg-ceiling)))", bp_under.lambda_, 0.0)

# ---------- hard-limit filter: never starves the candidate set, falls back to cheapest ----------
kept = bp.filter_agents(["clip", "gig", "bounty"], {"clip": 1.0, "gig": 10.0, "bounty": 3.0})
chk_true("filter_agents: clip (1.0 <= hard_limit 5.0) kept", "clip" in kept)
chk_true("filter_agents: bounty (3.0 <= hard_limit 5.0) kept", "bounty" in kept)
chk_true("filter_agents: gig (10.0 > hard_limit 5.0) excluded", "gig" not in kept)

kept_all_over = bp.filter_agents(["gig"], {"gig": 10.0})
chk("filter_agents: candidate set never emptied -- falls back to cheapest even if it exceeds hard_limit", kept_all_over, ["gig"])

kept_unknown_cost = bp.filter_agents(["clip", "mystery"], {"clip": 1.0})
chk_true("filter_agents: agent missing from cost estimates is treated as zero-cost and passes", "mystery" in kept_unknown_cost)

print(f"=== test_budget_pacer: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
