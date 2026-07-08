"""test_budget_gate.py — RED (Phase 2a, feature claude-p-ceo-loop).
PROP-CEO-005 (REQ-CEO-022/023): filter_budget_compliant_loops (fail-open when no budget config) +
budget_for_loop (agent-os `budget_for_agent`/`filter_budget_compliant_agents` copy+tweak, agent->loop).

ceo/budget.py does not exist yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from budget import budget_for_loop, filter_budget_compliant_loops  # noqa: E402  RED: does not exist yet

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


# ---------- budget_for_loop: fail-open (None) when config missing / entry missing ----------
chk("budget_for_loop(None, 'clip') -> None (no config section at all -> fail-open)", budget_for_loop(None, "clip"), None)
chk("budget_for_loop({}, 'clip') -> None (empty budgets section -> fail-open)", budget_for_loop({}, "clip"), None)

cfg_default_only = {"budgets": {"default": {"soft_warn_usd": 5.0, "hard_stop_usd": 10.0}}}
resolved = budget_for_loop(cfg_default_only, "gig")
chk("budget_for_loop: per_loop entry missing -> falls back to 'default' entry", resolved, {"soft_warn_usd": 5.0, "hard_stop_usd": 10.0})

cfg_per_loop = {"budgets": {"per_loop": {"clip": {"soft_warn_usd": 1.0, "hard_stop_usd": 2.0}}}}
resolved_specific = budget_for_loop(cfg_per_loop, "clip")
chk("budget_for_loop: per_loop entry present -> used directly", resolved_specific, {"soft_warn_usd": 1.0, "hard_stop_usd": 2.0})
chk("budget_for_loop: a DIFFERENT loop with no default and no per_loop entry -> None", budget_for_loop(cfg_per_loop, "video"), None)

# ---------- filter_budget_compliant_loops: fail-open + hard-stop exclusion (candidates for INCREASE only) ----------
candidates = ["clip", "gig", "bounty"]

passed, skipped = filter_budget_compliant_loops(candidates, None, {"clip": 12.0, "gig": 8.0})
chk("filter_budget_compliant_loops: no budget config -> ALL candidates pass unchanged (fail-open)", passed, candidates)
chk("filter_budget_compliant_loops: fail-open -> skipped is empty", skipped, {})

cfg = {"budgets": {"per_loop": {"clip": {"hard_stop_usd": 10.0}}}}
passed2, skipped2 = filter_budget_compliant_loops(candidates, cfg, {"clip": 12.0, "gig": 8.0, "bounty": 0.0})
chk_true("filter_budget_compliant_loops: clip spend $12 > hard_stop $10 -> EXCLUDED from candidates", "clip" not in passed2)
chk_true("filter_budget_compliant_loops: clip appears in the skipped map", "clip" in skipped2)
chk_true("filter_budget_compliant_loops: gig/bounty have no budget entry -> pass (fail-open per-loop)", "gig" in passed2 and "bounty" in passed2)

passed3, skipped3 = filter_budget_compliant_loops(["clip"], cfg, {"clip": 8.0})
chk("filter_budget_compliant_loops: clip spend $8 < hard_stop $10 -> NOT excluded", passed3, ["clip"])
chk("filter_budget_compliant_loops: not excluded -> skipped map empty for clip", skipped3, {})

print(f"=== test_budget_gate: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
