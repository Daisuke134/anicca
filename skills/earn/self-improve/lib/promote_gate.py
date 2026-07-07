"""promote_gate.py — close-loop Gap 3: the PURE/testable half of the per-candidate promotion
adversary (REQ-RH4). The EFFECTFUL half (spawning a fresh headless Opus `claude` process to render
the actual PASS/FAIL verdict) lives in `promote_gate.sh` — a real LLM call is not something a fast
deterministic pytest suite should invoke, so this module takes the adversary's verdict as a plain
string input and does everything else: the deterministic pre-checks, the ordered REQ-RH4 gate
decision, and the (mockable) commit step. This mirrors `lib/promote.py`'s own docstring convention
("tests exercising the promotion GATE... mock this function entirely").

REQ-RH4 order, exactly: (1) stage2 walk-forward PASS (beats_baseline), (2) trip-wire clear, (3)
fresh adversary PASS. Steps (1)+(2) are cheap and fully deterministic — `assess_candidate` computes
them and short-circuits `eligible_for_adversary_review=False` when either fails, so
`promote_gate.sh` never has to pay for an LLM call on a candidate that was never going anywhere
(EDGE-3: adversary unavailable/erroring still fail-closed via `decide_promotion` treating any
non-"PASS" verdict, including a missing one, as blocking).
"""
from __future__ import annotations

import os
import sys
from typing import Optional

_SELF_IMPROVE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SELF_IMPROVE_DIR not in sys.path:
    sys.path.insert(0, _SELF_IMPROVE_DIR)

import evaluator  # noqa: E402
from lib import gate_math, promote, scope_guard  # noqa: E402


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def assess_candidate(candidate_path: str, config: Optional[dict] = None, population_best: Optional[float] = None) -> dict:
    """Run every DETERMINISTIC gate (scope_guard -> evaluate() cascade -> trip-wire) for one
    candidate program file and report whether it is even eligible for the (costly, effectful)
    fresh-adversary review step. Never calls an LLM, never writes anything.

    `population_best` (REQ-RH2's "population's best-ever stage2 score"): for a single evolve run
    this defaults to the frozen baseline's own stage2 score — a documented, defensible floor (the
    population's confirmed-good starting point before this run's candidates existed). A caller with
    a real cross-run population history (e.g. from openevolve's own program database) MAY pass a
    tighter value."""
    baseline_code = _read_text(evaluator.BASELINE_PATH)
    candidate_code = _read_text(candidate_path)
    scope_ok, scope_reason = scope_guard.check(candidate_code, baseline_code)

    if not scope_ok:
        result = {
            "combined_score": evaluator.FAIL_SENTINEL,
            "stage1_pass": False,
            "stage2_pass": False,
            "baseline_stage2_score": evaluator.baseline_stage2_score(config),
            "mean_oos_net_usd": None,
            "std_oos_net_usd": None,
            "worst_window_oos_net_usd": None,
            "window_pairs": [],
        }
    else:
        result = evaluator.evaluate(candidate_path, config)
        result.setdefault("baseline_stage2_score", evaluator.baseline_stage2_score(config))
        result.setdefault("mean_oos_net_usd", None)
        result.setdefault("std_oos_net_usd", None)
        result.setdefault("worst_window_oos_net_usd", None)
        result.setdefault("window_pairs", [])

    baseline_score = result["baseline_stage2_score"]
    pop_best = population_best if population_best is not None else baseline_score
    tripwire = evaluator.tripwire_check(result["combined_score"], pop_best)

    eligible = bool(scope_ok and result["stage1_pass"] and result["stage2_pass"] and not tripwire["flagged"])

    return {
        "candidate_path": candidate_path,
        "scope_guard_ok": scope_ok,
        "scope_guard_reason": scope_reason,
        "stage1_pass": result["stage1_pass"],
        "stage2_pass": result["stage2_pass"],
        "combined_score": result["combined_score"],
        "baseline_stage2_score": baseline_score,
        "population_best_used": pop_best,
        "tripwire_flagged": tripwire["flagged"],
        "tripwire_clear": not tripwire["flagged"],
        "mean_oos_net_usd": result["mean_oos_net_usd"],
        "std_oos_net_usd": result["std_oos_net_usd"],
        "worst_window_oos_net_usd": result["worst_window_oos_net_usd"],
        "window_pairs": result["window_pairs"],
        "eligible_for_adversary_review": eligible,
    }


def decide_promotion(assessment: dict, adversary_verdict: Optional[str], adversary_reason: str = "") -> dict:
    """The REQ-RH4 gate itself, wrapping `gate_math.stage_gate`. `adversary_verdict` MUST be the
    exact string `"PASS"` to ever promote — anything else (including `None`, an empty string, or a
    non-PASS verdict text) fails closed (EDGE-3: adversary unavailable/erroring blocks promotion,
    never silently skips it). When `assessment["eligible_for_adversary_review"]` is already False,
    the adversary's opinion (if any) is irrelevant — promotion was already blocked by a
    deterministic gate, and that is reported as the reason instead."""
    if not assessment["eligible_for_adversary_review"]:
        return {
            "promote": False,
            "reason": (
                "deterministic gate not cleared before adversary review: "
                f"scope_guard_ok={assessment['scope_guard_ok']} ({assessment['scope_guard_reason']}), "
                f"stage1_pass={assessment['stage1_pass']}, stage2_pass={assessment['stage2_pass']}, "
                f"tripwire_clear={assessment['tripwire_clear']}"
            ),
            "adversary_verdict": None,
        }

    verdict = adversary_verdict or "MISSING"
    promotable = gate_math.stage_gate(
        stage1_pass=assessment["stage1_pass"],
        stage2_pass=assessment["stage2_pass"],
        tripwire_clear=assessment["tripwire_clear"],
        adversary_verdict=verdict,
    )
    reason = adversary_reason or (
        "fresh adversary PASS" if promotable else f"fresh adversary verdict was {verdict!r}, not PASS"
    )
    return {"promote": promotable, "reason": reason, "adversary_verdict": verdict}


def promote_if_approved(
    candidate_code: str, baseline_path: str, decision: dict, *, cwd: Optional[str] = None, commit: bool = True
) -> dict:
    """The ONLY code path that ever calls `lib.promote.promote` (the actual git-commit side
    effect) — and only when `decision["promote"]` is True. This indirection (rather than calling
    `promote.promote` inline everywhere) is what makes
    `tests/test_adversary_disapprove.py` able to assert "promote() is NEVER called" by mocking a
    single, narrow entrypoint."""
    if not decision.get("promote"):
        return {"committed": False, "reason": decision.get("reason", "not promoted")}
    return promote.promote(candidate_code, baseline_path, cwd=cwd, commit=commit)
