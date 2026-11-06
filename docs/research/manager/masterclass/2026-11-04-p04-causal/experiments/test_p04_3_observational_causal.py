"""Offline unit tests for P04-3; no production systems accessed."""
import unittest
import numpy as np
from p04_3_observational_causal import (
    simulate, naive_difference, standardize, outcome_regression,
    estimate_propensity, validate_overlap, ipw_hajek, predict_outcomes,
    aipw, exact_match_att, did, bootstrap_standardized_ci, report,
)


class CausalIdentificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = simulate(n=80_000, seed=20261104)
        cls.e = estimate_propensity(cls.d.a, cls.d.u)

    def test_01_all_lengths_match(self):
        self.assertEqual(len(self.d.y), 80_000)
        self.assertEqual(len(self.d.a), len(self.d.u))

    def test_02_binary_features(self):
        for ar in (self.d.a, self.d.u, self.d.y, self.d.y0, self.d.y1):
            self.assertTrue(set(np.unique(ar)).issubset({0, 1}))

    def test_03_same_seed_reproduces(self):
        d2 = simulate(80_000, seed=20261104)
        np.testing.assert_array_equal(self.d.y, d2.y)

    def test_04_different_seed_changes(self):
        d2 = simulate(80_000, seed=12)
        self.assertFalse(np.array_equal(self.d.y, d2.y))

    def test_05_observed_outcome_consistency(self):
        np.testing.assert_array_equal(self.d.y, np.where(self.d.a, self.d.y1, self.d.y0))

    def test_06_oracle_ate_close_to_minus_ten_points(self):
        self.assertLess(abs(np.mean(self.d.y1 - self.d.y0) + 0.10), 0.009)

    def test_07_naive_has_wrong_sign(self):
        self.assertGreater(naive_difference(self.d.y, self.d.a), .23)

    def test_08_standardization_close_to_true(self):
        self.assertLess(abs(standardize(self.d.y,self.d.a,self.d.u) + .10),.02)

    def test_09_gcomp_equals_stratification(self):
        self.assertAlmostEqual(outcome_regression(self.d.y,self.d.a,self.d.u),
                               standardize(self.d.y,self.d.a,self.d.u),places=10)

    def test_10_propensity_in_range(self):
        self.assertGreater(self.e.min(), 0.17)
        self.assertLess(self.e.max(), 0.83)

    def test_11_ipw_close_to_true(self):
        self.assertLess(abs(ipw_hajek(self.d.y,self.d.a,self.e) + .10),.02)

    def test_12_aipw_close_to_true(self):
        m0,m1=predict_outcomes(self.d.y,self.d.a,self.d.u)
        self.assertLess(abs(aipw(self.d.y,self.d.a,self.e,m0,m1)+.10),.02)

    def test_13_aipw_correct_outcome_wrong_propensity(self):
        m0,m1=predict_outcomes(self.d.y,self.d.a,self.d.u)
        wrong_e=np.repeat(.5,len(self.d.y))
        self.assertLess(abs(aipw(self.d.y,self.d.a,wrong_e,m0,m1)+.10),.02)

    def test_14_aipw_correct_propensity_wrong_outcomes(self):
        wrong_m0=np.repeat(.5,len(self.d.y))
        wrong_m1=np.repeat(.5,len(self.d.y))
        self.assertLess(abs(aipw(self.d.y,self.d.a,self.e,wrong_m0,wrong_m1)+.10),.02)

    def test_15_matching_att_close_to_true(self):
        self.assertLess(abs(exact_match_att(self.d.y,self.d.a,self.d.u)+.10),.025)

    def test_16_positivity_detects_zero(self):
        with self.assertRaises(ValueError): validate_overlap(np.array([0., .5]))

    def test_17_positivity_detects_one(self):
        with self.assertRaises(ValueError): validate_overlap(np.array([.5, 1.]))

    def test_18_positivity_detects_near_zero(self):
        with self.assertRaises(ValueError): validate_overlap(np.array([.02,.98]),threshold=.05)

    def test_19_strata_empty_raises(self):
        with self.assertRaises(ValueError): standardize(np.array([0,1]),np.array([0,1]),np.array([0,1]))

    def test_20_missing_group_raises(self):
        with self.assertRaises(ValueError): naive_difference(np.array([0,1]), np.array([1,1]))

    def test_21_did_formula(self):
        self.assertAlmostEqual(did(.30,.38,.20,.25),.03)

    def test_22_did_rejects_invalid_rate(self):
        with self.assertRaises(ValueError):did(-1,.38,.20,.25)

    def test_23_bootstrap_interval_contains_sample_estimate(self):
        ci=bootstrap_standardized_ci(self.d,replicates=100,seed=11)
        point = standardize(self.d.y, self.d.a, self.d.u)
        self.assertLess(ci[0], point)
        self.assertGreater(ci[1], point)

    def test_24_report_exposes_assumptions(self):
        r=report(n=1000,seed=3,bootstrap_reps=50)
        self.assertIn("synthetic",r["dataset"])
        self.assertEqual(r["theoretical_ATE"],-.1)

    def test_25_tiny_sample_rejected(self):
        with self.assertRaises(ValueError): simulate(n=2)

    def test_26_no_infinite_ipw(self):
        with self.assertRaises(ValueError):ipw_hajek(np.array([0,1]),np.array([0,1]),np.array([0.5,0.0]))


if __name__=="__main__":
    unittest.main()
