"""test_guardrails.py — RED (Phase 2a, feature claude-p-loop-verification).
PROP-LV-028/029/030 / REQ-LV-130/132-135 — Loop Scaling (fleet increase) guardrail pure functions.
Placed under skills/self/loop-scale/ (a NEW namespace, deliberately separate from the existing
skills/self/spawn/lib/ citizen-registry spawn system, which spawns whole new Anicca-colony citizens
— a different concern from scaling an EXISTING earn loop's own account fleet).

  scale_eligible(streak, weekly_score, weekly_score_threshold, disk_free_gb) -> bool   (REQ-LV-130)
  cooldown_ok(last_spawn_ts, now_ts, min_interval_days) -> bool                        (REQ-LV-133)
  fleet_at_capacity(current_count, max_count) -> bool                                  (REQ-LV-134)
  is_ban_suspected(consecutive_failures, threshold) -> bool                            (REQ-LV-135)

guardrails.py does not exist yet -> ImportError -> RED.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from guardrails import scale_eligible, cooldown_ok, fleet_at_capacity, is_ban_suspected  # RED

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


# --- PROP-LV-028: scale_eligible — 3-condition AND, strict > on score threshold ---
chk("scale_eligible: streak=7, score>threshold, disk=5 -> true (all 3 conditions met)",
    scale_eligible(streak=7, weekly_score=10, weekly_score_threshold=5, disk_free_gb=5), True)
chk("scale_eligible: streak=6 (1 short of 7) -> false",
    scale_eligible(streak=6, weekly_score=10, weekly_score_threshold=5, disk_free_gb=5), False)
chk("scale_eligible: disk=4.9 (below 5) -> false",
    scale_eligible(streak=7, weekly_score=10, weekly_score_threshold=5, disk_free_gb=4.9), False)
chk("scale_eligible: score==threshold exactly (tie, not '>') -> false",
    scale_eligible(streak=7, weekly_score=5, weekly_score_threshold=5, disk_free_gb=5), False)
chk("scale_eligible: streak=7, score>threshold, disk=5.0 exactly (boundary, >=5 passes) -> true",
    scale_eligible(streak=7, weekly_score=100, weekly_score_threshold=1, disk_free_gb=5.0), True)

# --- PROP-LV-029: cooldown_ok ---
DAY = 86400
chk("cooldown_ok: last spawn 10 days ago, min_interval=7 -> true (past cooldown)",
    cooldown_ok(last_spawn_ts=1_000_000, now_ts=1_000_000 + 10 * DAY, min_interval_days=7), True)
chk("cooldown_ok: last spawn 3 days ago, min_interval=7 -> false (still cooling down)",
    cooldown_ok(last_spawn_ts=1_000_000, now_ts=1_000_000 + 3 * DAY, min_interval_days=7), False)
chk("cooldown_ok: no prior spawn (None) -> true (never spawned, no cooldown to respect)",
    cooldown_ok(last_spawn_ts=None, now_ts=1_000_000, min_interval_days=7), True)

# --- PROP-LV-029: fleet_at_capacity ---
chk("fleet_at_capacity: current==max -> true (at capacity)",
    fleet_at_capacity(current_count=5, max_count=5), True)
chk("fleet_at_capacity: current<max -> false (room to grow)",
    fleet_at_capacity(current_count=4, max_count=5), False)
chk("fleet_at_capacity: current>max (defensive, should not happen) -> true",
    fleet_at_capacity(current_count=6, max_count=5), True)

# --- PROP-LV-030: is_ban_suspected ---
chk("is_ban_suspected: consecutive_failures < threshold -> false",
    is_ban_suspected(consecutive_failures=2, threshold=3), False)
chk("is_ban_suspected: consecutive_failures == threshold -> true",
    is_ban_suspected(consecutive_failures=3, threshold=3), True)
chk("is_ban_suspected: consecutive_failures > threshold -> true",
    is_ban_suspected(consecutive_failures=5, threshold=3), True)

print(f"=== test_guardrails: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
