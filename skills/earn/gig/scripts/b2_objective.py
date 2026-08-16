#!/usr/bin/env python3
"""Decide which categories the apply lane works this pass, from measured reward.

WHY THIS EXISTS (X8c)
  category_bandit.py has produced a Thompson-sampling ranking over categories since
  a11cc68, and nothing read it. `grep -rn category_bandit` found callers: zero. The
  apply lane kept taking its order from strategy.json's priority_categories, which is
  LLM hypothesis written across 537 passes and never tied to what earned money. A
  number that no decision consumes is not a measurement, it is a decoration.

  This module is the wire. Same shape as b0_objective.py: compute the decision in code,
  hand the lane one concrete sentence, leave the judgement work (which posting, what to
  write) to the agent. The lane can no longer quietly re-rank by taste.

  Note for anyone chasing a ghost: category_bandit.select() has never emitted a
  `selected` key. Its contract is a ranking, deliberately -- picking one arm and
  discarding the rest would collapse the apply lane onto a single category per pass.
  "selected is None" is a missing field, not a failed selection. Choosing whom to apply
  to, in what order, is THIS module's job.

AUTHORITY (unchanged from category_bandit.py's docstring; restated because this file
is where it is now enforced against a live prompt)

  category ORDER ........ measured. Thompson sampling over the ledgers.
  skip_categories ....... LLM, absolute. "cannot be physically present", "violates
                          ToS", "requires a human voice" are capability and ethics
                          limits, not performance claims. A high reward may not
                          resurrect one, so every path here -- including every fallback
                          path -- re-filters through skip_tokens(). Defence in depth:
                          category_bandit already filters, and it is still done again
                          on the fallback list, because the fallback list comes
                          straight from priority_categories and the two fields have
                          been observed out of sync (skip_categories' own last entry
                          records exactly that drift, at pass420).
  wording/price/templates LLM experiments[]. Not arms. Marketplace form constraints
                          are execution requirements, never experiment dimensions.

FAIL-SAFE
  Every function here returns rather than raises, and main() returns 0 unconditionally.
  When the bandit is not steering, the order is priority_categories verbatim. The loop
  applying to a slightly worse category is a small loss; the loop not applying is the
  money entrance closed by our own hand. There is no bandit failure worth that.

EXPLORATION
  category_order is the FULL ranking, never a top-N slice. Thompson sampling only keeps
  a cold-start arm reachable if the arm is still on the list when the lane runs out of
  better options; a slice would delete the tail, and the tail is where every category
  that has never been tried lives. The objective SENTENCE names the first few for
  legibility, but the full order travels in the JSON.

CONFOUNDING (the hazard that makes this more than a wire)
  Two learners share one funnel. Thompson sampling moves the CATEGORY dimension;
  strategy.json's experiments[] keep/revert moves WORDING, PRICE and TEMPLATES. If both
  move in the same window, a change in reply rate is attributable to neither -- the
  bandit reads a wording win as a category win, and keep/revert reads a category win as
  a wording win. Both then learn the wrong thing, confidently. With ~a few applications
  per day, there is no traffic to spare on an experiment whose result cannot be read.

  So exactly one dimension holds the floor, and which one is COMPUTED, not chosen:

    bandit steering (status ok, i.e. >= MIN_TRIALS resolved trials exist)
        -> freeze_experiments = True. The category dimension moves; the lane is told to
           hold the experiment variants at their current strategy.json values and to
           start no new experiment this pass. Brief tailoring and the live category
           minimum/maximum price remain mandatory execution adjustments. Experiments
           already running still get evaluated -- winding them down needs their
           verdicts, and holding those back would strand them mid-flight forever.

    bandit not steering (fallback: insufficient_data / error / unreadable)
        -> freeze_experiments = False. A learner with nothing to say has no claim on the
           floor, and the wording loop should keep working.

  RELEASE CONDITION (also computed): the freeze lifts the moment the leading arm has
  FREEZE_RELEASE_ARM_TRIALS resolved trials OF ITS OWN. Rationale: the freeze exists to
  buy the bandit a clean window in which to separate the arms. Once the arm it is
  actually recommending carries its own per-arm evidence -- not just a posterior
  inherited from the empirical-Bayes prior -- that window has done its work, the
  category choice is stable, and the floor returns to the wording loop. The threshold is
  the same 8 as category_bandit.MIN_TRIALS on purpose: 8 is already this codebase's
  answer to "how many observations before a claim is more than noise", and inventing a
  second, differently-argued number here would be a hand-set judgement dressed up as
  design. Measured 2026-07-27: 20 resolved trials over 27 arms, top arm trials=0, so the
  freeze is ON and the release condition is genuinely far away, which is the honest
  state -- not a formality that lifts on the first pass.

DECISION LEDGER
  Every pass appends one row to category-decisions.jsonl: which authority chose, which
  category led, and the sampled/posterior numbers behind it. Same motive as X8b's
  category_source -- a decision whose inputs were not recorded cannot be audited later,
  and "was the bandit right?" is a question this loop will need to answer against
  months-old passes. Recording is strictly best-effort: bookkeeping is never allowed to
  cost an application.

NO EXTRA MODEL CALLS
  Everything here is deterministic arithmetic over ledgers already on disk. X18's
  four-call ceiling is untouched.

Usage:
  b2_objective.py                     # one-line objective for the B2 step prompt
  b2_objective.py --json              # the full decision, including category_order
  b2_objective.py --json --pass-id P  # ... and append the decision to the ledger

Spec: docs/loop-engineering/28-gig-category-bandit-spec.md,
      docs/loop-engineering/26-gig-loop-asis-tobe-plan.md (X8c row).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Sequence

_HERE = Path(__file__).resolve().parent


def _load_sibling(filename: str, alias: str):
    spec = importlib.util.spec_from_file_location(alias, _HERE / filename)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging accident
        raise RuntimeError(f"{filename} not importable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The bandit owns the ranking and the skip-token grammar. Both are imported rather than
# reimplemented so this file cannot drift into a second, subtly different definition of
# "a skipped category" -- which is precisely the class of drift skip_categories' own
# pass420 entry records.
category_bandit = _load_sibling("category_bandit.py", "category_bandit_for_b2")

STATE = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
LEDGER = STATE / "category-decisions.jsonl"

# How many categories the prompt sentence names. Legibility only -- category_order in
# the JSON always carries every arm, so this number cannot starve exploration.
NAMED_IN_SENTENCE = 6

# See CONFOUNDING above. Deliberately equal to category_bandit.MIN_TRIALS.
FREEZE_RELEASE_ARM_TRIALS = category_bandit.MIN_TRIALS

FREEZE_RELEASE_CONDITION = (
    f"the leading arm reaches {FREEZE_RELEASE_ARM_TRIALS} resolved trials of its own "
    f"(category_bandit.MIN_TRIALS), or the bandit stops steering and falls back"
)


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _arm_rows(bandit_result: dict) -> list[dict]:
    ranking = bandit_result.get("ranking")
    if not isinstance(ranking, list):
        return []
    return [r for r in ranking if isinstance(r, dict) and r.get("arm")]


def _priority(strategy: dict) -> list[str]:
    raw = strategy.get("priority_categories")
    if not isinstance(raw, list):
        return []
    out = []
    for entry in raw:
        label = category_bandit.normalize_label(entry)
        if label and label not in out:
            out.append(label)
    return out


def decide(*, bandit_result: Any, strategy: Any, top_n: int = NAMED_IN_SENTENCE) -> dict:
    """Turn a bandit ranking into the apply lane's category order and its objective.

    Pure: no I/O, no clock. Never raises -- callers are on the money path.
    """
    result = _as_dict(bandit_result)
    strat = _as_dict(strategy)

    try:
        skipped = category_bandit.skip_tokens(strat.get("skip_categories") or [])
    except Exception:
        skipped = set()

    # D4 epoch alternation: while one reversible wording/price experiment is active,
    # category is the control variable and must not move.  The experiment starter
    # snapshots the full order before mutating strategy.  Once evaluator marks it
    # kept/reverted/quarantined this branch disappears and Thompson sampling resumes.
    experiments = strat.get("experiments")
    experiments = experiments if isinstance(experiments, list) else []
    active_epoch = next((
        row for row in experiments
        if isinstance(row, dict)
        and row.get("status") == "active"
        and isinstance(row.get("frozen_category_order"), list)
    ), None)
    if active_epoch is not None:
        order = [
            category_bandit.normalize_label(value)
            for value in active_epoch["frozen_category_order"]
        ]
        order = [value for value in order if value and value not in skipped]
        if order:
            experiment_id = str(active_epoch.get("id") or "active")
            return {
                "decided_by": "experiment_epoch",
                "bandit_status": str(result.get("status") or "paused"),
                "reason": f"category_frozen_for:{experiment_id}",
                "category_order": order,
                "arms": [{"arm": value, "trials": 0} for value in order[:top_n]],
                "top_arm_trials": 0,
                "freeze_experiments": True,
                "freeze_release_condition": (
                    f"experiment_evaluator reaches a terminal verdict for {experiment_id}"
                ),
                "coverage": _as_dict(result.get("coverage")),
                "objective": (
                    f"APPLY in this fixed category order for isolated experiment "
                    f"{experiment_id}: " + " > ".join(order[:top_n])
                    + ". Do not re-rank categories during this cohort; only the "
                    "code-owned strategy mutation may vary. Categories in "
                    "skip_categories remain excluded."
                ),
            }

    steering = result.get("status") == "ok" and bool(_arm_rows(result))
    arms = _arm_rows(result) if steering else []

    # Every path re-filters. The fallback list in particular comes straight from
    # priority_categories, which has been observed holding a category that
    # skip_categories had already excluded.
    order = [a["arm"] for a in arms if a["arm"] not in skipped]
    arms = [a for a in arms if a["arm"] not in skipped]

    if not order:
        steering = False
        order = [c for c in _priority(strat) if c not in skipped]
        # Fallback rows carry no sampled numbers, and pretending otherwise would put
        # fabricated posteriors in the audit ledger.
        arms = [{"arm": c, "trials": 0} for c in order]

    decided_by = "thompson_sampling" if steering else "fallback"

    # The freeze is a claim on the shared floor, so only a steering bandit may make it,
    # and only until its leading arm can stand on its own evidence.
    top_trials = 0
    if steering and arms:
        try:
            top_trials = int(arms[0].get("trials") or 0)
        except (TypeError, ValueError):
            top_trials = 0
    freeze = steering and top_trials < FREEZE_RELEASE_ARM_TRIALS

    return {
        "decided_by": decided_by,
        "bandit_status": str(result.get("status") or "unavailable"),
        "reason": str(result.get("reason") or ""),
        "category_order": order,
        "arms": arms[:top_n],
        "top_arm_trials": top_trials,
        "freeze_experiments": freeze,
        "freeze_release_condition": FREEZE_RELEASE_CONDITION if freeze else "",
        "coverage": _as_dict(result.get("coverage")),
        "objective": _objective(decided_by, order, arms, freeze, top_n),
    }


def _objective(decided_by: str, order: list[str], arms: list[dict], freeze: bool,
               top_n: int) -> str:
    """One sentence for the B2 prompt. Concrete enough that the lane cannot re-rank."""
    named = order[:top_n]
    if not named:
        head = (
            "APPLY using strategy.json's priority_categories in the order they appear "
            "there; no measured ranking is available this pass."
        )
    elif decided_by == "thompson_sampling":
        head = (
            "APPLY in this measured category order, most promising first: "
            + " > ".join(named)
            + f" (Thompson sampling over the application ledgers; {len(order)} arms "
            "ranked, the rest of the order follows in category_order). Work down the "
            "list and only move on when a category has no open 募集 you can honestly "
            "deliver. This order is measured outcome, not preference -- do not re-rank "
            "it by taste. It is a ranking, not a whitelist: a listing outside it is "
            "still applicable once the ranked categories are exhausted."
        )
    else:
        head = (
            "APPLY in this category order, most promising first: " + " > ".join(named)
            + " (from strategy.json priority_categories -- the bandit is not steering "
            "this pass). Work down the list in order."
        )

    tail = (
        " Categories in skip_categories are excluded for capability or ethics reasons "
        "and stay excluded no matter how well they would pay."
    )
    if freeze:
        tail += (
            " EXPERIMENT FREEZE is in effect: the category dimension is the one moving "
            "right now, so keep the current experiment variants and start no new "
            "experiment this pass "
            "(evaluating experiments already running is fine). Moving both dimensions "
            "at once makes every reply unattributable to either. Freeze lifts when "
            + FREEZE_RELEASE_CONDITION
            + ". Live form validation is execution, not an experiment: every proposal "
            "must still be tailored to the specific brief "
            "and satisfy Coconala's measured 200-3000 character requirement. Adjust the "
            "strategy price to the live category minimum when it is lower, and to the "
            "request budget ceiling when the strategy price is higher; this required "
            "form-compatible price is not a new experiment. A form validation or "
            "strategy-price mismatch never makes an otherwise feasible open request "
            "ineligible."
        )
    return head + tail


def build(*, applied_path=None, earnings_path=None, strategy_path=None,
          listing_path=None, chain_path=None, seed=None, now=None) -> dict:
    """Run the bandit against the live ledgers and decide. Never raises."""
    strategy_path = strategy_path if strategy_path is not None else STATE / "strategy.json"
    try:
        strategy = json.loads(Path(strategy_path).read_text(encoding="utf-8"))
    except Exception:
        strategy = {}

    try:
        bandit_result = category_bandit.select(
            applied_path=applied_path, earnings_path=earnings_path,
            strategy_path=strategy_path, listing_path=listing_path,
            chain_path=chain_path, seed=seed, now=now,
        )
    except Exception as exc:  # select() already promises not to raise; belt and braces
        bandit_result = {"status": "error", "reason": f"{type(exc).__name__}: {exc}",
                         "ranking": []}

    decision = decide(bandit_result=bandit_result, strategy=strategy)
    decision["seed"] = seed
    return decision


def record(decision: dict, *, path: Path | str | None = None,
           pass_id: str | None = None) -> None:
    """Append one compact line to the decision ledger. Best-effort, never raises.

    Compact single-line json is the repo-wide .jsonl rule (see GIG_PASS_RUNBOOK STEP -2):
    a pretty-printed object corrupts the file for every later reader.
    """
    try:
        target = Path(path) if path is not None else LEDGER
        decision = _as_dict(decision)
        order = decision.get("category_order") or []
        row = {
            "ts": time.time(),
            "pass_id": pass_id,
            # Named to match X8b's field so the two decision records join.
            "category_source": decision.get("decided_by"),
            "bandit_status": decision.get("bandit_status"),
            "reason": decision.get("reason"),
            "chosen": order[0] if order else None,
            "n_arms": len(order),
            "category_order": order,
            "arms": decision.get("arms") or [],
            "freeze_experiments": decision.get("freeze_experiments"),
            "top_arm_trials": decision.get("top_arm_trials"),
            "seed": decision.get("seed"),
            "coverage": decision.get("coverage") or {},
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        return  # bookkeeping must never cost an application


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="print the full decision")
    ap.add_argument("--applied", default=None)
    ap.add_argument("--earnings", default=None)
    ap.add_argument("--strategy", default=None)
    ap.add_argument("--listing", default=None)
    ap.add_argument("--chain", default=None)
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--pass-id", default=None,
                    help="append this decision to the ledger under the given pass id")
    ap.add_argument("--no-record", action="store_true")
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        return 0        # a prompt-builder must never fail the pass that calls it

    try:
        decision = build(
            applied_path=args.applied, earnings_path=args.earnings,
            strategy_path=args.strategy, listing_path=args.listing,
            chain_path=args.chain, seed=args.seed,
        )
        if not args.no_record:
            record(decision, path=args.ledger, pass_id=args.pass_id)
        print(json.dumps(decision, ensure_ascii=False) if args.json
              else decision["objective"])
    except Exception as exc:
        # Last line of defence: emit a usable instruction and let the pass continue.
        print(f"APPLY using strategy.json priority_categories in order "
              f"(category decision unavailable: {type(exc).__name__}).",
              file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
