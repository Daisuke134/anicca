"""test_rollback_pass_composition.py — RED (Phase 2a, feature claude-p-ceo-loop).
PROP-CEO-021 (B3/B4/B6/B7/B9修正): the Phase 1c adversary's 4-week rollback scenario, replayed as a
PURE-FUNCTION composition (should_snapshot / should_rollback / restore_from_rollback /
update_miss_count / next_cooldown_weeks_remaining / build_next_registry chained by hand in this
test, in-memory dicts standing in for the real state files). This is NOT the Tier3 E2E (that needs
a real main-agent run against real ~/.anicca-founder/state/ files + mail + a fresh-context Opus 4.8
adversary verdict -- PROP-CEO-021's actual Tier-3 requirement, done in Phase 3, not here). This RED
test exists to catch state-machine wiring bugs in the pure layer *before* paying for a real E2E run,
per team-lead's explicit scope ("cooldown/rollback状態機械" + PROP-CEO-021).

Scenario (mirrors REQ-CEO-058's own worked example in the spec, lines 702-726):
  week N-2 (baseline): allocation = A_good, budget v1.
  week N-1: streak healthy (count=0,cooldown=0) -> snapshot ARMS to A_good. Agent decides A_bad1.
            miss#1 (beats=False) -> consecutive_miss_count becomes 1. No rollback (1 < 2).
  week N:   should_snapshot is False (streak in progress) -> ceo-rollback.json stays A_good.
            miss#2 -> consecutive_miss_count reaches 2 -> should_rollback fires.
            Step 8 is skipped ENTIRELY this pass (B6: cooldown_in==0 and not rollback_fired_this_pass
            is False here) -- the agent's hypothetical A_bad3 is never even computed.
            build_next_registry restores A_good (not A_bad1, not A_bad3) AND applies this week's
            budget snapshot in the SAME call (B9 content-assertion core).
  week N+1: cooldown week (cooldown_weeks_remaining_in=1) -> step 8 skipped again, allocation frozen
            at A_good, only budget updates. cooldown decrements to 0 for next week.
  week N+2: cooldown_weeks_remaining_in=0, rollback_fired=False -> step 8 gate is open again
            (normal operation resumes).

ceo/allocator.py does not exist yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from allocator import (  # noqa: E402  RED: does not exist yet
    build_next_registry,
    next_cooldown_weeks_remaining,
    restore_from_rollback,
    should_rollback,
    should_snapshot,
    update_miss_count,
)

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


A_GOOD = {"freq": 1.0}
A_BAD1 = {"freq": 0.5}

# ---------- week N-2 baseline ----------
registry = {"clip": {"allocation": dict(A_GOOD), "budget": {"v": 1}}}
miss_streak = {"consecutive_miss_count": 0, "cooldown_weeks_remaining": 0}
rollback_snapshot = None  # ceo-rollback.json not yet written

# ---------- week N-1: healthy streak -> snapshot arms, agent decides A_bad1, miss #1 ----------
count_in, cooldown_in = miss_streak["consecutive_miss_count"], miss_streak["cooldown_weeks_remaining"]
if should_snapshot(count_in, cooldown_in):
    rollback_snapshot = {"clip": {"allocation": dict(registry["clip"]["allocation"])}}  # captures A_GOOD, before this week's write
chk_true("week N-1: should_snapshot(0,0) fired -> ceo-rollback.json captured A_good", rollback_snapshot == {"clip": {"allocation": A_GOOD}})

allocation_decisions_n1 = {"clip": {"allocation": dict(A_BAD1)}}  # agent's (bad) decision this week
budget_snapshot_n1 = {"clip": {"v": 2}}
registry = build_next_registry(registry, budget_snapshot_n1, None, allocation_decisions_n1)
chk("week N-1: registry now holds A_bad1 (the agent's decision was written -- rollback hadn't fired yet)", registry["clip"]["allocation"], A_BAD1)

count_new = update_miss_count(count_in, beats_this_week=False, cooldown_weeks_remaining=cooldown_in)
rollback_fired_n1 = should_rollback(count_new, cooldown_in)
cooldown_next_n1 = next_cooldown_weeks_remaining(cooldown_in, rollback_fired_n1, rollback_cooldown_weeks=1)
chk("week N-1: consecutive_miss_count becomes 1 (miss #1)", count_new, 1)
chk("week N-1: should_rollback is False yet (1 < threshold 2)", rollback_fired_n1, False)
miss_streak = {"consecutive_miss_count": count_new, "cooldown_weeks_remaining": cooldown_next_n1}

# ---------- week N: streak in progress -> snapshot frozen, miss #2 -> rollback fires, step 8 skipped ----------
count_in, cooldown_in = miss_streak["consecutive_miss_count"], miss_streak["cooldown_weeks_remaining"]
if should_snapshot(count_in, cooldown_in):
    rollback_snapshot = {"clip": {"allocation": dict(registry["clip"]["allocation"])}}  # would capture A_bad1 -- must NOT happen
chk("week N: should_snapshot(1,0) is False -- ceo-rollback.json is NOT overwritten with A_bad1", rollback_snapshot, {"clip": {"allocation": A_GOOD}})

count_new_n = update_miss_count(count_in, beats_this_week=False, cooldown_weeks_remaining=cooldown_in)
chk("week N: consecutive_miss_count becomes 2 (miss #2)", count_new_n, 2)
rollback_fired_n = should_rollback(count_new_n, cooldown_in)
chk("week N: should_rollback(2, 0) fires True", rollback_fired_n, True)

rollback_restore_n = restore_from_rollback(rollback_snapshot) if rollback_fired_n else None
chk("week N: rollback_restore is the frozen A_good snapshot (not A_bad1, not a hypothetical A_bad3)", rollback_restore_n, {"clip": {"allocation": A_GOOD}})

# B6: step 8's formal gate (cooldown_in==0 and not rollback_fired_this_pass) is False this pass ->
# allocation_decisions MUST be empty -- the agent's hypothetical this-week decision is never computed.
step8_gate_open_n = (cooldown_in == 0) and (not rollback_fired_n)
chk("week N: step 8 gate (cooldown_in==0 and not rollback_fired_this_pass) is False -- SKIPPED", step8_gate_open_n, False)
allocation_decisions_n = {} if not step8_gate_open_n else {"clip": {"allocation": {"freq": 0.3}}}
chk("week N: allocation_decisions is empty dict (agent decision never computed this pass)", allocation_decisions_n, {})

budget_snapshot_n = {"clip": {"v": 3}}  # step 3-c ALWAYS runs, rollback pass or not
registry = build_next_registry(registry, budget_snapshot_n, rollback_restore_n, allocation_decisions_n)
chk("week N (B9 core): registry allocation restored to A_good (neither A_bad1 nor a hypothetical A_bad3)", registry["clip"]["allocation"], A_GOOD)
chk("week N (B9 content-assertion): registry budget is ALSO this week's fresh snapshot, in the SAME call", registry["clip"]["budget"], {"v": 3})

cooldown_next_n = next_cooldown_weeks_remaining(cooldown_in, rollback_fired_n, rollback_cooldown_weeks=1)
chk("week N: cooldown ARMS to 1 (not decremented within this same firing pass -- B4 core)", cooldown_next_n, 1)
miss_count_persisted_n = 0 if rollback_fired_n else count_new_n  # REQ-CEO-058 step 10: rollback resets to 0
chk("week N: consecutive_miss_count persists as 0 (rollback resets the streak)", miss_count_persisted_n, 0)
miss_streak = {"consecutive_miss_count": miss_count_persisted_n, "cooldown_weeks_remaining": cooldown_next_n}

# ---------- week N+1: cooldown week -> step 8 skipped again, allocation frozen, budget still updates ----------
count_in, cooldown_in = miss_streak["consecutive_miss_count"], miss_streak["cooldown_weeks_remaining"]
chk("week N+1: START cooldown_weeks_remaining_in is 1 (not silently re-zeroed)", cooldown_in, 1)
count_new_np1 = update_miss_count(count_in, beats_this_week=False, cooldown_weeks_remaining=cooldown_in)
chk("week N+1: update_miss_count frozen during cooldown (stays 0)", count_new_np1, 0)
rollback_fired_np1 = should_rollback(count_new_np1, cooldown_in)
chk("week N+1: should_rollback does not re-fire during cooldown", rollback_fired_np1, False)
step8_gate_open_np1 = (cooldown_in == 0) and (not rollback_fired_np1)
chk("week N+1: step 8 gate is False (cooldown_in=1 != 0) -- allocation stays frozen", step8_gate_open_np1, False)
budget_snapshot_np1 = {"clip": {"v": 4}}
registry = build_next_registry(registry, budget_snapshot_np1, None, {})
chk("week N+1: allocation unchanged from last pass (still A_good, cooldown freezes decisions)", registry["clip"]["allocation"], A_GOOD)
chk("week N+1: budget still updates during cooldown (observation/reporting never stops)", registry["clip"]["budget"], {"v": 4})
cooldown_next_np1 = next_cooldown_weeks_remaining(cooldown_in, rollback_fired_np1, rollback_cooldown_weeks=1)
chk("week N+1: cooldown decrements from 1 to 0 (only NOW, one pass after the arm)", cooldown_next_np1, 0)
miss_streak = {"consecutive_miss_count": count_new_np1, "cooldown_weeks_remaining": cooldown_next_np1}

# ---------- week N+2: normal operation resumes ----------
count_in, cooldown_in = miss_streak["consecutive_miss_count"], miss_streak["cooldown_weeks_remaining"]
rollback_fired_np2 = should_rollback(count_in, cooldown_in)
step8_gate_open_np2 = (cooldown_in == 0) and (not rollback_fired_np2)
chk("week N+2: cooldown has fully cleared (0) and no rollback pending -- step 8 gate reopens", step8_gate_open_np2, True)

print(f"=== test_rollback_pass_composition: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
