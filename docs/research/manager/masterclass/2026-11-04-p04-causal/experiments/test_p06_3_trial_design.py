"""P06-3 tests of actual statsmodels/scipy power + A/A validity."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from p06_3_trial_design import (
    AA_REPLICATIONS, ALPHA, BASE_RATE, MDE, POWER, EARLY_LOOKS,
    plan,write_plan,sample_size,srm_check,aa_peeking_demo,sha,run,
)


class P063ExperimentDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=TemporaryDirectory()
        cls.path=Path(cls.tmp.name)
        cls.result=run(cls.path)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_01_local_prereg_not_external(self):
        self.assertFalse(plan()["external_preregistration"])
        self.assertFalse(self.result["real_trial_registered"])

    def test_02_primary_and_target_fixed(self):
        self.assertEqual(plan()["primary"],
            "found_correct_official_link_within_prespecified_seconds")
        self.assertEqual(plan()["minimum_detectable_absolute_improvement"],0.03)

    def test_03_official_power_lib_used(self):
        self.assertIn("statsmodels",sample_size()["library"])

    def test_04_power_fixed_nperarm(self):
        self.assertEqual(self.result["power"]["fixed_horizon_n_per_arm"],3395)

    def test_05_power_four_looks_more_expensive(self):
        x=self.result["power"]
        self.assertEqual(x["bonferroni_n_per_arm_at_80pct_power"],4824)
        self.assertGreater(x["bonferroni_total_recruited_for_15pct_loss"],
                           x["fixed_horizon_total_recruited_for_15pct_loss"])

    def test_06_attrition_budget_not_synthetic_users_observed(self):
        p=self.result["power"]
        self.assertEqual(p["fixed_horizon_total_recruited_for_15pct_loss"],7990)
        self.assertTrue(p["cannot_start_real_trial"])

    def test_07_aa_seed_reproducible(self):
        self.assertEqual(aa_peeking_demo(),self.result["AA_early_stopping"])

    def test_08_aa_four_looks_increases_false_positive(self):
        a=self.result["AA_early_stopping"]
        self.assertGreater(a["naive_any_of_four_looks_false_positive"],.08)
        self.assertGreater(a["naive_any_of_four_looks_false_positive"],
                           a["only_last_look_false_positive"])

    def test_09_bonferroni_controls_false_positive(self):
        a=self.result["AA_early_stopping"]
        self.assertLess(a["bonferroni_any_of_four_looks_false_positive"],.06)
        self.assertLess(a["bonferroni_any_of_four_looks_false_positive"],
                        a["naive_any_of_four_looks_false_positive"])

    def test_10_no_fabricated_early_msprt_claim(self):
        self.assertIn("not mSPRT",self.result["AA_early_stopping"]["caution"])

    def test_11_good_allocation_not_srm(self):
        self.assertFalse(srm_check(505,495)["invalid_srm_at_p_lt_0_001"])

    def test_12_bad_allocation_flagged(self):
        self.assertTrue(srm_check(560,440)["invalid_srm_at_p_lt_0_001"])

    def test_13_zero_traffic_rejected(self):
        with self.assertRaises(ValueError):srm_check(0,0)

    def test_14_negative_traffic_rejected(self):
        with self.assertRaises(ValueError):srm_check(-1,100)

    def test_15_invalid_expected_fraction_rejected(self):
        with self.assertRaises(ValueError):srm_check(5,5,expected_control_share=1)

    def test_16_hash_frozen_before_aa(self):
        frozen=json.loads((self.path/"P06-3_PLAN_FREEZE_SYNTHETIC.json").read_text())
        self.assertEqual(frozen["plan_sha256"],
                         sha((self.path/"P06-3_PREANALYSIS_DESIGN_SYNTHETIC.json").read_bytes()))

    def test_17_changing_frozen_plan_breaks_digest(self):
        f=self.path/"P06-3_PREANALYSIS_DESIGN_SYNTHETIC.json"
        original=f.read_bytes()
        try:
            f.write_bytes(original+b" ")
            self.assertNotEqual(sha(f.read_bytes()),self.result["plan_sha256"])
        finally:
            f.write_bytes(original)

    def test_18_multiple_looks_denominator(self):
        self.assertEqual(len(EARLY_LOOKS),4)
        self.assertEqual(AA_REPLICATIONS,self.result["AA_early_stopping"]["n_repetitions"])

    def test_19_alpha_is_two_sided(self):
        self.assertEqual(plan()["analysis"],
                        "two-sided two-independent-proportion z approximation, one fixed final analysis")

    def test_20_actual_real_participants_zero(self):
        self.assertEqual(self.result["actual_real_participants"],0)

    def test_21_missing_independent_outcome_is_not_zero(self):
        self.assertFalse(plan()["independent_real_outcomes_available"])


if __name__=="__main__":
    unittest.main()
