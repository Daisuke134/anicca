"""test_earning_health.py — is_fresh_but_barren() pure predicate (earning-health.py).
Mirrors test_cadence.py's dialect: plain print-based checker, no pytest, run directly with python3.

THE BLIND SPOT THIS PROVES CLOSED: Franklin's real earn/sol-trade.trace.jsonl
(2026-07-08T15:10:40Z .. 2026-07-10T12:53:17Z) recorded 67 CONSECUTIVE lines that were all
action=="skip" with the identical reason "identity-mismatch (own=none cli=none); only
Franklin(.blockrun) may run this slot" -- the trace stayed FRESH (a new line every wake) the whole
time, so the existing artifact-AGE staleness check never fired. is_fresh_but_barren() must FLAG that
exact fixture, and must NOT flag a real live-pass (even a long run of legitimate WAIT decisions).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# earning-health.py has a hyphen -> not importable as a normal module name; load by path.
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "earning_health", os.path.join(os.path.dirname(os.path.dirname(__file__)), "earning-health.py")
)
earning_health = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(earning_health)
is_fresh_but_barren = earning_health.is_fresh_but_barren

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


IDENTITY_MISMATCH_REASON = "identity-mismatch (own=none cli=none); only Franklin(.blockrun) may run this slot"


def skip(reason=IDENTITY_MISMATCH_REASON):
    return {"action": "skip", "reason": reason}


def live_pass(note="WAIT — TradingSignal for SOL is neutral"):
    return {"action": "live-pass", "exit": 0, "note": note}


# ---------------------------------------------------------------------------
# THE REGRESSION FIXTURE: Franklin's real 67-consecutive-identity-mismatch-skip run must FLAG.
# ---------------------------------------------------------------------------
franklin_67_skips = [skip() for _ in range(67)]
chk("Franklin fixture: 67 consecutive identical-reason skips (default min_run=20) -> BARREN",
    is_fresh_but_barren(franklin_67_skips, min_run=20), True)
chk("Franklin fixture: same 67 skips with min_run=67 (exact boundary) -> BARREN",
    is_fresh_but_barren(franklin_67_skips, min_run=67), True)

# ---------------------------------------------------------------------------
# THE ANTI-FALSE-POSITIVE FIXTURE: a real live-pass (even the latest one being a legitimate WAIT,
# as Franklin's actual 2026-07-10T14:04:39Z line was) must NEVER be flagged as barren-by-skip.
# ---------------------------------------------------------------------------
skips_then_live_pass = [skip() for _ in range(19)] + [live_pass()]
chk("19 skips then a real live-pass (agent actually ran) -> NOT barren",
    is_fresh_but_barren(skips_then_live_pass, min_run=20), False)

many_legit_waits = [live_pass(f"WAIT — signal neutral, pass {i}") for i in range(30)]
chk("30 consecutive live-pass WAITs (legitimate trading strategy, zero trades) -> NOT barren",
    is_fresh_but_barren(many_legit_waits, min_run=20), False)

# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
chk("fewer entries than min_run (not enough evidence yet) -> NOT barren",
    is_fresh_but_barren([skip() for _ in range(5)], min_run=20), False)

chk("empty trace -> NOT barren",
    is_fresh_but_barren([], min_run=20), False)

mixed_reasons = [skip("identity-mismatch (own=none cli=none); only Franklin(.blockrun) may run this slot")] * 10 \
    + [skip("kill-switch")] * 10
chk("20 skips but with TWO DIFFERENT reasons (rotating cause, not one sustained bug) -> NOT barren",
    is_fresh_but_barren(mixed_reasons, min_run=20), False)

chk("a skip with an empty/missing reason never satisfies the identical-non-empty-reason condition",
    is_fresh_but_barren([{"action": "skip", "reason": ""} for _ in range(20)], min_run=20), False)

chk("older skip run followed by enough live-passes to fill the window -> NOT barren "
    "(only the LAST min_run entries matter, not history further back)",
    is_fresh_but_barren([skip() for _ in range(50)] + [live_pass() for _ in range(20)], min_run=20), False)

print(f"=== test_earning_health: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
