"""test_cooldown_rollback_state_machine.py — RED (Phase 2a, feature claude-p-ceo-loop).
PROP-CEO-014 (B5修正, REQ-CEO-053/054): should_rollback / update_miss_count.
PROP-CEO-014b (B3新設/m4修正/B7/B9修正, REQ-CEO-052/053): should_snapshot / restore_from_rollback.
PROP-CEO-014c (B4新設, REQ-CEO-058): next_cooldown_weeks_remaining — the single function that owns
cooldown_weeks_remaining's next-pass value (fixes the B4 set-then-decrement same-pass competition).

ceo/allocator.py does not exist yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from allocator import (  # noqa: E402  RED: does not exist yet
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


# ---------- PROP-CEO-014: should_rollback ----------
chk("should_rollback: count=1, cooldown=0 -> False (below threshold)", should_rollback(1, 0), False)
chk("should_rollback: count=2, cooldown=0 -> True (2-week threshold met)", should_rollback(2, 0), True)
chk("should_rollback: count=2, cooldown=1 -> False (cooldown blocks re-firing even at threshold)", should_rollback(2, 1), False)

# ---------- PROP-CEO-014: update_miss_count (B5: cooldown means "return unchanged", not "reset to 0") ----------
chk("update_miss_count: prev=0, beats=False, cooldown=1 (in cooldown) -> 0 unchanged", update_miss_count(0, False, 1), 0)
chk("update_miss_count: prev=1, beats=False, cooldown=1 (in cooldown) -> 1 unchanged (NOT forced to 0)", update_miss_count(1, False, 1), 1)
chk("update_miss_count: prev=1, beats=False, cooldown=0 (normal) -> 2 (increments)", update_miss_count(1, False, 0), 2)
chk("update_miss_count: prev=1, beats=True, cooldown=0 (beat resets streak) -> 0", update_miss_count(1, True, 0), 0)

# ---------- PROP-CEO-014b: should_snapshot (freeze during streak/cooldown) ----------
chk("should_snapshot: count=0, cooldown=0 -> True (only healthy state snapshots)", should_snapshot(0, 0), True)
chk("should_snapshot: count=1, cooldown=0 -> False (miss streak in progress, frozen)", should_snapshot(1, 0), False)
chk("should_snapshot: count=0, cooldown=1 -> False (cooldown week, still frozen)", should_snapshot(0, 1), False)

# ---------- PROP-CEO-014b: restore_from_rollback (identity transform, wrapper-shape passthrough) ----------
snapshot = {"clip": {"allocation": {"x": 9}}}
restored = restore_from_rollback(snapshot)
chk("restore_from_rollback: identity passthrough of the {loop: {allocation: ...}} snapshot", restored, snapshot)
chk("restore_from_rollback: does not mutate/merge with anything else (same dict shape back)", set(restored["clip"].keys()), {"allocation"})

# ---------- PROP-CEO-014c: next_cooldown_weeks_remaining (the ONLY function that sets this value) ----------
chk(
    "next_cooldown: rollback just fired, cooldown_in=0 -> ARMS to rollback_cooldown_weeks=1 (NOT decremented this same pass, B4 core)",
    next_cooldown_weeks_remaining(cooldown_weeks_remaining_in=0, rollback_fired_this_pass=True, rollback_cooldown_weeks=1),
    1,
)
chk(
    "next_cooldown: no rollback, already in cooldown (in=1) -> decrements to 0",
    next_cooldown_weeks_remaining(cooldown_weeks_remaining_in=1, rollback_fired_this_pass=False, rollback_cooldown_weeks=1),
    0,
)
chk(
    "next_cooldown: no rollback, not in cooldown (in=0) -> stays 0 (normal operation)",
    next_cooldown_weeks_remaining(cooldown_weeks_remaining_in=0, rollback_fired_this_pass=False, rollback_cooldown_weeks=1),
    0,
)
chk(
    "next_cooldown: rollback fired while already mid-cooldown (unusual combo) -> arm value wins, stays at 1 (defensive, never negative/inconsistent)",
    next_cooldown_weeks_remaining(cooldown_weeks_remaining_in=1, rollback_fired_this_pass=True, rollback_cooldown_weeks=1),
    1,
)

print(f"=== test_cooldown_rollback_state_machine: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
