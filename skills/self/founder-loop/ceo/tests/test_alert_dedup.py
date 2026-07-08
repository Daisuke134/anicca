"""test_alert_dedup.py — RED (Phase 2a, feature claude-p-ceo-loop).
PROP-CEO-006 (REQ-CEO-024): alert_key/should_fire_alert, agent-os `check_budget_alerts` dedup-key
pattern copy+tweak — fires at most once per (month_key, loop, threshold_name).

ceo/budget.py does not exist yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from budget import alert_key, should_fire_alert  # noqa: E402  RED: does not exist yet

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


k1 = alert_key("2026-06", "clip", "hard_stop")
k1_again = alert_key("2026-06", "clip", "hard_stop")
chk("alert_key is deterministic for the same (month,loop,threshold)", k1, k1_again)

k2 = alert_key("2026-06", "clip", "soft_warn")
chk_true("alert_key: a different threshold_name produces a DIFFERENT key", k1 != k2)

k3 = alert_key("2026-07", "clip", "hard_stop")
chk_true("alert_key: a different month_key produces a DIFFERENT key", k1 != k3)

fired = set()
chk_true("should_fire_alert: key not yet fired -> True (first fire allowed)", should_fire_alert(k1, fired))
fired.add(k1)
chk("should_fire_alert: same key fired once already -> False (dedup, at most once)", should_fire_alert(k1, fired), False)
chk_true("should_fire_alert: a DIFFERENT (month,loop,threshold) key still fires independently", should_fire_alert(k2, fired))

print(f"=== test_alert_dedup: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
