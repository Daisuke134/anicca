"""adversarial_boundary_probe.py — Phase 5 (formal hardening) adversarial boundary probe for
claude-p-ceo-loop. Companion to the Phase 2/3 happy-path test suite under
~/anicca/.worktrees/ceo-loop/skills/self/founder-loop/ceo/tests/ (which the verifier re-ran
unmodified and confirmed still green, see verification-report.md). This script targets the class of
defect that Phase 5's brief explicitly calls out: malformed ledger/JSON rows (non-dict lines,
missing fields, unknown currencies, negative/huge values) that the happy-path suite does not exercise
-- the same defect class ("crash on a non-dict row") that a prior feature's hardening sweep missed.

Every assertion below actually EXECUTES the real ceo/ module functions from the ceo-loop worktree
(no mocking of the functions under test). Where a crash is the correct fail-closed behaviour (an
uncaught exception that would abort a WEEKLY pass) this is recorded as a FINDING, not silently
swallowed -- the pass/fail counters below track "the probe ran and recorded a verdict", not "no
exceptions occurred".
"""
from __future__ import annotations

import json
import os
import sys
import traceback

CEO_DIR = os.path.expanduser("~/anicca/.worktrees/ceo-loop/skills/self/founder-loop/ceo")
sys.path.insert(0, CEO_DIR)

import allocator  # noqa: E402
import bandit  # noqa: E402
import budget  # noqa: E402

P = 0
F = 0
FINDINGS = []


def chk(name, got, want):
    global P, F
    if got == want:
        print(f"  ok {name} ({got!r})")
        P += 1
    else:
        print(f"  FAIL {name} want={want!r} got={got!r}")
        F += 1


def chk_true(name, cond):
    chk(name, bool(cond), True)


def expect_raises(name, exc_types, fn, *args, **kwargs):
    """Records whether calling fn(*args) raises one of exc_types. Either outcome can be the
    'correct' fail-closed answer depending on the call site's own exception handling (see per-case
    FINDING notes below) -- this harness records the actual behaviour, it does not presuppose it."""
    global P, F
    try:
        result = fn(*args, **kwargs)
        print(f"  OBSERVED {name}: NO EXCEPTION, returned {result!r}")
        return ("no-exception", result)
    except exc_types as e:
        print(f"  OBSERVED {name}: raised {type(e).__name__}: {e}")
        return (type(e).__name__, str(e))
    except Exception as e:  # noqa: BLE001 -- intentionally broad, we want to see ANY crash type
        print(f"  OBSERVED {name}: raised UNEXPECTED {type(e).__name__}: {e}")
        return (type(e).__name__, str(e))


def finding(severity, text):
    FINDINGS.append((severity, text))
    print(f"  *** {severity}: {text}")


print("=== SECTION 1: sum_earn_by_currency — malformed ledger rows (non-dict lines) ===")
# A ceo-cost-events.jsonl / <loop>-earn-ledger.jsonl line that round-trips through json.loads() as a
# non-dict JSON value (a bare string/number/list/null) is a realistic malformed-input scenario --
# budget.load_cost_events() (ceo/budget.py) parses each jsonl line with json.loads() and appends
# WHATEVER json.loads() returns, with NO isinstance(dict) check before appending to `rows`.
rows_str_line = [{"earn_usdc": 5.0}, "not-a-dict-line", {"earn_usdc": 3.0}]
outcome = expect_raises(
    "sum_earn_by_currency([valid, 'not-a-dict-line', valid])",
    Exception, allocator.sum_earn_by_currency, rows_str_line,
)
if outcome[0] != "no-exception":
    finding(
        "BLOCKING",
        "allocator.sum_earn_by_currency() crashes (AttributeError: 'str' object has no attribute "
        "'get') on a non-dict JSONL row. run_pass.py builds `rows` via budget.load_cost_events() "
        "which parses each ceo-cost-events.jsonl/<loop>-earn-ledger.jsonl line with json.loads() and "
        "appends the result UNCONDITIONALLY (no isinstance(dict) filter) -- a single malformed line "
        "(e.g. a bare JSON string/number/list written by a bug elsewhere, or hand-edited state) is "
        "enough to abort the entire WEEKLY pass with an uncaught exception, since run_pass.py wraps "
        "NONE of its per-loop loop body in try/except. This is the exact defect class the Phase 5 "
        "brief calls out (mirrors the prior 'non-dict row crash' gig-hardening miss).",
    )

rows_int_line = [{"earn_usdc": 5.0}, 42]
expect_raises(
    "sum_earn_by_currency([valid, 42 (int line)])", Exception, allocator.sum_earn_by_currency, rows_int_line,
)

rows_null_line = [{"earn_usdc": 5.0}, None]
expect_raises(
    "sum_earn_by_currency([valid, None (null line)])", Exception, allocator.sum_earn_by_currency, rows_null_line,
)

rows_list_line = [{"earn_usdc": 5.0}, [1, 2, 3]]
expect_raises(
    "sum_earn_by_currency([valid, [1,2,3] (list line)])", Exception, allocator.sum_earn_by_currency, rows_list_line,
)

# Confirm budget.load_cost_events() really does let non-dict lines through unfiltered (the root
# cause, not just a hypothetical) -- write a real jsonl file with a malformed line and load it.
import tempfile  # noqa: E402

with tempfile.TemporaryDirectory() as td:
    p = os.path.join(td, "malformed-ledger.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        f.write('{"earn_usdc": 5.0}\n')
        f.write('"just-a-string"\n')  # valid JSON, not a dict
        f.write("42\n")  # valid JSON, not a dict
        f.write("not even valid json {{{\n")  # invalid JSON -> silently skipped (json.JSONDecodeError caught)
        f.write('{"earn_usdc": 3.0}\n')
    loaded = budget.load_cost_events(p)
    chk_true(
        "budget.load_cost_events(): invalid-JSON line IS silently skipped (json.JSONDecodeError caught)",
        len(loaded) == 4,  # 4 valid-JSON lines survive: dict, str, int, dict (the malformed-JSON line is dropped)
    )
    chk_true(
        "budget.load_cost_events(): a syntactically-valid-JSON-but-non-dict line (bare string/int) "
        "IS NOT filtered out -- it passes straight through into `rows`",
        any(not isinstance(r, dict) for r in loaded),
    )
    outcome2 = expect_raises(
        "allocator.sum_earn_by_currency(budget.load_cost_events(<file with a bare-string JSON line>))",
        Exception, allocator.sum_earn_by_currency, loaded,
    )
    if outcome2[0] != "no-exception":
        finding(
            "BLOCKING",
            "End-to-end repro (real file -> budget.load_cost_events() -> allocator.sum_earn_by_currency()): "
            "confirmed the root cause is real, not just a synthetic in-memory list -- "
            "budget.load_cost_events() only guards against *invalid JSON* (json.JSONDecodeError), it does "
            "NOT guard against *valid JSON that is not a dict*. Any writer bug (or hand-edited state file) "
            "that appends a bare JSON scalar/array line will abort the CEO WEEKLY pass the next time that "
            "ledger is read via sum_earn_by_currency(), monthly_spend_by_loop(), or weekly_spend_by_loop().",
        )

print()
print("=== SECTION 2: monthly_spend_by_loop / weekly_spend_by_loop — same non-dict-row exposure ===")
cost_rows_bad = [
    {"month_key": "2026-07", "loop": "clip", "usd_estimate": 1.0},
    "not-a-dict",
]
expect_raises(
    "budget.monthly_spend_by_loop([valid, 'not-a-dict'], '2026-07')",
    Exception, budget.monthly_spend_by_loop, cost_rows_bad, "2026-07",
)
expect_raises(
    "budget.weekly_spend_by_loop([valid, 'not-a-dict'], '2026-07-06')",
    Exception, budget.weekly_spend_by_loop, cost_rows_bad, "2026-07-06",
)
finding(
    "BLOCKING",
    "budget.monthly_spend_by_loop() and budget.weekly_spend_by_loop() both call row.get(...) with no "
    "isinstance(dict) guard -- same root-cause class as Section 1, reachable via ceo-cost-events.jsonl "
    "(the file 6 external loop CLIs append to via record-cost-event.sh) rather than a per-loop earn "
    "ledger. A malformed line in ceo-cost-events.jsonl aborts budget aggregation for ALL loops in the "
    "same WEEKLY pass, not just the loop that wrote the bad line.",
)

print()
print("=== SECTION 3: realized_profit_usd / convert_to_usd — unknown currency, empty fx_config ===")
outcome3 = expect_raises(
    "convert_to_usd(100, 'eur', {'jpy_usd_rate': 150.0})  (unknown currency)",
    Exception, allocator.convert_to_usd, 100, "eur", {"jpy_usd_rate": 150.0},
)
chk_true(
    "convert_to_usd: unknown currency raises ValueError (fail-CLOSED, not a silent 0/pass-through -- correct)",
    outcome3[0] == "ValueError",
)

outcome4 = expect_raises(
    "convert_to_usd(9000, 'jpy', {})  (fx_config missing jpy_usd_rate key)",
    Exception, allocator.convert_to_usd, 9000, "jpy", {},
)
if outcome4[0] == "KeyError":
    finding(
        "INFO",
        "convert_to_usd() raises KeyError (not a friendlier ValueError/default) when fx_config is "
        "present but missing 'jpy_usd_rate'. run_pass.py's own fx_config load "
        "(`_read_json(os.path.join(state_dir, 'ceo-fx-config.json'), {'jpy_usd_rate': 150.0})`) always "
        "supplies a default dict WITH 'jpy_usd_rate' when the file is absent OR unparsable, so this "
        "path is only reachable if ceo-fx-config.json exists on disk, parses as valid JSON, but is "
        "missing that one key (e.g. `{}` or `{\"other_key\": 1}` written by a bug/hand-edit) -- not "
        "reachable via simple file-absence. Non-blocking but worth a defensive default in a future "
        "iteration (spec REQ-CEO-050 documents a fallback rate of 150.0 for the FILE-MISSING case, "
        "not for this present-but-malformed-content case).",
    )

chk("realized_profit_usd([]) == 0.0 (empty entries, no crash)", allocator.realized_profit_usd([], {"jpy_usd_rate": 150.0}), 0.0)

outcome5 = expect_raises(
    "realized_profit_usd([{'amount': 5.0}], {...})  (entry missing 'currency' key)",
    Exception, allocator.realized_profit_usd, [{"amount": 5.0}], {"jpy_usd_rate": 150.0},
)
chk_true(
    "realized_profit_usd: entry missing 'currency' key raises KeyError (fail-closed -- correct, this "
    "should never happen since sum_earn_by_currency() always produces well-formed {amount,currency} "
    "entries, but a hand-crafted CEO_AGENT_DECISIONS_JSON-adjacent caller could hit this)",
    outcome5[0] == "KeyError",
)

print()
print("=== SECTION 4: capital_increase_within_realized_profit — boundary / negative values ===")
chk(
    "capital_increase_within_realized_profit(100, 50, 0.0) -- zero realized profit, any increase rejected",
    allocator.capital_increase_within_realized_profit(100, 50, 0.0), False,
)
chk(
    "capital_increase_within_realized_profit(100, 50, -30.0) -- NEGATIVE realized profit (a loop that "
    "is currently net-negative, e.g. spend > earn) still correctly rejects any increase, not just "
    "clamps to 0",
    allocator.capital_increase_within_realized_profit(100, 50, -30.0), False,
)
chk(
    "capital_increase_within_realized_profit(40, 50, -30.0) -- a DECREASE with negative realized "
    "profit is still allowed (increase<=0 short-circuit fires correctly even when profit is negative)",
    allocator.capital_increase_within_realized_profit(40, 50, -30.0), True,
)
chk(
    "capital_increase_within_realized_profit(50, 50, -30.0) -- exact-equal (zero delta) with negative "
    "profit is allowed (increase==0 <= 0 short-circuit)",
    allocator.capital_increase_within_realized_profit(50, 50, -30.0), True,
)

print()
print("=== SECTION 5: update_miss_count / should_rollback / next_cooldown — negative & boundary inputs ===")
chk(
    "update_miss_count(prev_count=-1, beats=False, cooldown=0) -- a NEGATIVE prev_count (should never "
    "occur via normal state-machine flow, but state file could be hand-edited/corrupted) is treated "
    "as an ordinary int and incremented, not clamped -- returns 0 (arithmetic, not a crash)",
    allocator.update_miss_count(-1, False, 0), 0,
)
chk(
    "update_miss_count(prev_count=-5, beats=True, cooldown=0) -- negative prev_count + a beat still "
    "resets cleanly to 0 (no crash, no negative propagation)",
    allocator.update_miss_count(-5, True, 0), 0,
)
chk(
    "should_rollback(consecutive_miss_count=-1, cooldown=0, threshold=2) -- negative count never "
    "satisfies >=threshold, correctly returns False (not a crash, not a false-positive)",
    allocator.should_rollback(-1, 0, threshold=2), False,
)
chk(
    "should_snapshot(consecutive_miss_count=0, cooldown_weeks_remaining=-1) -- a NEGATIVE cooldown "
    "value (should never occur, defensive check) does NOT satisfy '==0', so should_snapshot correctly "
    "stays frozen (fail-closed toward NOT overwriting the rollback snapshot) rather than snapshotting "
    "on a corrupted state value",
    allocator.should_snapshot(0, -1), False,
)
chk(
    "next_cooldown_weeks_remaining(cooldown_weeks_remaining_in=-1, rollback_fired=False) -- negative "
    "input, no rollback: the `> 0` guard means a negative value takes the ELSE branch and returns 0 "
    "(self-healing/self-correcting, not a crash, not a negative propagated forward)",
    allocator.next_cooldown_weeks_remaining(-1, False), 0,
)
chk(
    "next_cooldown_weeks_remaining(cooldown_weeks_remaining_in=999999, rollback_fired=False) -- huge "
    "cooldown value decrements by exactly 1 as usual, no overflow/special-case bug",
    allocator.next_cooldown_weeks_remaining(999999, False), 999998,
)

print()
print("=== SECTION 6: build_next_registry — non-dict / huge / adversarial fixture shapes ===")
# Empty-everything already covered by the shipped suite (PROP-CEO-024) -- probe genuinely NEW shapes:
# a loop present in allocation_decisions but ABSENT from existing_registry (first-ever allocation for
# a brand-new loop, e.g. a freshly-added cadence-contracts.json entry).
out = allocator.build_next_registry(
    existing_registry={},
    budget_snapshot_by_loop={},
    rollback_restore=None,
    allocation_decisions={"brand-new-loop": {"allocation": {"x": 1}, "consecutive_bad_weeks": 0}},
)
chk_true(
    "build_next_registry: a loop with NO existing_registry entry at all (first-ever allocation) is "
    "assembled without crashing and its allocation is set correctly",
    out.get("brand-new-loop", {}).get("allocation") == {"x": 1},
)

# rollback_restore and allocation_decisions BOTH populated for the SAME loop (the spec says this
# combination should structurally never occur within one real WEEKLY pass, REQ-CEO-044's own
# docstring calls it "a万一の想定外呼び出し" -- probe it anyway as a defensive fail-safe check).
out2 = allocator.build_next_registry(
    existing_registry={"clip": {"allocation": {"x": 1}, "budget": {"b": 1}}},
    budget_snapshot_by_loop={"clip": {"b": 2}},
    rollback_restore={"clip": {"allocation": {"x": 99}}},
    allocation_decisions={"clip": {"allocation": {"x": 9}, "consecutive_bad_weeks": 3}},
)
chk(
    "build_next_registry: BOTH rollback_restore AND allocation_decisions non-empty for the SAME loop "
    "(should structurally never happen in one real pass per REQ-CEO-058's own gate, but the function "
    "is a defensive fail-safe) -- rollback wins for 'allocation' as documented",
    out2["clip"]["allocation"], {"x": 99},
)
chk(
    "build_next_registry: in that same adversarial fixture, 'consecutive_bad_weeks' still comes from "
    "allocation_decisions (rollback_restore does not carry that subkey at all) -- no crash mixing the "
    "two sources for different subkeys of the same loop",
    out2["clip"]["consecutive_bad_weeks"], 3,
)

# Huge numeric allocation values flowing through unchanged (build_next_registry does not itself
# range-check -- that is validate_allocation_ranges()'s job, called by the caller BEFORE this
# function per REQ-CEO-042; confirm build_next_registry itself has no silent clamp that would mask a
# caller bug).
out3 = allocator.build_next_registry(
    existing_registry={},
    budget_snapshot_by_loop={},
    rollback_restore=None,
    allocation_decisions={"clip": {"allocation": {"capital_cap_usd": 10 ** 12}, "consecutive_bad_weeks": 0}},
)
chk(
    "build_next_registry: a huge (1e12) capital_cap_usd value passes through unchanged -- confirms "
    "build_next_registry does NOT itself range-gate (that is validate_allocation_ranges()'s exclusive "
    "job per REQ-CEO-042/REQ-CEO-044 docstring, called earlier in run_pass.py's step 8 before this "
    "function is ever invoked)",
    out3["clip"]["allocation"]["capital_cap_usd"], 10 ** 12,
)

print()
print("=== SECTION 7: validate_allocation_ranges — negative / huge / unknown-field adversarial input ===")
ranges_cfg = {"pass_frequency_multiplier": {"min": 0.1, "max": 10}}
chk(
    "validate_allocation_ranges({'pass_frequency_multiplier': -5}, ranges_cfg) -- a NEGATIVE value "
    "below the configured min is correctly rejected",
    allocator.validate_allocation_ranges({"pass_frequency_multiplier": -5}, ranges_cfg), False,
)
chk(
    "validate_allocation_ranges({'pass_frequency_multiplier': 1e9}, ranges_cfg) -- a HUGE value above "
    "the configured max is correctly rejected",
    allocator.validate_allocation_ranges({"pass_frequency_multiplier": 1e9}, ranges_cfg), False,
)
chk(
    "validate_allocation_ranges({'unknown_field_agent_invented': 999999999}, ranges_cfg) -- a field "
    "NOT present in ranges_cfg at all (e.g. an agent proposing a made-up allocation field) is NOT "
    "gated -- passes through as True. This is spec-compliant per REQ-CEO-042's own docstring "
    "('Fields absent from ranges_cfg are not gated') but is worth flagging: an agent-proposed field "
    "name that happens to not be in ranges_cfg bypasses range validation entirely and would reach "
    "loop-registry.json unchecked via allocation_decisions.",
    allocator.validate_allocation_ranges({"unknown_field_agent_invented": 999999999}, ranges_cfg), True,
)
finding(
    "INFO",
    "validate_allocation_ranges() only gates fields explicitly listed in ceo-allocation-ranges.json. "
    "Any allocation field name not in that config (typo, or a genuinely new field an agent invents) "
    "passes through unchecked. Not a spec violation (REQ-CEO-042 documents this explicitly) but is a "
    "defense-in-depth gap worth noting for anyone editing ceo-allocation-ranges.json: it must be kept "
    "in sync with every allocation field the agent is allowed to set, or new fields silently bypass "
    "range validation.",
)

print()
print("=== SECTION 8: bandit — cold-start A=I, empty arms, select_scores boundary ===")
chk_true(
    "bandit.cold_start_state(3, 0.5)['A'] is the 3x3 identity matrix",
    bandit.cold_start_state(3, 0.5)["A"] == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
)
chk(
    "bandit.select_scores(context, arms={}) -- EMPTY arms dict (no loop has ever been seen yet, "
    "true cold-start company) returns {} without crashing (matches its own docstring 'if not arms: "
    "return {}')",
    bandit.select_scores([1.0, 0.0, 0.0], {}), {},
)
# A=I cold start selected as an arm and scored: exploit should be exactly the prior b-dot-context.
cold = bandit.cold_start_state(3, 0.5)
scores = bandit.select_scores([1.0, 0.0, 0.0], {"clip": cold}, alpha=1.0)
chk(
    "bandit.select_scores on a single cold-start (A=I) arm: exploit == context·theta == context·b "
    "(since A=I -> theta=b) == 1.0*0.5 + 0*0.5 + 0*0.5 == 0.5",
    round(scores["clip"]["exploit"], 6), 0.5,
)

print()
print(f"=== adversarial_boundary_probe: {P} passed {F} failed, {len(FINDINGS)} findings recorded ===")
for sev, text in FINDINGS:
    print(f"[{sev}] {text}")

sys.exit(0)
