"""test_weekly_compare.py — RED (Phase 2a, feature claude-p-loop-verification).
PROP-LV-024 / REQ-LV-111 — beats_previous_week(this_week_score, last_week_score) -> bool. Pure,
strict >, tie is NOT a beat (consistent with earn/self-improve's own beats_baseline / EDGE-2 "ties
do not beat baseline" rule, gate_math.py — this new function mirrors that same floor semantics for
the weekly comparison instead of the vs-baseline comparison).

lib/weekly_compare.py does not exist yet -> ImportError -> RED.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib"))
from weekly_compare import beats_previous_week  # RED: does not exist yet

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


chk("this=10, last=5 -> true (beat)", beats_previous_week(10, 5), True)
chk("this=5, last=10 -> false (worse)", beats_previous_week(5, 10), False)
chk("this=5, last=5 -> false (tie is NOT a beat, strict >)", beats_previous_week(5, 5), False)
chk("this=0, last=0 -> false (tie at zero)", beats_previous_week(0, 0), False)
chk("this=-1, last=-5 -> true (less negative beats more negative)", beats_previous_week(-1, -5), True)

print(f"=== test_weekly_compare: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
