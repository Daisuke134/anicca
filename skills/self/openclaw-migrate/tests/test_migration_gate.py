"""test_migration_gate.py — RED (Phase 2a, feature claude-p-loop-verification).
PROP-LV-039 / REQ-LV-141 — channel_migration_eligible(has_verification_tool) -> bool. v2.2's core
constraint: "そのチャネルのoutputを機械検証できるツールがある"ことが移行の絶対的前提条件. Near-identity
but explicit — the judgment (does this specific channel actually have a verification tool) stays
with the agent; this function only codifies the resulting record's meaning so no channel can be
migrated "by default" without that judgment being made and recorded.

migration_gate.py does not exist yet -> ImportError -> RED.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from migration_gate import channel_migration_eligible  # RED: does not exist yet

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


chk("has_verification_tool=True -> eligible (included in Wave 1 migration)",
    channel_migration_eligible(True), True)
chk("has_verification_tool=False -> NOT eligible (excluded, no unconditional migration)",
    channel_migration_eligible(False), False)

# defensive: this MUST be a real bool check, not a truthy/falsy string trap ("False" the string is
# truthy in Python — a naive `if has_verification_tool:` implementation would wrongly pass this).
chk("has_verification_tool=None -> NOT eligible (missing/undetermined must not default to eligible)",
    channel_migration_eligible(None), False)

print(f"=== test_migration_gate: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
