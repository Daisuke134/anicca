"""test_registry_bootstrap_and_ranges.py — RED (Phase 2a, feature claude-p-ceo-loop).
PROP-CEO-011 (REQ-CEO-041): bootstrap_registry_if_missing — fail-safe {} when loop-registry.json
doesn't exist yet (task #13's spawner hasn't written it, this feature may be its first writer).
PROP-CEO-012 (REQ-CEO-042): validate_allocation_ranges — inclusive-bound range gate.

ceo/allocator.py does not exist yet -> ImportError -> RED.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from allocator import bootstrap_registry_if_missing, validate_allocation_ranges  # noqa: E402  RED: does not exist yet

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


# ---------- PROP-CEO-011: bootstrap_registry_if_missing ----------
tmpdir = tempfile.mkdtemp()
missing_path = os.path.join(tmpdir, "loop-registry.json")  # deliberately never created
try:
    result = bootstrap_registry_if_missing(missing_path)
    chk("bootstrap_registry_if_missing: missing file -> {} (does not raise)", result, {})
except Exception as e:  # noqa: BLE001
    chk(f"bootstrap_registry_if_missing: missing file must not raise (raised {type(e).__name__})", False, True)

existing_path = os.path.join(tmpdir, "loop-registry-existing.json")
with open(existing_path, "w") as f:
    f.write('{"clip": {"allocation": {"x": 1}}}')
result_existing = bootstrap_registry_if_missing(existing_path)
chk("bootstrap_registry_if_missing: existing file -> parsed content returned as-is", result_existing, {"clip": {"allocation": {"x": 1}}})

# ---------- PROP-CEO-012: validate_allocation_ranges ----------
ranges_cfg = {"pass_frequency_multiplier": {"min": 0.1, "max": 10}}
chk(
    "validate_allocation_ranges: pass_frequency_multiplier=0.1 (lower bound, inclusive) -> True",
    validate_allocation_ranges({"pass_frequency_multiplier": 0.1}, ranges_cfg),
    True,
)
chk(
    "validate_allocation_ranges: pass_frequency_multiplier=10 (upper bound, inclusive) -> True",
    validate_allocation_ranges({"pass_frequency_multiplier": 10}, ranges_cfg),
    True,
)
chk(
    "validate_allocation_ranges: pass_frequency_multiplier=0.05 (below lower bound) -> False",
    validate_allocation_ranges({"pass_frequency_multiplier": 0.05}, ranges_cfg),
    False,
)
chk(
    "validate_allocation_ranges: pass_frequency_multiplier=15 (above upper bound) -> False (the 'frequency multiplier 20x' runaway case)",
    validate_allocation_ranges({"pass_frequency_multiplier": 15}, ranges_cfg),
    False,
)

print(f"=== test_registry_bootstrap_and_ranges: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
