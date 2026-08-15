"""The apply lane's category order comes from measured reward. Run: python3 tests/test_b2_objective.py

Why this file exists (X8c): category_bandit.py has computed a Thompson-sampling ranking
since a11cc68 and NOTHING READ IT. The apply lane still took its order from
strategy.json's priority_categories, which is LLM hypothesis. A number nobody consumes
is not a decision. These tests pin the wire: bandit ranking -> b2_objective -> the apply
lane's prompt and passprep's JSON, plus the four things that wire must never break.

The four invariants, each of which was a live hazard before it was a test:

  fail-safe      A bandit that errors, or has too little data, must fall back to
                 priority_categories. The bandit failing must never be the reason the
                 loop stops applying -- that is closing the money entrance by hand.
  skip authority skip_categories encode capability and ethics ("cannot be physically
                 present", "violates ToS"). They are not performance claims. No reward,
                 however high, may resurrect one.
  exploration    The order handed downstream is the FULL ranking, never a top-N slice.
                 A slice would let a trials=0 arm fall off the list permanently, and a
                 category that is never tried can never be measured.
  confounding    Thompson sampling moves the category dimension while the LLM
                 experiments[] loop moves wording/price/templates. Both moving at once
                 makes every reward unattributable. Exactly one dimension holds the
                 floor at a time; which one is computed, not chosen.

Spec: docs/loop-engineering/28-gig-category-bandit-spec.md, docs/loop-engineering/26-gig-loop-asis-tobe-plan.md X8c row.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import b2_objective  # noqa: E402

SKIPPED_LABEL = "イラスト/VTuber/Live2D/キャラデザ (art skill required)"
SKIPPED_TOKEN = "イラスト"


def ranking(*pairs):
    """[(arm, sample, trials), ...] -> a bandit-shaped ranking, already sample-sorted."""
    rows = [
        {"arm": arm, "sample": sample, "posterior_mean": sample, "alpha": 1.0,
         "beta": 1.0, "trials": trials, "reward_sum": 0.0, "in_flight": 0,
         "paid_trials": 0, "stages": {}}
        for arm, sample, trials in pairs
    ]
    rows.sort(key=lambda r: r["sample"], reverse=True)
    return rows


def ok_result(*pairs):
    return {"status": "ok", "decided_by": "thompson_sampling", "prior_mean": 0.05,
            "prior_strength": 2.0, "no_positive_reward_observed": False, "seed": 1,
            "coverage": {"resolved_trials": 20}, "ranking": ranking(*pairs)}


STRATEGY = {
    "priority_categories": ["AI活用支援/AI研修/Claude活用", "PPT/スライド", "文字起こし"],
    "skip_categories": [SKIPPED_LABEL],
}


class DecisionTest(unittest.TestCase):
    def test_bandit_order_becomes_the_category_order(self):
        """The whole point of X8c: the measured ranking is what the lane is told."""
        decision = b2_objective.decide(
            bandit_result=ok_result(("PPT/スライド", 0.9, 3), ("文字起こし", 0.2, 5)),
            strategy=STRATEGY)
        self.assertEqual(decision["decided_by"], "thompson_sampling")
        self.assertEqual(decision["category_order"], ["PPT/スライド", "文字起こし"])

    def test_objective_sentence_names_the_measured_top_category(self):
        decision = b2_objective.decide(
            bandit_result=ok_result(("PPT/スライド", 0.9, 3), ("文字起こし", 0.2, 5)),
            strategy=STRATEGY)
        self.assertIn("PPT/スライド", decision["objective"])

    def test_decision_carries_the_numbers_that_produced_it(self):
        """Auditability: 'was the bandit right' must be answerable months later."""
        decision = b2_objective.decide(
            bandit_result=ok_result(("PPT/スライド", 0.9, 3), ("文字起こし", 0.2, 5)),
            strategy=STRATEGY)
        top = decision["arms"][0]
        self.assertEqual(top["arm"], "PPT/スライド")
        for field in ("sample", "posterior_mean", "trials"):
            self.assertIn(field, top)


class FailSafeTest(unittest.TestCase):
    """A broken bandit must cost the loop nothing but its ordering."""

    def test_insufficient_data_falls_back_to_priority_categories(self):
        result = {"status": "insufficient_data", "decided_by": "fallback",
                  "reason": "3 resolved trials < min_trials=8",
                  "ranking": [{"arm": c, "trials": 0}
                              for c in STRATEGY["priority_categories"]]}
        decision = b2_objective.decide(bandit_result=result, strategy=STRATEGY)
        self.assertEqual(decision["decided_by"], "fallback")
        self.assertEqual(decision["category_order"], STRATEGY["priority_categories"])

    def test_bandit_error_falls_back_and_still_names_categories(self):
        result = {"status": "error", "decided_by": "fallback", "reason": "ValueError: x",
                  "ranking": [{"arm": c, "trials": 0}
                              for c in STRATEGY["priority_categories"]]}
        decision = b2_objective.decide(bandit_result=result, strategy=STRATEGY)
        self.assertEqual(decision["decided_by"], "fallback")
        self.assertTrue(decision["category_order"])

    def test_empty_bandit_ranking_still_yields_priority_categories(self):
        """strategy_unavailable gives an empty ranking; the lane must still have a list."""
        decision = b2_objective.decide(
            bandit_result={"status": "strategy_unavailable", "ranking": []},
            strategy=STRATEGY)
        self.assertEqual(decision["category_order"], STRATEGY["priority_categories"])

    def test_decide_never_raises_on_garbage(self):
        for junk in (None, {}, {"ranking": None}, {"status": "ok", "ranking": "nope"}):
            decision = b2_objective.decide(bandit_result=junk, strategy=STRATEGY)
            self.assertIsInstance(decision["category_order"], list)
            self.assertEqual(decision["decided_by"], "fallback")

    def test_objective_is_non_empty_even_with_no_strategy_at_all(self):
        decision = b2_objective.decide(bandit_result=None, strategy={})
        self.assertTrue(decision["objective"].strip())


class SkipAuthorityTest(unittest.TestCase):
    """skip_categories are capability/ethics limits. Reward does not outrank them."""

    def test_a_skipped_category_never_enters_the_order(self):
        decision = b2_objective.decide(
            bandit_result=ok_result((SKIPPED_TOKEN, 0.99, 9), ("PPT/スライド", 0.1, 3)),
            strategy=STRATEGY)
        self.assertNotIn(SKIPPED_TOKEN, decision["category_order"])
        self.assertEqual(decision["category_order"][0], "PPT/スライド")

    def test_a_skipped_category_is_dropped_on_the_fallback_path_too(self):
        strategy = dict(STRATEGY, priority_categories=[SKIPPED_TOKEN, "PPT/スライド"])
        decision = b2_objective.decide(
            bandit_result={"status": "insufficient_data",
                           "ranking": [{"arm": SKIPPED_TOKEN, "trials": 0},
                                       {"arm": "PPT/スライド", "trials": 0}]},
            strategy=strategy)
        self.assertNotIn(SKIPPED_TOKEN, decision["category_order"])

    def test_the_objective_sentence_never_advertises_a_skipped_category(self):
        decision = b2_objective.decide(
            bandit_result=ok_result((SKIPPED_TOKEN, 0.99, 9), ("PPT/スライド", 0.1, 3)),
            strategy=STRATEGY)
        self.assertNotIn(SKIPPED_TOKEN, decision["objective"])


class ExplorationTest(unittest.TestCase):
    """A category that is never offered can never be measured."""

    def test_cold_start_arm_survives_into_the_order(self):
        decision = b2_objective.decide(
            bandit_result=ok_result(("PPT/スライド", 0.9, 12), ("新カテゴリ", 0.05, 0)),
            strategy=STRATEGY)
        self.assertIn("新カテゴリ", decision["category_order"])

    def test_a_cold_start_arm_can_lead_the_order(self):
        decision = b2_objective.decide(
            bandit_result=ok_result(("PPT/スライド", 0.1, 12), ("新カテゴリ", 0.9, 0)),
            strategy=STRATEGY)
        self.assertEqual(decision["category_order"][0], "新カテゴリ")

    def test_the_order_is_the_full_ranking_not_a_top_n_slice(self):
        """A slice would starve the tail forever; the tail is where new arms live."""
        pairs = [(f"cat{i}", 1.0 - i / 100.0, 0) for i in range(30)]
        decision = b2_objective.decide(bandit_result=ok_result(*pairs), strategy=STRATEGY)
        self.assertEqual(len(decision["category_order"]), 30)


class ConfoundingFreezeTest(unittest.TestCase):
    """Exactly one dimension moves at a time, and the switch is computed."""

    def test_bandit_steering_freezes_the_wording_experiments(self):
        decision = b2_objective.decide(
            bandit_result=ok_result(("PPT/スライド", 0.9, 3), ("文字起こし", 0.2, 5)),
            strategy=STRATEGY)
        self.assertTrue(decision["freeze_experiments"])
        self.assertTrue(decision["freeze_release_condition"])

    def test_freeze_lifts_once_the_top_arm_has_its_own_evidence(self):
        decision = b2_objective.decide(
            bandit_result=ok_result(("PPT/スライド", 0.9,
                                     b2_objective.FREEZE_RELEASE_ARM_TRIALS),
                                    ("文字起こし", 0.2, 5)),
            strategy=STRATEGY)
        self.assertFalse(decision["freeze_experiments"])

    def test_fallback_leaves_the_experiment_floor_open(self):
        """If the bandit is not steering, it has no claim on the floor."""
        decision = b2_objective.decide(
            bandit_result={"status": "insufficient_data",
                           "ranking": [{"arm": "PPT/スライド", "trials": 0}]},
            strategy=STRATEGY)
        self.assertFalse(decision["freeze_experiments"])

    def test_frozen_objective_tells_the_lane_to_hold_wording_still(self):
        decision = b2_objective.decide(
            bandit_result=ok_result(("PPT/スライド", 0.9, 3)), strategy=STRATEGY)
        self.assertIn("experiment", decision["objective"].lower())

    def test_active_isolated_experiment_freezes_category_order_instead(self):
        strategy = dict(STRATEGY, experiments=[{
            "id": "proposal-v2",
            "status": "active",
            "frozen_category_order": ["文字起こし", "PPT/スライド"],
        }])
        decision = b2_objective.decide(
            bandit_result=ok_result(
                ("AI活用支援/AI研修/Claude活用", 0.99, 0),
                ("PPT/スライド", 0.1, 3),
            ),
            strategy=strategy,
        )
        self.assertEqual(decision["decided_by"], "experiment_epoch")
        self.assertEqual(
            decision["category_order"], ["文字起こし", "PPT/スライド"]
        )
        self.assertTrue(decision["freeze_experiments"])
        self.assertIn("proposal-v2", decision["objective"])


class LedgerTest(unittest.TestCase):
    """X8b's category_source lesson: record which authority chose, and on what numbers."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.path = self.root / "category-decisions.jsonl"

    def test_record_appends_one_compact_line(self):
        decision = b2_objective.decide(
            bandit_result=ok_result(("PPT/スライド", 0.9, 3)), strategy=STRATEGY)
        b2_objective.record(decision, path=self.path, pass_id="pass-1")
        b2_objective.record(decision, path=self.path, pass_id="pass-2")
        lines = self.path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        row = json.loads(lines[0])
        self.assertEqual(row["pass_id"], "pass-1")

    def test_recorded_row_can_answer_was_the_bandit_right(self):
        decision = b2_objective.decide(
            bandit_result=ok_result(("PPT/スライド", 0.9, 3), ("文字起こし", 0.2, 5)),
            strategy=STRATEGY)
        b2_objective.record(decision, path=self.path, pass_id="pass-1")
        row = json.loads(self.path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["category_source"], "thompson_sampling")
        self.assertEqual(row["chosen"], "PPT/スライド")
        self.assertEqual(row["arms"][0]["arm"], "PPT/スライド")
        self.assertIn("sample", row["arms"][0])
        self.assertIn("ts", row)
        self.assertIn("freeze_experiments", row)

    def test_record_never_raises_when_the_ledger_is_unwritable(self):
        """Bookkeeping must not be able to stop an application."""
        decision = b2_objective.decide(bandit_result=None, strategy=STRATEGY)
        b2_objective.record(decision, path=self.root / "no" / "such" / "dir.jsonl",
                            pass_id="p")


class CliTest(unittest.TestCase):
    def test_cli_exits_zero_with_every_input_missing(self):
        root = Path(tempfile.mkdtemp())
        rc = b2_objective.main([
            "--applied", str(root / "a.jsonl"), "--earnings", str(root / "e.jsonl"),
            "--strategy", str(root / "s.json"), "--ledger", str(root / "l.jsonl"),
        ])
        self.assertEqual(rc, 0)

    def test_json_mode_exposes_the_order_and_the_freeze(self):
        root = Path(tempfile.mkdtemp())
        (root / "s.json").write_text(json.dumps(STRATEGY, ensure_ascii=False),
                                     encoding="utf-8")
        (root / "a.jsonl").write_text("", encoding="utf-8")
        decision = b2_objective.build(
            applied_path=root / "a.jsonl", earnings_path=root / "e.jsonl",
            strategy_path=root / "s.json", seed=1)
        self.assertIn("category_order", decision)
        self.assertIn("freeze_experiments", decision)
        self.assertEqual(decision["decided_by"], "fallback")   # no trials yet


if __name__ == "__main__":
    unittest.main()
