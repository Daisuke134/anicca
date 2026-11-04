"""Reconstructed 14 educational tests for P04-1 (not original historical test file)."""
import unittest
from p04_1_causal_vs_observational import analytical, experiment


class ObservationVsInterventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = analytical()
        cls.e = experiment(200_000, 20261104)

    def test_01_theory_treated_observation(self):
        self.assertAlmostEqual(self.a['observation']['treated_rate'], .58)

    def test_02_theory_control_observation(self):
        self.assertAlmostEqual(self.a['observation']['untreated_rate'], .32)

    def test_03_theory_observed_difference(self):
        self.assertAlmostEqual(self.a['observation']['observational_difference'], .26)

    def test_04_theory_intervene_one(self):
        self.assertAlmostEqual(self.a['intervention']['do_treated_rate'], .40)

    def test_05_theory_intervene_zero(self):
        self.assertAlmostEqual(self.a['intervention']['do_untreated_rate'], .50)

    def test_06_theory_ate(self):
        self.assertAlmostEqual(self.a['intervention']['average_causal_effect'], -.10)

    def test_07_theory_within_strata_zero(self):
        self.assertAlmostEqual(self.a['by_intent']['0']['causal_effect'], -.10)

    def test_08_theory_within_strata_one(self):
        self.assertAlmostEqual(self.a['by_intent']['1']['causal_effect'], -.10)

    def test_09_sample_size(self):
        self.assertEqual(self.e['n'], 200_000)

    def test_10_sample_observational_positive(self):
        self.assertGreater(self.e['observational_difference'], .24)

    def test_11_randomized_negative(self):
        self.assertLess(self.e['randomized_difference'], -.08)

    def test_12_adjusted_negative(self):
        self.assertLess(self.e['standardized_difference'], -.08)

    def test_13_reproducible_seed(self):
        self.assertEqual(self.e, experiment(200_000, 20261104))

    def test_14_bad_n_rejected(self):
        with self.assertRaises(ValueError):
            experiment(20)


if __name__=='__main__':
    unittest.main()
