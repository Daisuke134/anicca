"""test_build_next_registry.py — RED (Phase 2a, feature claude-p-ceo-loop).
PROP-CEO-024 (B7新設/B9修正, REQ-CEO-044): build_next_registry(existing_registry,
budget_snapshot_by_loop, rollback_restore, allocation_decisions) -> dict — the SOLE assembly point
for loop-registry.json, replacing the discarded `registry_updates` accumulator (B9, "道A"). Direct
test of the explicit 4-argument priority order (rollback_restore beats allocation_decisions beats
existing_registry for "allocation"; budget_snapshot_by_loop beats existing_registry for "budget").

ceo/allocator.py does not exist yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from allocator import build_next_registry  # noqa: E402  RED: does not exist yet

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


existing = {"clip": {"fleet": 3, "allocation": {"x": 1}, "budget": {"old": True}}}

# ---------- base case: budget from budget_snapshot, allocation from allocation_decisions, fleet preserved ----------
result = build_next_registry(
    existing_registry=existing,
    budget_snapshot_by_loop={"clip": {"hard_stopped": False}},
    rollback_restore=None,
    allocation_decisions={"clip": {"allocation": {"x": 9}}},
)
chk("build_next_registry: 'fleet' key (untouched by this feature) is preserved from existing_registry", result["clip"]["fleet"], 3)
chk("build_next_registry: 'allocation' comes from allocation_decisions when rollback_restore is None", result["clip"]["allocation"], {"x": 9})
chk("build_next_registry: 'budget' comes from budget_snapshot_by_loop", result["clip"]["budget"], {"hard_stopped": False})

# ---------- priority disproof (B9 core): rollback_restore, when non-None, wins over allocation_decisions ----------
result_rollback = build_next_registry(
    existing_registry=existing,
    budget_snapshot_by_loop={"clip": {"hard_stopped": False}},
    rollback_restore={"clip": {"allocation": {"x": 99}}},
    allocation_decisions={"clip": {"allocation": {"x": 9}}},  # present but must NOT win
)
chk("build_next_registry: non-None rollback_restore wins over allocation_decisions ({x:99}, not {x:9})", result_rollback["clip"]["allocation"], {"x": 99})
chk(
    "build_next_registry: budget_snapshot_by_loop still applies in the SAME single call as the rollback restore (B9 content-assertion: both fields coexist)",
    result_rollback["clip"]["budget"],
    {"hard_stopped": False},
)

# ---------- minimal / empty-everything case: existing_registry passes through unchanged ----------
result_empty = build_next_registry(
    existing_registry=existing,
    budget_snapshot_by_loop={},
    rollback_restore=None,
    allocation_decisions={},
)
chk("build_next_registry: all-empty args -> existing_registry's allocation is preserved", result_empty["clip"]["allocation"], {"x": 1})
chk("build_next_registry: all-empty args -> existing_registry's budget is preserved", result_empty["clip"]["budget"], {"old": True})

print(f"=== test_build_next_registry: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
