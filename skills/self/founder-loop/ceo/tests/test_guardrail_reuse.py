"""test_guardrail_reuse.py — RED (Phase 2a, feature claude-p-ceo-loop).
REQ-CEO-031: fleet-size-increase gating MUST call the EXISTING
__REPO_ROOT__/skills/self/loop-scale/guardrails.py::scale_eligible/cooldown_ok/fleet_at_capacity
functions (already implemented+tested for task #13-adjacent work) rather than re-implementing the
3-condition AND. This is a source-level reuse check (Tier2, grep-style) -- not a re-test of
guardrails.py's own logic (that's already covered by test-healthcheck-lib.sh's siblings; this
feature must not duplicate it, per '車輪の再発明禁止').

ceo/allocator.py does not exist yet -> the source-import check itself fails (FileNotFoundError) ->
RED, for the correct reason (nothing has been implemented yet).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CEO_DIR = os.path.dirname(HERE)
ALLOCATOR_PATH = os.path.join(CEO_DIR, "allocator.py")

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


try:
    with open(ALLOCATOR_PATH) as f:
        src = f.read()
except FileNotFoundError:
    print(f"  FAIL ceo/allocator.py does not exist yet at {ALLOCATOR_PATH} -- guardrail reuse cannot be verified")
    F += 1
    src = None

if src is not None:
    chk_true(
        "ceo/allocator.py imports the existing loop-scale/guardrails module (does not re-implement scale_eligible/cooldown_ok/fleet_at_capacity)",
        "guardrails" in src and ("scale_eligible" in src) and ("cooldown_ok" in src) and ("fleet_at_capacity" in src),
    )
    # The AND-of-3-conditions itself must not be re-derived with hardcoded literals like
    # "streak >= 7" (guardrails.scale_eligible's own literal) living a second time in allocator.py.
    chk_true(
        "ceo/allocator.py does not re-hardcode guardrails.py's own streak>=7 threshold literal",
        "streak >= 7" not in src and "streak>=7" not in src,
    )

print(f"=== test_guardrail_reuse: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
