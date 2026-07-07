"""evaluator.py — the effectful evaluation shell openevolve calls per candidate.

`evaluate(program_path)` / `evaluate_stage1(program_path)` / `evaluate_stage2(program_path)` each
return a PLAIN DICT (openevolve's real `EvaluationResult` also accepts a plain dict of metrics —
see openevolve's evaluator interface; this module deliberately does NOT `import openevolve` so the
deterministic tests in tests/ stay dependency-light and runnable without vendoring the real
package, per this stage's scope).

`evaluate_stage1` runs `scope_guard.check(...)` FIRST, before any backtest computation (REQ-DL5).
When scope_guard rejects a candidate, evaluation stops immediately: the returned
`combined_score` is the fail-sentinel (REQ-EV6/DL5) and `evaluate_stage2` is NEVER called for
that candidate.

`combined_score` is ALWAYS derived from a real backtest over the historical fixture — never an LLM
judge's subjective score (REQ-GR1, REQ-EV1, Jason Wei's Verifier's Law). Stage1's `combined_score`
is raw `net_usd(gross, cost)` on the cheap filter window (unchanged). Stage2's (and therefore the
full `evaluate()` cascade's) `combined_score` is a RISK-ADJUSTED metric —
`gate_math.risk_adjusted_score(oos_scores)`, a Sharpe-like mean/stddev over the walk-forward OOS
window scores — added in the close-loop revision (2026-07-08) specifically because a raw-USD
stage2 score let a real accepted candidate (`233d923c`, see execution-notes-self-improve.md) win
purely by leveraging (scaling up) the SAME trade selection as baseline, not by finding a better
one. Risk-adjusting is structurally leverage-resistant (see `gate_math.risk_adjusted_score`'s own
docstring for the proof) while still being 100% backtest-derived, deterministic, and non-LLM —
still Verifier's Law-compliant, just risk- rather than magnitude-scored.

This module reads the historical fixture (read-only) and NEVER writes to `earn-ledger.jsonl` or
any other live-system state file (REQ-EV7). It NEVER imports any order-execution module
(`place_order`, `execute_swap`, a live `run.sh`) — REQ-RH3's sandbox boundary.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from typing import Optional

_SELF_IMPROVE_DIR = os.path.dirname(os.path.abspath(__file__))
if _SELF_IMPROVE_DIR not in sys.path:
    sys.path.insert(0, _SELF_IMPROVE_DIR)

from lib import gate_math, scope_guard  # noqa: E402  (path insert must happen first)

# The frozen, committed baseline strategy program — the reference `diff_in_scope`/denylist checks
# every candidate against, and whose own stage2 walk-forward score is the `beats_baseline` floor.
BASELINE_PATH = os.path.join(_SELF_IMPROVE_DIR, "strategies", "pm_backtest_strategy.py")

# Real openevolve (verified 2026-07-07 against pip-installed openevolve==0.3.0) copies each
# candidate's file TEXT into a throwaway `tempfile.NamedTemporaryFile` under the OS temp dir before
# calling evaluate_stage1/evaluate_stage2 with that temp path — never the original
# strategies/pm_backtest_strategy.py path. `pm_backtest_strategy.py::load_fixture`'s own default
# argument (`os.path.dirname(__file__)`-relative) therefore resolves to the WRONG directory for
# every real candidate (`/tmp/.../fixtures/pm_history.csv`, which does not exist) — confirmed live:
# a real trial run failed every single candidate, including generation-0's unmodified copy of the
# baseline, with `FileNotFoundError` before this fix. This module (evaluator.py) is always loaded
# by openevolve from its REAL on-disk path (never tempfile-copied — only the strategy/initial
# program is), so an absolute path computed from evaluator.py's own location is stable across every
# candidate regardless of where openevolve happens to have written that candidate's temp file.
FIXTURE_PATH = os.path.join(_SELF_IMPROVE_DIR, "strategies", "fixtures", "pm_history.csv")

# Historical fixture has 6 non-overlapping windows (0..5). Stage1 uses window 0 alone as a cheap
# filter (REQ-EV2); its window is a SUBSET of the union of windows stage2 draws its walk-forward
# pairs from (PROP-SI-EV2). Stage2 draws 3 fully-disjoint (train, test) window pairs (REQ-EV3 —
# "≥3 non-overlapping window pairs"); only the `test` (out-of-sample) window's score ever counts
# toward `combined_score` (never the in-sample `train` window).
STAGE1_WINDOW = 0
WINDOW_PAIRS = ((0, 1), (2, 3), (4, 5))

# REQ-EV2 cascade filter: stage1's quick-window net USD must clear this bar before stage2 (the
# expensive walk-forward run) is attempted at all.
STAGE1_MIN_NET_USD = 1.0

# REQ-EV6/DL5 fail-sentinel: never a value that could beat a non-negative baseline (beats_baseline
# requires strictly > max(baseline_score, 0), so 0.0 can never satisfy that comparison — consistent
# with EDGE-2's "ties do not beat baseline" rule).
FAIL_SENTINEL = 0.0

# REQ-RH1 reward cap: no single generation's combined_score is ever reported above this ceiling.
# Left at 500.0 unchanged by the close-loop risk-adjusted revision even though a genuine
# risk-adjusted score on this fixture's scale typically sits in single digits (0-10ish, see
# tests/test_baseline_beat.py's real numbers) — the cap's real job under the new metric is
# guarding the ONE degenerate case risk_adjusted_score's own `eps` denominator creates: a
# candidate whose OOS window scores are (near-)identical (stddev -> 0) produces an artificially
# huge ratio (mean / eps) despite representing only 3 real data points, not a genuinely proven
# edge. 500.0 is generous relative to normal scores specifically so it never clips a real,
# moderate improvement, while still bounding the eps-driven degenerate blowup case (REQ-RH1).
COMBINED_SCORE_CEILING = 500.0

# REQ-RH2 trip-wire multiple: a candidate scoring more than this multiple of the population's
# best-ever stage2 score is flagged for adversary review rather than auto-promoted.
TRIPWIRE_MULTIPLE = 3.0


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _load_candidate_module(program_path: str):
    """Import the candidate program file as a fresh module (by absolute path, so two different
    candidate files never collide under the same module name) and return it. Only ever called
    AFTER scope_guard.check has passed for this exact file text — see evaluate_stage1."""
    module_name = f"_self_improve_candidate_{abs(hash(os.path.abspath(program_path)))}"
    spec = importlib.util.spec_from_file_location(module_name, program_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # noqa: S102 — confined to backtest-only pure functions
    return module


def evaluate_stage1(program_path: str, config: Optional[dict] = None) -> dict:
    """REQ-EV2/DL5: scope_guard's full check chain runs FIRST. A rejected candidate returns the
    fail-sentinel and stops here — no backtest computation, no evaluate_stage2 call, for that
    candidate."""
    candidate_code = _read_text(program_path)
    baseline_code = _read_text(BASELINE_PATH)

    ok, reason = scope_guard.check(candidate_code, baseline_code)
    artifacts = {"scope_guard_verdict": reason}
    if not ok:
        return {
            "combined_score": FAIL_SENTINEL,
            "stage1_pass": False,
            "artifacts": artifacts,
        }

    module = _load_candidate_module(program_path)
    rows = module.load_fixture(FIXTURE_PATH)
    window_rows = [r for r in rows if r["window"] == STAGE1_WINDOW]
    cfg = config or {}
    backtest = module.run_backtest(window_rows, cfg)
    score = gate_math.net_usd(backtest["gross_usd"], backtest["cost_usd"])
    stage1_pass = score >= STAGE1_MIN_NET_USD

    return {
        "combined_score": score,
        "stage1_pass": stage1_pass,
        "artifacts": artifacts,
    }


def evaluate_stage2(program_path: str, config: Optional[dict] = None) -> dict:
    """REQ-EV3: walk-forward across WINDOW_PAIRS' OUT-OF-SAMPLE windows only. Callers MUST only
    invoke this after evaluate_stage1 has passed for the same program_path (this function does
    NOT re-run scope_guard — that gate is stage1's job, wired as evaluate()'s first operation).

    `combined_score` (close-loop revision) is `gate_math.risk_adjusted_score(oos_net_usd_scores)`
    — a Sharpe-like mean/stddev over the per-window-pair raw net USD, NOT the raw mean net USD
    itself (see evaluator.py's module docstring + gate_math.risk_adjusted_score's own docstring
    for the reward-hacking/leverage rationale). The raw per-window net USD values are still
    reported in `window_pairs` (unchanged shape) and the aggregate `mean_oos_net_usd` /
    `std_oos_net_usd` / `worst_window_oos_net_usd` are reported alongside `combined_score` so a
    human/adversary/promote_gate reviewer can see both the risk-adjusted score AND the raw dollar
    figures it was computed from — never just one opaque number."""
    module = _load_candidate_module(program_path)
    rows = module.load_fixture(FIXTURE_PATH)
    cfg = config or {}

    oos_scores = []
    window_pairs_log = []
    for train_window, test_window in WINDOW_PAIRS:
        test_rows = [r for r in rows if r["window"] == test_window]
        backtest = module.run_backtest(test_rows, cfg)
        oos_score = gate_math.net_usd(backtest["gross_usd"], backtest["cost_usd"])
        oos_scores.append(oos_score)
        window_pairs_log.append(
            {"train_window": train_window, "test_window": test_window, "oos_net_usd": oos_score}
        )

    risk_adjusted = gate_math.risk_adjusted_score(oos_scores) if oos_scores else FAIL_SENTINEL
    mean_oos = sum(oos_scores) / len(oos_scores) if oos_scores else FAIL_SENTINEL
    worst_oos = min(oos_scores) if oos_scores else FAIL_SENTINEL
    variance = (
        sum((s - mean_oos) ** 2 for s in oos_scores) / len(oos_scores) if oos_scores else 0.0
    )
    return {
        "combined_score": risk_adjusted,
        "mean_oos_net_usd": mean_oos,
        "std_oos_net_usd": variance ** 0.5,
        "worst_window_oos_net_usd": worst_oos,
        "window_pairs": window_pairs_log,
        "artifacts": {},
    }


def baseline_stage2_score(config: Optional[dict] = None) -> float:
    """The frozen baseline's OWN stage2 walk-forward score — the reference `beats_baseline`
    compares every candidate against (REQ-RH4)."""
    return evaluate_stage2(BASELINE_PATH, config)["combined_score"]


def evaluate(program_path: str, config: Optional[dict] = None) -> dict:
    """Full cascade: stage1 (cheap filter, REQ-EV2) -> stage2 (walk-forward, REQ-EV3), only when
    stage1 passes (REQ-EV4: a stage1-only pass is NOT promotion-eligible; that is enforced here by
    stage2_pass defaulting to False whenever stage1 didn't pass, since evaluate_stage2 is never
    even called in that case). `combined_score` is reward-capped (REQ-RH1) before being returned."""
    stage1_result = evaluate_stage1(program_path, config)
    if not stage1_result["stage1_pass"]:
        return {
            "combined_score": gate_math.apply_score_cap(stage1_result["combined_score"], COMBINED_SCORE_CEILING),
            "stage1_pass": False,
            "stage2_pass": False,
            "artifacts": stage1_result["artifacts"],
        }

    stage2_result = evaluate_stage2(program_path, config)
    baseline_score = baseline_stage2_score(config)
    beats = gate_math.beats_baseline(stage2_result["combined_score"], baseline_score)
    capped = gate_math.apply_score_cap(stage2_result["combined_score"], COMBINED_SCORE_CEILING)

    return {
        "combined_score": capped,
        "stage1_pass": True,
        "stage2_pass": beats,
        "baseline_stage2_score": baseline_score,
        "mean_oos_net_usd": stage2_result["mean_oos_net_usd"],
        "std_oos_net_usd": stage2_result["std_oos_net_usd"],
        "worst_window_oos_net_usd": stage2_result["worst_window_oos_net_usd"],
        "window_pairs": stage2_result["window_pairs"],
        "artifacts": stage1_result["artifacts"],
    }


def tripwire_check(candidate_score: float, population_best: float, multiple: float = TRIPWIRE_MULTIPLE) -> dict:
    """REQ-RH1/RH2 combined helper: is `candidate_score` an implausible (>`multiple`x) jump over
    `population_best`, and what is its reward-capped value? Returns
    {"flagged": bool, "capped_score": float}. A flagged candidate SHALL be routed to adversary
    review rather than auto-promoted (the routing itself is the orchestrator's job; this function
    only computes the flag + the cap)."""
    flagged = gate_math.is_implausible_jump(candidate_score, population_best, multiple)
    capped_score = gate_math.apply_score_cap(candidate_score, COMBINED_SCORE_CEILING)
    return {"flagged": flagged, "capped_score": capped_score}
