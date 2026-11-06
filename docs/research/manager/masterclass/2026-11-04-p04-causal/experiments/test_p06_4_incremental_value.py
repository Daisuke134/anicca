"""P06-4 tests: real SciPy Welch calculation on completely synthetic ledger."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
import numpy as np

from p06_4_incremental_value import (
    ALPHA,CURRENCY,N,MAX_ADVERSE_COMPLAINT_INCREASE,
    plan,prefreeze,generate,mean_diff,decision,real_world_proof_outcome,run,checksum,
)


class P064ProfitAndGuardrailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=TemporaryDirectory()
        cls.out=Path(cls.tmp.name)
        cls.r=run(cls.out)
        cls.toy=generate()

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_01_plan_is_synthetic_not_preregistered(self):
        self.assertFalse(plan()["preregistered_externally"])
        self.assertFalse(self.r["real_financial_outcome"]["can_ship"])

    def test_02_no_real_ledger(self):
        self.assertFalse(plan()["external_payment_receipts_present"])

    def test_03_currency_yen(self):
        self.assertEqual(self.r["currency"],"JPY")

    def test_04_trial_has_fixed_n(self):
        self.assertEqual(len(self.toy["arm"]),N)
        self.assertEqual(N,30000)

    def test_05_purchase_only_one_per_unit(self):
        self.assertTrue(set(np.unique(self.toy["paid_purchase"]))<={0,1})

    def test_06_refund_requires_paid_purchase(self):
        self.assertTrue(np.all(self.toy["refunded_purchase"]<=
                               self.toy["paid_purchase"]))

    def test_07_recognized_less_than_or_equal_gross(self):
        self.assertTrue(np.all(self.toy["recognized_revenue"]<=
                               self.toy["gross_revenue"]))

    def test_08_revenue_minus_variable_cost_exact(self):
        np.testing.assert_allclose(
            self.toy["recognized_revenue"]-self.toy["variable_cost"],
            self.toy["net_contribution"])

    def test_09_reproducibility(self):
        other=generate()
        np.testing.assert_array_equal(self.toy["net_contribution"],
                                      other["net_contribution"])

    def test_10_wrong_tiny_population_rejected(self):
        with self.assertRaises(ValueError):generate(n=5)

    def test_11_wrong_huge_population_rejected(self):
        with self.assertRaises(ValueError):generate(n=300001)

    def test_12_welch_profit_ci_contains_mean_diff(self):
        r=self.r["metrics"]["net_contribution"]
        self.assertLess(r["ci95"][0],r["diff"])
        self.assertLess(r["diff"],r["ci95"][1])

    def test_13_synthetic_profit_positive(self):
        self.assertGreater(self.r["metrics"]["net_contribution"]["ci95"][0],0)

    def test_14_synthetic_refunds_reported(self):
        self.assertIn("refund_yen",self.r["metrics"])
        self.assertGreater(self.r["metrics"]["refund_yen"]["manager_mean"],0)

    def test_15_harm_worsens(self):
        r=self.r["metrics"]["complaint"]
        self.assertGreater(r["ci95"][0],MAX_ADVERSE_COMPLAINT_INCREASE)

    def test_16_no_ship_when_profit_positive_but_harm(self):
        r=self.r["toy_strict_ship_gate"]
        self.assertEqual(r["decision"],"DO_NOT_SHIP")
        self.assertTrue(r["positive_primary_CI"])
        self.assertFalse(r["guardrail_upper_below_max"])

    def test_17_missing_real_receipt_not_assumed_zero(self):
        r=real_world_proof_outcome()
        self.assertIsNone(r["real_incremental_contribution_yen"])
        self.assertIsNone(r["refunds_yen"])

    def test_18_fake_real_receipts_rejected(self):
        with self.assertRaises(ValueError):
            real_world_proof_outcome(official_receipts={"self_assertion":"paid"})

    def test_19_good_metric_still_no_field_proof(self):
        result=decision(
            {"ci95":[.01,.20]},
            {"ci95":[-.002,.002]},
            {"invalid_srm_at_p_lt_0_001":False},
            independent_outcomes=False)
        self.assertEqual(result["decision"],"DO_NOT_SHIP")
        self.assertIn("no_independent_real_benefit_receipt",result["reason"])

    def test_20_adverse_guardrail_even_when_receipts_claimed(self):
        result=decision(
            {"ci95":[.01,.20]},
            {"ci95":[.007,.015]},
            {"invalid_srm_at_p_lt_0_001":False},
            independent_outcomes=True)
        self.assertEqual(result["decision"],"DO_NOT_SHIP")

    def test_21_invalid_srm_blocks_profit(self):
        result=decision(
            {"ci95":[.01,.20]},
            {"ci95":[-.002,.002]},
            {"invalid_srm_at_p_lt_0_001":True},
            independent_outcomes=True)
        self.assertIn("invalid_sample_ratio",result["reason"])

    def test_22_strict_gate_only_when_every_condition_passes(self):
        result=decision(
            {"ci95":[.01,.20]},
            {"ci95":[-.002,.002]},
            {"invalid_srm_at_p_lt_0_001":False},
            independent_outcomes=True)
        self.assertEqual(result["decision"],"ELIGIBLE_FOR_REVIEW")

    def test_23_frozen_plan_stored(self):
        r=json.loads((self.out/"P06-4_PREANALYSIS_FREEZE.json").read_text())
        self.assertEqual(r["sha256"],
                         checksum((self.out/"P06-4_PREANALYSIS_SYNTHETIC.json").read_bytes()))

    def test_24_research_excludes_tax_and_fixed_costs(self):
        self.assertTrue(self.r["fixed_cost_and_tax_not_included"])

    def test_25_total_contribution_uses_randomized_assignment_mean(self):
        r=self.r["metrics"]["net_contribution"]
        self.assertEqual(r["n_manager"]+r["n_baseline"],N)

    def test_26_revenue_and_refunds_not_just_clicks(self):
        self.assertIn("recognized_revenue",self.r["metrics"])
        self.assertIn("refund_yen",self.r["metrics"])
        self.assertIn("variable_cost",self.r["metrics"])

    def test_27_no_real_customer_harm_claim(self):
        self.assertFalse(plan()["actual_human_harm_outcomes"])

    def test_28_no_live_provider_action(self):
        self.assertTrue(self.r["no_real_intervention_performed"])


if __name__=="__main__":
    unittest.main()
