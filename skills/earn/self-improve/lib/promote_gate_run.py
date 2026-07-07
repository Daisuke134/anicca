"""promote_gate_run.py — close-loop Gap 3: the EFFECTFUL driver `promote_gate.sh` invokes.

Confined here (mirrors `lib/promote.py`'s own "subprocess deliberately confined to THIS module"
convention): everything that talks to a real subprocess (the fresh `claude --model opus` adversary
call) or performs the actual promotion side effect. The DETERMINISTIC/pure decision logic
(`assess_candidate`/`decide_promotion`/`promote_if_approved`) lives in `lib/promote_gate.py` and is
unit-tested there (`tests/test_adversary_disapprove.py`) WITHOUT ever spending a real LLM call —
this module is instead exercised by the one real, human-zero "RUN IT ONCE" proof invocation
(evidence under `evidence/close-loop/`), never by the fast pytest suite.

REQ-RH4 order enforced end-to-end: (1)+(2) (stage2 beats_baseline + trip-wire clear) are checked by
`assess_candidate` BEFORE this module ever shells out to an LLM — an ineligible candidate never
costs a single token. Only an eligible candidate reaches step (3), the fresh adversary call.

Usage: `python3 lib/promote_gate_run.py <candidate_program_path> <run_dir> [--dry-run]`
`--dry-run` (or `PROMOTE_GATE_DRY_RUN=1`) still runs the full assessment + real adversary call, but
never actually commits the promotion (useful for smoke-testing the mechanism against a
hand-crafted candidate without mutating the committed baseline strategy file).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from difflib import unified_diff
from typing import Optional

_SELF_IMPROVE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SELF_IMPROVE_DIR not in sys.path:
    sys.path.insert(0, _SELF_IMPROVE_DIR)

import evaluator  # noqa: E402
from lib import promote_gate  # noqa: E402

ADVERSARY_JSON_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
            "reason": {"type": "string"},
        },
        "required": ["verdict", "reason"],
        "additionalProperties": False,
    }
)

MAX_BUDGET_USD = "1.00"  # hard $ cap on the single adversary call (paper-only proof, cheap insurance)
ADVERSARY_TIMEOUT_S = 600


def _repo_root() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=_SELF_IMPROVE_DIR, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _resolve_claude_bin() -> str:
    return shutil.which("claude") or "/opt/homebrew/bin/claude"


def _build_prompt(assessment: dict, candidate_code: str, baseline_code: str) -> str:
    diff_lines = list(
        unified_diff(
            baseline_code.splitlines(keepends=True),
            candidate_code.splitlines(keepends=True),
            fromfile="strategies/pm_backtest_strategy.py (baseline)",
            tofile="candidate (openevolve-proposed)",
        )
    )
    diff_text = "".join(diff_lines) or "(no textual diff — candidate is byte-identical to baseline)"

    return f"""You are the fresh, independent per-candidate promotion adversary for Anicca's
self-improve harness (behavioral-spec.md REQ-RH4 step 3). This is a PAPER/BACKTEST-ONLY harness —
nothing you approve executes a live trade; "promote" only means merging this diff into a committed
backtest strategy file (strategies/pm_backtest_strategy.py). No human is in this loop; your verdict
is the final gate before any promotion.

DETERMINISTIC PRE-CHECKS (already computed, before you were invoked — you do not need to
re-derive these, but you MAY spot-check anything below using Read/Bash if you want independent
verification):
- scope_guard verdict: {assessment['scope_guard_reason']} (ok={assessment['scope_guard_ok']})
- stage1_pass: {assessment['stage1_pass']}
- stage2_pass (beats_baseline): {assessment['stage2_pass']}
- combined_score (risk-adjusted, candidate): {assessment['combined_score']}
- baseline_stage2_score (risk-adjusted, baseline): {assessment['baseline_stage2_score']}
- mean_oos_net_usd: {assessment['mean_oos_net_usd']}  std_oos_net_usd: {assessment['std_oos_net_usd']}
- worst_window_oos_net_usd: {assessment['worst_window_oos_net_usd']}
- trip-wire clear (not an implausible >3x jump over population_best={assessment['population_best_used']}): {assessment['tripwire_clear']}

THE DIFF (candidate vs the frozen baseline, EVOLVE-BLOCK region only — scope_guard already
verified nothing outside it changed):
```diff
{diff_text}
```

YOUR JOB: decide whether this candidate represents a GENUINE selection/edge improvement, or is
variance-amplification / leverage / overfitting to this specific historical fixture dressed up as
one. Specifically weigh:
1. Does the candidate change WHICH trades are selected (a real selection/logic change), or does it
   only change stake SIZE on the same selection as baseline (leverage)? A pure stake multiplier on
   an unchanged selection cannot genuinely raise a risk-adjusted (mean/stddev) score except by
   floating-point noise — if you see one anyway, treat it with suspicion.
2. Is the worst individual OOS window (`worst_window_oos_net_usd` above) non-negative, or does the
   apparent improvement hide behind a good average with a hidden bad window (EDGE-5)?
3. Is std_oos_net_usd suspiciously close to zero (a near-zero-variance artifact from only 3 OOS
   data points can produce an inflated ratio that is not really "proven" by 3 points)?
4. Does the candidate's own code stay inside the single evolvable function
   (`score_candidate`), doing plausible strategy logic (thresholds, sizing, feature combination) —
   not something structurally suspicious?

Write your verdict as your ONLY structured output: {{"verdict": "PASS" or "FAIL", "reason": "<one
paragraph, concrete, citing the specific numbers/diff content that drove your decision>"}}.
"PASS" means you are willing to have this candidate promoted into the committed baseline strategy
file for future backtest runs. Default to FAIL when genuinely uncertain (fail-closed)."""


def _invoke_adversary(prompt: str, repo_root: str) -> dict:
    claude_bin = _resolve_claude_bin()
    # The prompt is sent via STDIN, never as a trailing positional argument: `--add-dir` takes a
    # variadic list of directories ("Additional directories...", nargs: variadic), and a bare
    # positional string placed right after it gets silently swallowed as an extra --add-dir value
    # instead of being recognized as the prompt (confirmed live: this exact ordering produced
    # `Error: Input must be provided either through stdin or as a prompt argument` — the CLI saw
    # zero prompt args left over). Piping via stdin sidesteps the whole ordering question.
    cmd = [
        claude_bin,
        "--model",
        "opus",
        "--dangerously-skip-permissions",
        "--print",
        "--output-format",
        "json",
        "--json-schema",
        ADVERSARY_JSON_SCHEMA,
        "--max-budget-usd",
        MAX_BUDGET_USD,
        "--add-dir",
        repo_root,
    ]
    try:
        result = subprocess.run(
            cmd, cwd=repo_root, input=prompt, capture_output=True, text=True, timeout=ADVERSARY_TIMEOUT_S
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"adversary process timed out after {ADVERSARY_TIMEOUT_S}s"}
    except FileNotFoundError:
        return {"ok": False, "error": f"claude binary not found (tried {claude_bin})"}

    if result.returncode != 0:
        return {"ok": False, "error": f"adversary process exited {result.returncode}: {result.stderr[-2000:]}"}

    try:
        outer = json.loads(result.stdout)
    except ValueError:
        return {"ok": False, "error": f"adversary stdout was not valid JSON: {result.stdout[-2000:]}"}

    structured = outer.get("structured_output")
    if not isinstance(structured, dict) or "verdict" not in structured:
        return {"ok": False, "error": f"adversary response missing structured_output.verdict: {outer}"}

    return {
        "ok": True,
        "verdict": structured.get("verdict"),
        "reason": structured.get("reason", ""),
        "cost_usd": outer.get("total_cost_usd"),
        "session_id": outer.get("session_id"),
    }


def main(argv: list) -> int:
    if len(argv) < 3:
        print("usage: promote_gate_run.py <candidate_program_path> <run_dir> [--dry-run]", file=sys.stderr)
        return 2
    candidate_path = argv[1]
    run_dir = argv[2]
    dry_run = "--dry-run" in argv[3:] or os.environ.get("PROMOTE_GATE_DRY_RUN") == "1"

    os.makedirs(run_dir, exist_ok=True)
    verdict_path = os.path.join(run_dir, "verdict.json")
    log_path = os.path.join(run_dir, "promote_gate.log")

    def _log(msg: str) -> None:
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(line)

    if not os.path.isfile(candidate_path):
        out = {"promote": False, "reason": f"candidate program not found at {candidate_path}", "adversary_invoked": False}
        with open(verdict_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        _log(f"FATAL candidate not found: {candidate_path}")
        return 1

    assessment = promote_gate.assess_candidate(candidate_path)
    with open(os.path.join(run_dir, "assessment.json"), "w", encoding="utf-8") as f:
        json.dump(assessment, f, indent=2, default=str)

    if not assessment["eligible_for_adversary_review"]:
        decision = promote_gate.decide_promotion(assessment, adversary_verdict=None)
        out = {**decision, "adversary_invoked": False, "assessment": assessment}
        with open(verdict_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, default=str)
        _log(f"NOT ELIGIBLE for adversary review (no LLM call made): {decision['reason']}")
        return 0

    repo_root = _repo_root()
    candidate_code = _read_text(candidate_path)
    baseline_code = _read_text(evaluator.BASELINE_PATH)
    prompt = _build_prompt(assessment, candidate_code, baseline_code)

    _log("candidate is eligible — invoking fresh Opus adversary (real call, real $ per --max-budget-usd cap)")
    adversary_result = _invoke_adversary(prompt, repo_root)

    if not adversary_result["ok"]:
        decision = promote_gate.decide_promotion(
            assessment, adversary_verdict=None, adversary_reason=f"adversary unavailable/erroring: {adversary_result['error']}"
        )
        out = {**decision, "adversary_invoked": True, "adversary_error": adversary_result["error"], "assessment": assessment}
        with open(verdict_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, default=str)
        _log(f"ADVERSARY UNAVAILABLE/ERRORED (fail-closed, not promoted): {adversary_result['error']}")
        return 0

    decision = promote_gate.decide_promotion(
        assessment, adversary_verdict=adversary_result["verdict"], adversary_reason=adversary_result["reason"]
    )
    _log(
        f"ADVERSARY VERDICT: {adversary_result['verdict']} — {adversary_result['reason']} "
        f"(cost_usd={adversary_result.get('cost_usd')})"
    )

    # IMPORTANT (found the hard way during this feature's own smoke test, see execution notes):
    # `lib.promote.promote(..., commit=False)` still WRITES `baseline_path` to disk unconditionally
    # — only the git-commit step is skipped, per its own documented "commit=False writes the file
    # only (for dry-run tooling)" contract. That is NOT a safe no-op for a `--dry-run` smoke test
    # against the REAL committed baseline path, so `--dry-run` here skips calling
    # `promote_if_approved`/`promote.promote` ENTIRELY (zero file writes, zero git operations) —
    # it only ever reports what the decision WOULD have been.
    if dry_run:
        promote_result = {
            "committed": False,
            "reason": "dry-run: promote_if_approved/promote.promote was never called (zero file/git side effects)",
            "would_promote": decision["promote"],
        }
    else:
        promote_result = promote_gate.promote_if_approved(
            candidate_code, evaluator.BASELINE_PATH, decision, cwd=repo_root, commit=True
        )
    out = {
        **decision,
        "adversary_invoked": True,
        "adversary_cost_usd": adversary_result.get("cost_usd"),
        "adversary_session_id": adversary_result.get("session_id"),
        "dry_run": dry_run,
        "promote_result": promote_result,
        "assessment": assessment,
    }
    with open(verdict_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)

    if decision["promote"] and not dry_run:
        _log(f"PROMOTED: committed={promote_result.get('committed')} commit={promote_result.get('commit')}")
    elif decision["promote"] and dry_run:
        _log("DRY-RUN: adversary said PASS but --dry-run set — NOT committed (smoke test only)")
    else:
        _log(f"NOT PROMOTED: {decision['reason']}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
