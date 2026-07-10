#!/usr/bin/env python3
"""test_harness_health.py -- RED (Phase 2a, feature anicca-harness-tooluse-health).
R8 (behavioral-spec.md + verification-architecture.md proof table): harness_health.py mirrors
harness-health.mjs's R1-R5 (classify_layer, compute_slot_health, compute_brain_transport_health,
compute_harness_health, should_escalate), proven identical to the JS twin via the SHARED fixture
`runtime/loop/__tests__/fixtures/harness-health-parity.json`.

skills/self/self-improve/lib/harness_health.py does not exist yet -> ImportError -> RED.
Style mirrors this directory's existing tests (test_loop_evaluators.py / test_weekly_compare.py):
a manual pass/fail counter, no pytest dependency, `python3 tests/test_harness_health.py` runnable
standalone, exit code 0 iff all checks pass.
"""
import sys, os, json, subprocess

HERE = os.path.dirname(os.path.dirname(__file__))  # .../skills/self/self-improve
sys.path.insert(0, os.path.join(HERE, "lib"))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FIXTURE_PATH = os.path.join(REPO_ROOT, "runtime", "loop", "__tests__", "fixtures", "harness-health-parity.json")

P = 0
F = 0


def chk(name, cond, extra=""):
    global P, F
    if cond:
        print(f"  ok {name}")
        P += 1
    else:
        print(f"  FAIL {name} {extra}")
        F += 1


try:
    from harness_health import (
        classify_layer,
        compute_slot_health,
        compute_brain_transport_health,
        compute_harness_health,
        should_escalate,
        DEFAULT_STREAK_THRESHOLD,
    )
except Exception as e:
    print(f"IMPORT FAILED: {type(e).__name__}: {e}")
    print("=== test_harness_health: 0 passed 1 failed ===")
    sys.exit(1)

# ── R1: classify_layer ───────────────────────────────────────────────────────
chk("R1: wake -> clean", classify_layer({"kind": "wake"}) == "clean")
chk("R1: narrate -> clean", classify_layer({"kind": "narrate"}) == "clean")
chk("R1: shutdown -> clean", classify_layer({"kind": "shutdown"}) == "clean")
chk("R1: wake_error -> brain_transport", classify_layer({"kind": "wake_error"}) == "brain_transport")
chk("R1: skill_missing -> tool_missing", classify_layer({"kind": "skill_missing"}) == "tool_missing")
chk("R1: skill_timeout -> tool_timeout", classify_layer({"kind": "skill_timeout"}) == "tool_timeout")
chk("R1: skill_error -> tool_logic", classify_layer({"kind": "skill_error"}) == "tool_logic")
chk("R1: unrecognized kind -> unknown, never throws", classify_layer({"kind": "nope"}) == "unknown")

# ── R2: compute_slot_health ──────────────────────────────────────────────────
r2_records = [
    {"ts": 1, "wake_id": "a", "kind": "wake", "slot": "x"},
    {"ts": 2, "wake_id": "b", "kind": "wake", "slot": "x"},
    {"ts": 3, "wake_id": "c", "kind": "skill_error", "slot": "x"},
    {"ts": 4, "wake_id": "d", "kind": "skill_error", "slot": "x"},
]
h = compute_slot_health(r2_records, "x")
chk("R2: wakes=4 failures=2 rate=0.5 streak=2", h["wakes"] == 4 and h["failures"] == 2 and h["failureRate"] == 0.5 and h["consecutiveFailureStreak"] == 2)
chk("R2: slot never present -> None", compute_slot_health(r2_records, "never-seen") is None)

r2_loopdetect = [
    {"ts": 1, "wake_id": "a", "kind": "wake", "slot": "x"},
    {"ts": 2, "wake_id": "b", "kind": "loop_detect", "slot": "x"},
    {"ts": 3, "wake_id": "c", "kind": "skill_error", "slot": "x"},
]
h2 = compute_slot_health(r2_loopdetect, "x")
chk("R2 (INV-LOOPDETECT-SEPARATE): loop_detect excluded -> wakes=2 failures=1", h2["wakes"] == 2 and h2["failures"] == 1, extra=str(h2))

# ── R3: compute_brain_transport_health ───────────────────────────────────────
r3_records = [
    {"ts": 1, "wake_id": "a", "kind": "wake_error"},
    {"ts": 2, "wake_id": "b", "kind": "wake"},
    {"ts": 3, "wake_id": "c", "kind": "wake_error"},
    {"ts": 4, "wake_id": "d", "kind": "wake_error"},
]
brain = compute_brain_transport_health(r3_records)
chk("R3: failures=3 streak=2 (reset by wake)", brain["failures"] == 3 and brain["consecutiveFailureStreak"] == 2, extra=str(brain))

# ── R4: compute_harness_health ───────────────────────────────────────────────
r4_records = [
    {"ts": 1, "wake_id": "a", "kind": "wake", "slot": "yield"},
    {"ts": 2, "wake_id": "b", "kind": "skill_error", "slot": "yield"},
    {"ts": 3, "wake_id": "c", "kind": "wake", "slot": "x402_sell"},
    {"ts": 4, "wake_id": "d", "kind": "wake_error"},
]
report = compute_harness_health(r4_records, streak_threshold=5)
chk("R4: perSlot keys match exactly the distinct slots present", sorted(report["perSlot"].keys()) == ["x402_sell", "yield"])
chk("R4: generatedAt present", "generatedAt" in report)

empty_report = compute_harness_health([])
chk("R4: empty records -> empty-ledger shape, never throws",
    empty_report["perSlot"] == {} and empty_report["brainTransport"]["failures"] == 0
    and empty_report["brainTransport"]["consecutiveFailureStreak"] == 0)

# ── R5: should_escalate ──────────────────────────────────────────────────────
chk("R5: one below threshold -> False", should_escalate(4, 5) is False)
chk("R5: exactly at threshold -> True", should_escalate(5, 5) is True)
chk("R5: one above threshold -> True", should_escalate(6, 5) is True)
chk("R5: DEFAULT_STREAK_THRESHOLD is 5 when env unset", DEFAULT_STREAK_THRESHOLD == 5)

# ── R8: cross-language parity against the SHARED fixture ────────────────────
if os.path.exists(FIXTURE_PATH):
    with open(FIXTURE_PATH) as f:
        fixture = json.load(f)
    parity_report = compute_harness_health(fixture["records"], streak_threshold=fixture["streakThreshold"])
    parity_report_no_ts = {k: v for k, v in parity_report.items() if k != "generatedAt"}
    chk("R8: compute_harness_health(shared fixture) matches expected field-for-field (generatedAt excluded)",
        parity_report_no_ts == fixture["expected"], extra=json.dumps(parity_report_no_ts))
else:
    chk(f"R8: shared parity fixture exists at {FIXTURE_PATH}", False)

# ── R8: harness_health_report.py CLI prints valid JSON matching compute_harness_health ──
REPORT_CLI = os.path.join(HERE, "harness_health_report.py")
if os.path.exists(REPORT_CLI) and os.path.exists(FIXTURE_PATH):
    import tempfile
    fd, tmp_ledger = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w") as tf:
        for row in fixture["records"]:
            tf.write(json.dumps(row) + "\n")
    try:
        proc = subprocess.run(
            [sys.executable, REPORT_CLI, tmp_ledger, "--threshold", "5"],
            capture_output=True, text=True, timeout=15,
        )
        chk("R8: harness_health_report.py exits 0", proc.returncode == 0, extra=proc.stderr)
        try:
            cli_report = json.loads(proc.stdout)
            cli_report_no_ts = {k: v for k, v in cli_report.items() if k != "generatedAt"}
            chk("R8: harness_health_report.py CLI JSON matches compute_harness_health(fixture_rows, 5)",
                cli_report_no_ts == fixture["expected"], extra=proc.stdout[:500])
        except Exception as e:
            chk("R8: harness_health_report.py prints valid JSON", False, extra=f"{type(e).__name__}: {e}; stdout={proc.stdout[:300]}")
    finally:
        os.unlink(tmp_ledger)
else:
    chk(f"R8: harness_health_report.py exists at {REPORT_CLI}", False)

print(f"=== test_harness_health: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
