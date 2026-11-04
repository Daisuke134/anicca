"""Focused deterministic tests of the P04-2 synthetic RCT teaching lab."""
import unittest
import numpy as np
from p04_2_rct_ate import (make_population, complete_random_assignment,
                          difference_of_means, normal_approx_per_arm_n, run)

class TestRCT(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = run(n=20_000, monte_carlo_reps=300)

    def test_random_assignment_is_balanced(self):
        z = complete_random_assignment(200, np.random.default_rng(15))
        self.assertEqual(int(z.sum()), 100)

    def test_assignment_reproducible(self):
        a = complete_random_assignment(100, np.random.default_rng(15))
        b = complete_random_assignment(100, np.random.default_rng(15))
        self.assertTrue(np.array_equal(a, b))

    def test_assignment_rejects_odd(self):
        with self.assertRaises(ValueError): complete_random_assignment(3, np.random.default_rng(1))

    def test_oracle_negative_effect(self):
        self.assertLess(self.data['oracle_realized_ate'], -0.07)
        self.assertGreater(self.data['oracle_realized_ate'], -0.13)

    def test_observation_misleading_positive(self):
        self.assertGreater(self.data['observational']['risk_difference'], .20)

    def test_randomization_recovers_negative(self):
        self.assertLess(self.data['randomized']['risk_difference'], -.07)
        self.assertGreater(self.data['randomized']['risk_difference'], -.13)

    def test_randomized_ci_contains_truth(self):
        r=self.data['randomized']
        self.assertLess(r['ci_95_low'], -.1)
        self.assertGreater(r['ci_95_high'], -.1)

    def test_randomized_assignment_se_correct(self):
        r=self.data['randomized']
        self.assertAlmostEqual(r['risk_difference'], r['treatment_mean']-r['control_mean'])
        self.assertGreater(r['standard_error'], 0)

    def test_itt_with_noncompliance_diluted(self):
        v=self.data['noncompliance']['itt_by_assignment']['risk_difference']
        self.assertGreater(v, -.11)
        self.assertLess(v, -.04)

    def test_as_treated_differs_from_itt(self):
        n=self.data['noncompliance']
        self.assertNotAlmostEqual(n['as_treated_selection_biased']['risk_difference'], n['itt_by_assignment']['risk_difference'],places=2)

    def test_monte_carlo_mean_near_truth(self):
        self.assertAlmostEqual(self.data['repeated_rcts']['estimated_ate_mean'], -.10, delta=.012)

    def test_monte_carlo_coverage_reasonable(self):
        self.assertGreater(self.data['repeated_rcts']['illustrative_95pct_interval_coverage_for_true_minus_0_1'],.88)
        self.assertLess(self.data['repeated_rcts']['illustrative_95pct_interval_coverage_for_true_minus_0_1'],.99)

    def test_sample_size_declines_for_bigger_effect(self):
        self.assertGreater(normal_approx_per_arm_n(.04,.06),normal_approx_per_arm_n(.5,.4))

    def test_invalid_sample_size_rejected(self):
        with self.assertRaises(ValueError):normal_approx_per_arm_n(0,.2)
        with self.assertRaises(ValueError):normal_approx_per_arm_n(.2,.2)

    def test_difference_of_means_simple_example(self):
        z=np.array([1,1,0,0])
        y=np.array([1,0,0,0])
        self.assertAlmostEqual(difference_of_means(z,y).risk_difference,.5)

    def test_invalid_assignment_rejected(self):
        with self.assertRaises(ValueError): difference_of_means(np.array([0,1,2]),np.array([1,0,1]))

    def test_simulation_reproducible(self):
        a=run(n=2000,seed=78,monte_carlo_reps=5,rep_n=100)
        b=run(n=2000,seed=78,monte_carlo_reps=5,rep_n=100)
        self.assertEqual(a['randomized'],b['randomized'])

if __name__ == '__main__':unittest.main()
