"""Software fixtures only; no real participant row is committed."""
import unittest
from rct_bench_real_outcome_eval import two_arm_summary, numeric, TRIALS

class PinnedRCTTests(unittest.TestCase):
    def test_catalog_tracks_actual_outcomes(self):
        self.assertIn(103,TRIALS)
        self.assertEqual(TRIALS[103]["outcomes"],["YP_qaly_90d_observed"])
        self.assertIn(116,TRIALS)

    def test_missing_values(self):
        self.assertIsNone(numeric("NA"))
        self.assertIsNone(numeric(float("nan")))
        self.assertEqual(numeric("0.5"),0.5)

    def test_unadjusted_difference_and_missingness(self):
        rows=[
            {"Treatment":"Control","YP_y":"1"},
            {"Treatment":"Control","YP_y":"3"},
            {"Treatment":"Treated","YP_y":"4"},
            {"Treatment":"Treated","YP_y":"6"},
            {"Treatment":"Treated","YP_y":"NA"}
        ]
        r=two_arm_summary(rows,"Control","Treated","YP_y",n_boot=120)
        self.assertEqual(r["arm1_minus_arm0"],3.0)
        self.assertEqual(r["missing_arm1"],1)
        self.assertFalse(r["individual_effects_known"])
        self.assertFalse(r["manager_intervention_efficacy_measured"])

    def test_invalid_arm_rejected(self):
        with self.assertRaises(ValueError):
            two_arm_summary([{"Treatment":"other","YP_y":"2"}]*4,"A","B","YP_y",n_boot=120)

    def test_nonprimary_rejected(self):
        with self.assertRaises(ValueError):
            two_arm_summary([{"Treatment":"A","X_y":"1"}]*4,"A","B","X_y",n_boot=120)

if __name__=="__main__":
    unittest.main()
