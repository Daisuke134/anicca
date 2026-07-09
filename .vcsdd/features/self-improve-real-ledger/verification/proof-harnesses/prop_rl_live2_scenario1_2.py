"""PROP-RL-LIVE2 scenarios 1+2: real compute_realized_gate + decide_promotion against
a disposable git clone (real git history) + the REAL live ledger.

Scenario 1: eligible candidate, disposable CLONE of /Users/anicca/anicca (real git history,
including the real "feat(self-improve): promote candidate" commit), env=None so the REAL ledger
resolves via ledger_reader's own __file__-relative default -> real realized_gate assembled ->
fed into the REAL decide_promotion.

Scenario 2: genuinely trigger resolved=False (NOT a hand-built dict) by deleting the
ledger_reader module's own `__file__` global for the duration of one call (simulates the exotic
"cannot determine our own module __file__" packaging context REQ-RL1.3 guards against) -> the
REAL compute_realized_gate/decide_promotion functions run unmodified -> unconditional block.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

SELF_IMPROVE_DIR = "/Users/anicca/anicca/skills/earn/self-improve"
sys.path.insert(0, SELF_IMPROVE_DIR)
sys.path.insert(0, os.path.join(SELF_IMPROVE_DIR, "tests"))

import evaluator  # noqa: E402
from lib import ledger_reader, promote_gate  # noqa: E402
from conftest import patched_baseline_code, write_candidate_with_fixtures  # noqa: E402

assert "ANICCA_HOME" not in os.environ

REAL_REPO = "/Users/anicca/anicca"


def log(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


tmp_root = tempfile.mkdtemp(prefix="prop-rl-live2-")
clone_dir = os.path.join(tmp_root, "repo_clone")

log("STEP 0: disposable git clone (real git history, read-only, never the live repo)")
result = subprocess.run(["git", "clone", "-q", REAL_REPO, clone_dir], capture_output=True, text=True)
print(f"git clone exit={result.returncode} stderr={result.stderr.strip()}")
assert result.returncode == 0

clone_baseline_path = os.path.join(
    clone_dir, "skills", "earn", "self-improve", "strategies", "pm_backtest_strategy.py"
)
assert os.path.isfile(clone_baseline_path)

# Independently confirm (git log directly, not via our code) what the clone's real history says,
# as ground truth to compare compute_realized_gate's own git-log call against.
ground_truth = subprocess.run(
    ["git", "log", "-1", "--format=%ct", "--fixed-strings",
     "--grep=feat(self-improve): promote candidate", "--",
     "skills/earn/self-improve/strategies/pm_backtest_strategy.py"],
    cwd=clone_dir, capture_output=True, text=True,
)
ground_truth_ts = int(ground_truth.stdout.strip())
print(f"ground-truth (raw git log in the clone) last promotion ts = {ground_truth_ts}")

log("STEP 1: build a hand-crafted ELIGIBLE candidate from the clone's own baseline text")
# Monkeypatch evaluator.BASELINE_PATH (a plain path string, not a function) to the clone's copy,
# so assess_candidate/compute_realized_gate's OWN unmodified code reads/diffs/git-logs against the
# disposable clone instead of the live repo. No function's behavior/logic is altered.
orig_baseline_path = evaluator.BASELINE_PATH
evaluator.BASELINE_PATH = clone_baseline_path

# patched_baseline_code() reads BASELINE_PATH freshly each call (conftest.read_baseline_code uses
# the module-level BASELINE_PATH constant it computed from ITS OWN __file__ though -- that
# resolves to the REAL repo's tests/ dir, not the clone). So build the candidate text manually
# here instead, reading directly from the (now-monkeypatched) evaluator.BASELINE_PATH.
with open(evaluator.BASELINE_PATH, "r", encoding="utf-8") as f:
    baseline_text = f.read()

edit_pairs = [
    ('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'),
    ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'),
]
candidate_code = baseline_text
for old, new in edit_pairs:
    assert old in candidate_code, f"expected baseline text not found in clone copy: {old!r}"
    candidate_code = candidate_code.replace(old, new, 1)

tmp_cand_dir_obj = tempfile.mkdtemp(prefix="prop-rl-live2-candidate-")
import pathlib
tmp_cand_dir = pathlib.Path(tmp_cand_dir_obj)
candidate_path = write_candidate_with_fixtures(tmp_cand_dir, candidate_code)
print(f"candidate written to: {candidate_path}")

assessment = promote_gate.assess_candidate(candidate_path)
print(f"assessment.eligible_for_adversary_review = {assessment['eligible_for_adversary_review']}")
print(f"assessment.stage1_pass={assessment['stage1_pass']} stage2_pass={assessment['stage2_pass']} "
      f"tripwire_clear={assessment['tripwire_clear']}")
print(f"assessment.mean_oos_net_usd={assessment['mean_oos_net_usd']}")
assert assessment["eligible_for_adversary_review"] is True, "candidate must be eligible (precondition)"

log("STEP 2 (SCENARIO 1): REAL compute_realized_gate against the clone's git history + REAL ledger")
realized_gate = promote_gate.compute_realized_gate(
    mean_backtest_net_usd=assessment["mean_oos_net_usd"], env=None, repo_cwd=clone_dir
)
print(json.dumps(realized_gate, indent=2))

assert realized_gate["resolved"] is True
assert realized_gate["resolution_source"] == "file_relative_default"
assert realized_gate["ledger_path"] == "/Users/anicca/anicca/skills/earn/state/earn-ledger.jsonl"
assert realized_gate["window_start_ts"] == float(ground_truth_ts), (
    realized_gate["window_start_ts"], ground_truth_ts
)
print(f"CONFIRMED: window_start_ts matches ground-truth git-log result ({ground_truth_ts})")

# Hand-prediction: every real ledger row's ts is BEFORE the last real promotion commit
# (confirmed independently: the ledger's own last row ts=1783207348 < ground_truth_ts), so
# row_count inside [window_start_ts, now) must be 0 -> sufficient False -> no block.
ledger_rows_raw = ledger_reader.read_ledger()
max_ledger_ts = max(r.get("ts", 0) for r in ledger_rows_raw)
print(f"max real ledger row ts = {max_ledger_ts}, ground_truth_ts (window_start) = {ground_truth_ts}")
if max_ledger_ts < ground_truth_ts:
    print("HAND-PREDICTION: all real rows predate the last promotion -> row_count == 0 expected")
    assert realized_gate["row_count"] == 0
    assert realized_gate["sufficient"] is False
    assert realized_gate["trend_blocks"] is False
    assert realized_gate["realism_gap_blocks"] is False
else:
    print("HAND-PREDICTION: some real rows postdate the last promotion -> row_count > 0 expected")
    assert realized_gate["row_count"] > 0

log("STEP 3: REAL decide_promotion, adversary PASS, real (non-blocking) realized_gate")
decision_pass = promote_gate.decide_promotion(assessment, "PASS", realized_gate=realized_gate)
print(json.dumps(decision_pass, indent=2, default=str))
assert decision_pass["promote"] is True, "realized_gate did not block -> adversary PASS should promote"

log("STEP 4: REAL decide_promotion, adversary MISSING (None), SAME real realized_gate")
decision_missing = promote_gate.decide_promotion(assessment, None, realized_gate=realized_gate)
print(json.dumps(decision_missing, indent=2, default=str))
assert decision_missing["promote"] is False
assert "not PASS" in decision_missing["reason"] or "MISSING" in str(decision_missing.get("adversary_verdict"))
print("CONFIRMED: realized_gate itself did not block (Step 3 promoted); the adversary's own "
      "verdict is what independently gates Step 4 -- proving realized_gate= flows through "
      "end-to-end without masking the pre-existing adversary-verdict gate.")

log("STEP 5 (SCENARIO 2): genuinely trigger resolved=False (real __file__ NameError branch, not a hand-built dict)")
orig_file_attr = ledger_reader.__dict__.pop("__file__")
try:
    real_unresolved_gate = promote_gate.compute_realized_gate(
        mean_backtest_net_usd=assessment["mean_oos_net_usd"], env=None, repo_cwd=clone_dir
    )
finally:
    ledger_reader.__dict__["__file__"] = orig_file_attr

print(json.dumps(real_unresolved_gate, indent=2))
assert real_unresolved_gate["resolved"] is False
assert real_unresolved_gate["resolution_source"] == "unresolved_no_file_context"
print("CONFIRMED: compute_realized_gate's REAL (non-mocked) code path produced resolved=False "
      "genuinely, by removing __file__ from ledger_reader's own module namespace for one call "
      "(simulating the exotic packaging context REQ-RL1.3 documents) -- not a hand-built dict.")

decision_blocked = promote_gate.decide_promotion(assessment, "PASS", realized_gate=real_unresolved_gate)
print(json.dumps(decision_blocked, indent=2, default=str))
assert decision_blocked["promote"] is False
assert "unresolved" in decision_blocked["reason"]
print("CONFIRMED: the SAME otherwise-eligible, adversary-PASS candidate (Step 3 promoted it) is "
      "UNCONDITIONALLY blocked once realized_gate.resolved is genuinely False -- REQ-RL7 proven "
      "end-to-end against a real candidate + real code path, not just a synthetic fixture.")

evaluator.BASELINE_PATH = orig_baseline_path
shutil.rmtree(tmp_root, ignore_errors=True)
shutil.rmtree(tmp_cand_dir_obj, ignore_errors=True)

print("\n=== PROP-RL-LIVE2 SCENARIOS 1+2: ALL ASSERTIONS PASSED ===")
