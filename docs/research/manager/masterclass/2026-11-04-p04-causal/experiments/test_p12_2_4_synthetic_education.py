"""Unit checks for P12-2/3/4 synthetic scientific-methods exercises."""
import unittest
from copy import deepcopy
from math import log
from p12_2_4_synthetic_education import (
    attrition_binary_effect_bounds, evaluate_benefit_harm_guard,
    validate_claim_record, js_divergence, brier_score,
    model_update_proposal, synthetic_demo,
)


class AttritionBoundsTest(unittest.TestCase):
    def test_bound_calculation(self):
        d=attrition_binary_effect_bounds(100,80,60,100,90,54)
        self.assertAlmostEqual(d["observed_only_difference"],.15)
        self.assertAlmostEqual(d["range_of_unobserved_binary_effect"][0],-.04)
        self.assertAlmostEqual(d["range_of_unobserved_binary_effect"][1],.26)

    def test_missing_is_counted(self):
        d=attrition_binary_effect_bounds(100,80,60,100,90,54)
        self.assertEqual((d["treatment_missing"],d["control_missing"]),(20,10))

    def test_no_missing_collapses_bound(self):
        d=attrition_binary_effect_bounds(10,10,6,10,10,5)
        self.assertEqual(d["range_of_unobserved_binary_effect"][0],
                         d["range_of_unobserved_binary_effect"][1])

    def test_no_observed_values_not_turned_to_zero(self):
        d=attrition_binary_effect_bounds(10,0,0,10,0,0)
        self.assertIsNone(d["observed_only_difference"])
        self.assertEqual(d["range_of_unobserved_binary_effect"],[-1.0,1.0])

    def test_reject_negative_counts(self):
        with self.assertRaisesRegex(ValueError,"inconsistent"):
            attrition_binary_effect_bounds(100,20,-1,100,90,54)

    def test_reject_success_exceed_observed(self):
        with self.assertRaisesRegex(ValueError,"inconsistent"):
            attrition_binary_effect_bounds(100,20,21,100,90,54)

    def test_reject_float_counts(self):
        with self.assertRaisesRegex(ValueError,"integer"):
            attrition_binary_effect_bounds(100.0,80,60,100,90,54)

    def test_not_confidence_interval(self):
        d=attrition_binary_effect_bounds(100,80,60,100,90,54)
        self.assertTrue(d["not_a_confidence_interval"])
        self.assertTrue(d["not_real_human_causal_effect"])


class BenefitAndHarmTest(unittest.TestCase):
    def test_not_measured_blocks(self):
        d=evaluate_benefit_harm_guard("NOT_MEASURED","NOT_MEASURED",True,True)
        self.assertEqual(d["status"],"RESEARCH_HOLD")
        self.assertIn("BENEFIT_NOT_MEASURED",d["reasons"])

    def test_harm_observed_blocks(self):
        d=evaluate_benefit_harm_guard("BENEFIT_OBSERVED","HARM_OBSERVED",True,True)
        self.assertIn("HARM_REQUIRES_STOP_REVIEW",d["reasons"])

    def test_missing_consent_blocks(self):
        d=evaluate_benefit_harm_guard("BENEFIT_OBSERVED","NO_HARM_OBSERVED",False,True)
        self.assertIn("NO_CONSENT",d["reasons"])

    def test_no_independent_outcome_blocks(self):
        d=evaluate_benefit_harm_guard("BENEFIT_OBSERVED","NO_HARM_OBSERVED",True,False)
        self.assertIn("NO_INDEPENDENT_OUTCOME",d["reasons"])

    def test_eligible_does_not_grant_authority(self):
        d=evaluate_benefit_harm_guard("BENEFIT_OBSERVED","NO_HARM_OBSERVED",True,True)
        self.assertFalse(d["live_intervention_authority"])
        self.assertFalse(d["causal_effect_identified"])

    def test_invalid_evidence_label(self):
        with self.assertRaisesRegex(ValueError,"unsupported"):
            evaluate_benefit_harm_guard("CLINICALLY_PROVEN","NO_HARM_OBSERVED",True,True)


class ClaimContractTest(unittest.TestCase):
    def setUp(self):
        self.rec={
            "claim_id":"synth-001",
            "source_url":"https://example.org/research",
            "source_revision":"2026-11-08",
            "experiment_evidence_level":"SYNTHETIC_INTERNAL",
            "article_revision_sha256":"1"*64,
            "outcome_type":"educational",
            "supports_human_benefit":False,
            "explicit_limitations":"synthetic artificial example",
            "language":"ja",
            "publication_state":"DRAFT",
        }

    def test_card_valid_and_hash_stable(self):
        self.assertEqual(validate_claim_record(self.rec),validate_claim_record(self.rec))

    def test_reject_synthetic_human_benefit(self):
        r={**self.rec,"supports_human_benefit":True}
        with self.assertRaisesRegex(ValueError,"synthetic"):
            validate_claim_record(r)

    def test_reject_missing_source(self):
        r={**self.rec,"source_url":""}
        with self.assertRaisesRegex(ValueError,"identifiers"):
            validate_claim_record(r)

    def test_reject_non_https_source(self):
        r={**self.rec,"source_url":"http://example.org"}
        with self.assertRaisesRegex(ValueError,"HTTPS"):
            validate_claim_record(r)

    def test_reject_incorrect_sha(self):
        r={**self.rec,"article_revision_sha256":"abc"}
        with self.assertRaisesRegex(ValueError,"digest"):
            validate_claim_record(r)

    def test_reject_unreported_limitations(self):
        r={**self.rec,"explicit_limitations":" "}
        with self.assertRaisesRegex(ValueError,"limitations"):
            validate_claim_record(r)

    def test_reject_unknown_evidence_level(self):
        r={**self.rec,"experiment_evidence_level":"MAGIC"}
        with self.assertRaisesRegex(ValueError,"unknown evidence"):
            validate_claim_record(r)

    def test_reject_invalid_publication_state(self):
        r={**self.rec,"publication_state":"PUBLISHED_UNVERIFIED"}
        with self.assertRaisesRegex(ValueError,"publication state"):
            validate_claim_record(r)

    def test_reject_duplicate_undocumented_field(self):
        r={**self.rec,"invented_metric":.99}
        with self.assertRaisesRegex(ValueError,"provenance field"):
            validate_claim_record(r)


class DriftMetricsTest(unittest.TestCase):
    def test_js_same_distribution_zero(self):
        self.assertAlmostEqual(js_divergence([.5,.5],[.5,.5]),0)

    def test_js_shift_positive(self):
        self.assertGreater(js_divergence([.5,.5],[.9,.1]),0)

    def test_js_is_symmetric(self):
        self.assertAlmostEqual(js_divergence([.5,.5],[.9,.1]),
                               js_divergence([.9,.1],[.5,.5]))

    def test_js_max_for_disjoint_support(self):
        self.assertAlmostEqual(js_divergence([1.,0.],[0.,1.]),log(2))

    def test_js_invalid_mass(self):
        with self.assertRaisesRegex(ValueError,"distribution"):
            js_divergence([.7,.7],[.5,.5])

    def test_js_invalid_negative(self):
        with self.assertRaisesRegex(ValueError,"distribution"):
            js_divergence([-1.,2.],[.5,.5])

    def test_js_different_support_sizes(self):
        with self.assertRaisesRegex(ValueError,"same support"):
            js_divergence([.5,.5],[.2,.3,.5])

    def test_delayed_label_not_assumed_zero(self):
        d=brier_score([.9,.2],[1,None])
        self.assertEqual(d["status"],"PARTIAL_LABEL_COVERAGE")
        self.assertAlmostEqual(d["brier"],.01)
        self.assertEqual(d["coverage"],.5)

    def test_all_labels_unseen_returns_unknown(self):
        d=brier_score([.9,.2],[None,None])
        self.assertIsNone(d["brier"])
        self.assertEqual(d["status"],"PERFORMANCE_UNKNOWN")

    def test_invalid_probability_rejected(self):
        with self.assertRaisesRegex(ValueError,"invalid prediction"):
            brier_score([1.2],[1])

    def test_invalid_label_rejected(self):
        with self.assertRaisesRegex(ValueError,"binary outcomes"):
            brier_score([.5],[2])


class ProductionBoundaryTest(unittest.TestCase):
    def test_even_perfect_candidate_cannot_deploy(self):
        d=model_update_proposal(rights_verified=True,host_authority=True,
             baseline_better=True,harm_stopped=False,evidence_complete=True,budget_ok=True)
        self.assertEqual(d["status"],"RESEARCH_CANDIDATE_ONLY")
        self.assertFalse(d["production_deployed"])

    def test_harm_stop_blocks(self):
        d=model_update_proposal(rights_verified=True,host_authority=True,
             baseline_better=True,harm_stopped=True,evidence_complete=True,budget_ok=True)
        self.assertIn("NO_HARM_STOP",d["failed_checks"])

    def test_unlicensed_blocks(self):
        d=model_update_proposal(rights_verified=False,host_authority=True,
             baseline_better=True,harm_stopped=False,evidence_complete=True,budget_ok=True)
        self.assertIn("RIGHTS",d["failed_checks"])

    def test_budget_blocks(self):
        d=model_update_proposal(rights_verified=True,host_authority=True,
             baseline_better=True,harm_stopped=False,evidence_complete=True,budget_ok=False)
        self.assertIn("BUDGET",d["failed_checks"])

    def test_demo_explicitly_synthetic(self):
        d=synthetic_demo()
        self.assertTrue(d["all_examples_synthetic"])
        self.assertEqual(d["real_user_benefit"],"NOT_MEASURED")
        self.assertEqual(d["real_software_deployment"],"NOT_PERFORMED")


if __name__=="__main__":
    unittest.main()
