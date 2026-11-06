"""Unit checks for P04-4 synthetic RCT and mediation demonstration."""
import unittest
import numpy as np
from p04_4_heterogeneous_effects import (
    compare_means, simulate_population, subgroup_table, learn_policy, evaluate_policy,
    mediation_example, run,
)


class P044Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = simulate_population()

    def test_seed_reproducible(self):
        b = simulate_population()
        np.testing.assert_array_equal(self.data["outcome"], b["outcome"])

    def test_randomized_treatment_has_both_groups(self):
        counts = np.bincount(self.data["assignment"])
        self.assertEqual(int(sum(counts)), 24_000)
        self.assertTrue(np.all(counts > 1000))

    def test_true_subgroup_effects(self):
        expected = {(0, 0): .16, (0, 1): .10, (1, 0): -.04, (1, 1): -.10}
        for row in subgroup_table(self.data):
            self.assertAlmostEqual(row["oracle_cate"],
                                   expected[row["motivation"], row["fatigue"]], places=9)

    def test_subgroup_estimator_approximates_truth(self):
        for row in subgroup_table(self.data):
            self.assertLess(abs(row["effect"] - row["oracle_cate"]), .045)

    def test_ate_near_true_mean(self):
        result = compare_means(self.data["outcome"], self.data["assignment"])
        self.assertLess(abs(result["effect"] - np.mean(self.data["tau"])), .025)

    def test_confidence_intervals_properly_ordered(self):
        for row in subgroup_table(self.data):
            self.assertLess(row["ci95"][0], row["effect"])
            self.assertLess(row["effect"], row["ci95"][1])

    def test_policy_uses_only_train(self):
        data = self.data
        fitted = learn_policy(data)
        changed = {k: v.copy() for k, v in data.items()}
        changed["outcome"][~changed["train"]] = 1 - changed["outcome"][~changed["train"]]
        self.assertEqual(fitted, learn_policy(changed))

    def test_policy_sends_to_beneficial_strata(self):
        self.assertEqual(learn_policy(self.data),
                         {(0, 0): 1, (0, 1): 1, (1, 0): 0, (1, 1): 0})

    def test_policy_value_positive_holdout(self):
        z = evaluate_policy(self.data, learn_policy(self.data))
        self.assertGreater(z["heldout_ipw_gain"], 0)
        self.assertGreater(z["synthetic_oracle_best_four_cell_gain"],
                           z["synthetic_oracle_always_notify_gain"])

    def test_mediation_recovers_linear_paths(self):
        z = mediation_example()
        self.assertLess(abs(z["estimated_direct_effect"] - 0.12), 0.025)
        self.assertLess(abs(z["estimated_indirect_effect"] - 0.12), 0.025)
        self.assertLess(abs(z["estimated_total_effect"] - 0.24), 0.035)

    def test_small_sample_rejected(self):
        with self.assertRaises(ValueError):
            simulate_population(20)

    def test_report_not_real_human(self):
        self.assertIn("synthetic", run()["study"].lower())


if __name__ == "__main__":
    unittest.main()
