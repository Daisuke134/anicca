"""Tests for P04-6 locked synthetic policy trial and optional-peeking illustration."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from p04_6_preregistered_policy_value import (
    ALPHA, N_TOTAL, baseline_policy, execute, manager_policy, peek_demo,
    prepare, proposed_plan, run, simulate_trial, theoretical_policy_value,
    two_arm_mean_difference,
)


class PolicyValueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name)
        cls.report = run(cls.folder)
        cls.data = simulate_trial()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_plan_is_frozen_first(self):
        receipt = json.loads((self.folder / "P04-6_PLAN_FREEZE_RECEIPT.json").read_text())
        self.assertTrue(receipt["policy_frozen_before_outcomes"])
        self.assertTrue(receipt["primary_outcome_frozen_before_outcomes"])

    def test_plan_contains_single_primary(self):
        plan = proposed_plan()
        self.assertIn("net_utility", plan["primary_outcome"])
        self.assertEqual(plan["two_sided_alpha"], ALPHA)

    def test_data_are_synthetic_only(self):
        self.assertFalse(self.report["real_user_trial"])
        self.assertFalse(self.report["external_preregistration"])

    def test_equal_action_set_and_inputs(self):
        plan = proposed_plan()
        self.assertEqual(len(plan["shared_action_set"]), 2)
        self.assertEqual(plan["shared_available_features"], ["motivation_pre", "fatigue_pre"])

    def test_plan_change_rejected(self):
        planpath = self.folder / "P04-6_PREANALYSIS_PLAN_SYNTHETIC.json"
        original = planpath.read_bytes()
        try:
            planpath.write_bytes(original + b" ")
            with self.assertRaises(ValueError):
                execute(self.folder)
        finally:
            planpath.write_bytes(original)

    def test_policy_rules_differ_only_low_motivation_tired(self):
        x = np.array([0, 0, 1, 1])
        f = np.array([0, 1, 0, 1])
        self.assertEqual(manager_policy(x, f).tolist(), [1, 1, 0, 0])
        self.assertEqual(baseline_policy(x, f).tolist(), [1, 0, 0, 0])

    def test_seed_reproduces_outcomes(self):
        other = simulate_trial()
        np.testing.assert_array_equal(self.data["outcome"], other["outcome"])

    def test_randomization_size(self):
        self.assertEqual(len(self.data["outcome"]), N_TOTAL)
        self.assertTrue(np.all(np.bincount(self.data["randomized_arm"]) > 19_000))

    def test_true_value_difference_two_points(self):
        theo = theoretical_policy_value()
        self.assertAlmostEqual(theo["expected_incremental_net_utility"], .02, places=9)

    def test_estimated_policy_value_near_theory(self):
        delta = self.report["primary_pre_specified_net_utility_contrast"]["difference"]
        self.assertLess(abs(delta - .02), .017)

    def test_primary_95ci_valid(self):
        r = self.report["primary_pre_specified_net_utility_contrast"]
        self.assertLess(r["ci95"][0], r["difference"])
        self.assertLess(r["difference"], r["ci95"][1])

    def test_primary_pvalue_sensible(self):
        r = self.report["primary_pre_specified_net_utility_contrast"]
        self.assertLess(r["p_two_sided"], ALPHA)
        self.assertGreater(r["difference"], 0)

    def test_diagnostic_shows_more_notifications(self):
        r = self.report["secondary_notification_rate_contrast"]
        self.assertGreater(r["difference"], .20)
        self.assertLess(r["difference"], .30)

    def test_one_notification_max(self):
        self.assertTrue(np.isin(self.data["notify_sent"], [0, 1]).all())

    def test_primary_equals_completion_minus_cost(self):
        raw = self.report["secondary_completion_contrast"]["difference"]
        notify = self.report["secondary_notification_rate_contrast"]["difference"]
        self.assertAlmostEqual(
            self.report["primary_pre_specified_net_utility_contrast"]["difference"],
            raw - .02 * notify, places=10)

    def test_aa_peeking_inflates_errors(self):
        result = self.report["separate_aa_optional_peeking_demo"]
        self.assertLess(result["fixed_single_test_false_positive_rate"], .09)
        self.assertGreater(result["naive_peeking_any_look_false_positive_rate"],
                           result["fixed_single_test_false_positive_rate"] + .03)


if __name__ == "__main__":
    unittest.main()
