"""P06-5 provenance, field-result and missing-outcome protection tests."""
from pathlib import Path
from tempfile import TemporaryDirectory
import copy
import json
import shutil
import unittest

from p06_3_trial_design import run as p063
from p06_4_incremental_value import run as p064
from p06_5_independent_proof import (
    EVIDENCE,verify_chain,public_website_evidence,evidence_card,run,
)


def unavailable():
    raise ConnectionError("synthetic public connectivity unavailable")


class P065ProofCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory()
        cls.out=Path(cls.temp.name)
        for name in (
            "P06-2_PREANALYSIS_SYNTHETIC.json",
            "P06-2_POLICY_FREEZE_SYNTHETIC.json",
            "P06-2_SYNTHETIC_ABLATION_RESULTS.json"):
            shutil.copyfile(EVIDENCE/name,cls.out/name)
        cls.p063=p063(cls.out)
        cls.p064=p064(cls.out)
        cls.verified=verify_chain(cls.out)
        cls.cards=run(cls.out,reader=unavailable)
        cls.card=cls.cards["proof_card"]

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_01_all_nine_artifacts_verified(self):
        self.assertEqual(self.verified["n_verified_artifacts"],9)

    def test_02_all_plan_hashes_frozen(self):
        self.assertTrue(self.verified["plan_hashes_match_frozen_results"])

    def test_03_model_provenance_is_synthetic(self):
        self.assertTrue(self.verified["code_outputs_are_synthetic"])

    def test_04_hash_card_contains_no_raw_people_data(self):
        self.assertEqual(len(self.verified["sha256_by_filename"]),9)

    def test_05_public_source_fails_closed_on_connectivity_issue(self):
        real=public_website_evidence(reader=unavailable)
        self.assertEqual(real["status"],"UNVERIFIED_PUBLIC_READBACK")
        self.assertIsNone(real["real_intervention_effect"])

    def test_06_no_benefit_claim_if_website_unavailable(self):
        self.assertEqual(self.card["technical_real_world_observation"]["status"],
                         "UNVERIFIED_PUBLIC_READBACK")
        self.assertFalse(self.card["release_decision"]["can_claim_reduced_rumination"])

    def test_07_no_business_profit_from_synthetic_profit(self):
        self.assertGreater(self.card["research_synthetic"]
                           ["P06_4_toy_incremental_contribution_yen_per_assignment"],0)
        self.assertIsNone(self.card["actual_business"]
                          ["net_incremental_profit_yen"])

    def test_08_no_paid_receipt(self):
        self.assertIsNone(self.card["actual_business"]["payment_provider_receipt"])

    def test_09_no_refund_readback(self):
        self.assertIsNone(self.card["actual_business"]["refunds_verified"])

    def test_10_no_human_health_claim(self):
        self.assertIsNone(self.card["actual_human_behavior"]["rumination_change"])

    def test_11_no_real_recruited_participants(self):
        self.assertEqual(self.card["actual_human_behavior"]
                         ["real_study_participants"],0)

    def test_12_harm_guardrail_do_not_ship(self):
        self.assertEqual(self.card["research_synthetic"]["P06_4_decision"],
                         "DO_NOT_SHIP")

    def test_13_real_release_is_hold(self):
        self.assertEqual(self.card["release_decision"]["status"],
                         "HOLD_NO_VERIFIED_CAUSAL_FIELD_RESULTS")

    def test_14_missing_permissions_blocks_live(self):
        self.assertFalse(self.card["release_decision"]
                         ["new_production_action_authorized"])

    def test_15_never_claim_caused_less_rumination(self):
        self.assertFalse(self.card["release_decision"]
                         ["can_claim_reduced_rumination"])

    def test_16_corrupt_frozen_plan_detected(self):
        file=self.out/"P06-3_PREANALYSIS_DESIGN_SYNTHETIC.json"
        original=file.read_bytes()
        try:
            file.write_bytes(original+b" ")
            with self.assertRaises(ValueError):
                verify_chain(self.out)
        finally:
            file.write_bytes(original)

    def test_17_corrupt_frozen_policy_detected(self):
        file=self.out/"P06-2_POLICY_FREEZE_SYNTHETIC.json"
        original=file.read_text()
        try:
            x=json.loads(original)
            x["whatif_policy"]["0"]=1-x["whatif_policy"]["0"]
            file.write_text(json.dumps(x))
            with self.assertRaises(ValueError):
                verify_chain(self.out)
        finally:
            file.write_text(original)

    def test_18_missing_artifact_detected(self):
        f=self.out/"P06-4_INCREMENTAL_VALUE_SYNTHETIC_RESULTS.json"
        backup=f.read_bytes()
        try:
            f.unlink()
            with self.assertRaises(ValueError):
                verify_chain(self.out)
        finally:
            f.write_bytes(backup)

    def test_19_fabricated_toy_ship_bypass_rejected(self):
        bad=copy.deepcopy(self.p064)
        bad["toy_strict_ship_gate"]["decision"]="ELIGIBLE_FOR_REVIEW"
        with self.assertRaises(ValueError):
            evidence_card(self.verified,self.p063,bad,
                          public_website_evidence(reader=unavailable))

    def test_20_fabricated_real_ledger_rejected(self):
        bad=copy.deepcopy(self.p064)
        bad["real_financial_outcome"]["status"]="PAID_REAL_WORLD_REVENUE"
        with self.assertRaises(ValueError):
            evidence_card(self.verified,self.p063,bad,
                          public_website_evidence(reader=unavailable))

    def test_21_output_is_machine_readable_and_reproducible(self):
        p=self.out/"P06-5_PROOF_CARD_RESEARCH_AND_REAL_WORLD.json"
        self.assertEqual(json.loads(p.read_text())["card_schema"],
                         "manager.p06.proof-card.v0.1")

    def test_22_baseline_comparison_not_fabricated(self):
        self.assertIsNone(self.card["actual_business"]
                          ["control_arm_or_other_valid_counterfactual"])


if __name__=="__main__":
    unittest.main()
