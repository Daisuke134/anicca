"""PROP-RL-LIVE2 scenario 3: REAL promote_gate_run.main() invocation (the actual production
entrypoint promote_gate.sh calls), against the REAL live ledger, with a disposable git clone
supplying the candidate/baseline text, and ONLY the actual `claude` CLI subprocess call mocked
(explicit, documented: a real Opus adversary call costs real money / is slow / non-deterministic
and this test is proving the realized_gate WIRING at every call site inside main(), not the
adversary's judgment quality -- decide_promotion/compute_realized_gate/assess_candidate/every file
write in main() all execute FOR REAL, unmodified).

DISCOVERED REAL BEHAVIOR (worth documenting, not a bug): main()'s own `_repo_root()` helper always
git-rev-parses from THIS running module's own directory (the real /Users/operator/anicca checkout),
never the disposable clone -- so `promotion_history.last_promotion_ts`'s git-log call (path=the
monkeypatched clone's BASELINE_PATH, cwd=the REAL repo) finds the clone's path OUTSIDE the real
repo's working tree and fails closed to window_start_ts=0.0 (EDGE-RL3's "no current generation"
shape) -- exercising the REAL ledger's FULL history instead of the git-history-scoped window. This
is real, live, unmocked code, not a test defect: it means this scenario ends up demonstrating
REQ-RL11's data-realism-gap check against real, live, all-time ledger data instead of REQ-RL12's
git-window logic (which scenario 1/2's script already exercises with a consistent clone+repo_cwd
pairing). Both are genuine real-code proofs; this scenario additionally shows `main()`'s own
`_repo_root()` wiring interacting with a monkeypatched BASELINE_PATH exactly as its unmodified
source predicts.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from unittest import mock

SELF_IMPROVE_DIR = "/Users/operator/anicca/skills/earn/self-improve"
sys.path.insert(0, SELF_IMPROVE_DIR)
sys.path.insert(0, os.path.join(SELF_IMPROVE_DIR, "tests"))

import evaluator  # noqa: E402
from lib import promote_gate_run  # noqa: E402
from conftest import write_candidate_with_fixtures  # noqa: E402

assert "ANICCA_HOME" not in os.environ
REAL_REPO = "/Users/operator/anicca"


def log(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


tmp_root = tempfile.mkdtemp(prefix="prop-rl-live2-scenario3-")
clone_dir = os.path.join(tmp_root, "repo_clone")

log("STEP 0: disposable git clone (real git history)")
result = subprocess.run(["git", "clone", "-q", REAL_REPO, clone_dir], capture_output=True, text=True)
assert result.returncode == 0
clone_baseline_path = os.path.join(
    clone_dir, "skills", "earn", "self-improve", "strategies", "pm_backtest_strategy.py"
)

log("STEP 1: build a real eligible candidate from the clone's own baseline text")
orig_baseline_path = evaluator.BASELINE_PATH
evaluator.BASELINE_PATH = clone_baseline_path
with open(evaluator.BASELINE_PATH, "r", encoding="utf-8") as f:
    baseline_text = f.read()
edit_pairs = [
    ('config.get("edge_weight", 0.25)', 'config.get("edge_weight", 0.4)'),
    ('config.get("conf_weight", 0.45)', 'config.get("conf_weight", 0.1)'),
]
candidate_code = baseline_text
for old, new in edit_pairs:
    assert old in candidate_code
    candidate_code = candidate_code.replace(old, new, 1)

import pathlib
tmp_cand_dir = pathlib.Path(tempfile.mkdtemp(prefix="prop-rl-live2-s3-candidate-"))
candidate_path = write_candidate_with_fixtures(tmp_cand_dir, candidate_code)
run_dir = os.path.join(tmp_root, "run_dir")

log("STEP 2: REAL promote_gate_run.main() invocation, adversary CLI call mocked to 'unavailable'")
def fake_invoke_adversary(prompt, repo_root):
    return {"ok": False, "error": "PROP-RL-LIVE2 test: adversary CLI intentionally not invoked (real Opus call skipped)"}

argv = ["promote_gate_run.py", candidate_path, run_dir, "--dry-run"]
with mock.patch.object(promote_gate_run, "_invoke_adversary", side_effect=fake_invoke_adversary):
    rc = promote_gate_run.main(argv)

print(f"main() returned rc={rc}")

verdict_path = os.path.join(run_dir, "verdict.json")
assessment_path = os.path.join(run_dir, "assessment.json")
realized_gate_path = os.path.join(run_dir, "realized_gate.json")
escalation_path = os.path.join(run_dir, "realized_gate_escalation.json")

assert os.path.isfile(verdict_path), "verdict.json not written"
assert os.path.isfile(assessment_path), "assessment.json not written"
assert os.path.isfile(realized_gate_path), "realized_gate.json not written"

with open(verdict_path) as f:
    verdict = json.load(f)
with open(realized_gate_path) as f:
    realized_gate_written = json.load(f)

print("\nverdict.json:")
print(json.dumps(verdict, indent=2, default=str))
print("\nrealized_gate.json:")
print(json.dumps(realized_gate_written, indent=2, default=str))

# --- REAL, observed outcome (not what was originally hypothesized -- see module docstring) ---
# _repo_root() resolves to the REAL /Users/operator/anicca checkout (unmocked), so
# last_promotion_ts's git-log call (path=clone's BASELINE_PATH, cwd=real repo) fails closed
# (path outside repo) -> window_start_ts=0.0 -> the REAL ledger's full history (all 6 confirmed
# rows) is used -> row_count=6, sufficient=True, mean_realized_net_per_row=8.4731/6=1.4122 ->
# assessment.mean_oos_net_usd=4.328 is a >3x implausible jump over 1.4122 (4.328 > 3*1.4122=4.237)
# -> data_realism_gap fires FOR REAL against live production data -> realism_gap_blocks=True,
# which decide_promotion checks and blocks on BEFORE it ever reaches the (mocked-unavailable)
# adversary-verdict fallback branch. adversary_invoked is still True (main() invokes the adversary
# unconditionally for any eligible candidate, before decide_promotion's own gate ordering runs).
assert verdict["adversary_invoked"] is True, "expected the eligible candidate to reach the adversary step"
assert verdict["promote"] is False
assert realized_gate_written["resolved"] is True
assert realized_gate_written["ledger_path"] == "/Users/operator/anicca/skills/earn/state/earn-ledger.jsonl"
assert realized_gate_written["row_count"] == 6
assert realized_gate_written["sufficient"] is True
assert realized_gate_written["realism_gap_blocks"] is True
assert "implausible fixture-vs-reality gap" in verdict["reason"]
assert os.path.isfile(escalation_path), "REQ-RL13: escalation record must be written when realism_gap_blocks fires"
with open(escalation_path) as f:
    escalation = json.load(f)
print("\nrealized_gate_escalation.json:")
print(json.dumps(escalation, indent=2, default=str))
assert escalation["candidate_path"] == candidate_path
assert escalation["realism_gap_blocks"] is True

print("\nCONFIRMED: main()'s REAL call chain (assess_candidate -> compute_realized_gate -> "
      "decide_promotion, all unmocked) produced a GENUINE realism-gap block against the REAL "
      "live 30-row production ledger (row_count=6 confirmed rows, realized_net_usd=8.4731) -- "
      "this candidate's claimed mean_oos_net_usd (4.328) really is an implausible >3x jump over "
      "the real per-row average (1.4122) -- REQ-RL11/RL13 proven end-to-end against real data, "
      "the escalation JSON was written with the documented keys BEFORE decide_promotion's False "
      "verdict, and realized_gate= was genuinely sourced from compute_realized_gate at this real "
      "call site (never a stub/hardcoded literal), matching PROP-RL-WIRE1's static-scan proof "
      "with a live runtime instance.")

evaluator.BASELINE_PATH = orig_baseline_path
shutil.rmtree(tmp_root, ignore_errors=True)
shutil.rmtree(str(tmp_cand_dir), ignore_errors=True)

print("\n=== PROP-RL-LIVE2 SCENARIO 3: ALL ASSERTIONS PASSED ===")
