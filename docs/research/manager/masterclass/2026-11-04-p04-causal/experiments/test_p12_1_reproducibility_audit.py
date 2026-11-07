"""Contract tests for P12-1: reproducibility is NOT a third-party badge."""
import unittest
from dataclasses import replace

from p12_1_reproducibility_audit import (
    canonical_json_bytes, digest, alternative_ope, frozen_bandit_inputs,
    alternate_logistic_mle, alternate_negative_transfer, group_holdout_integrity,
    artificial_group_split_demo, validate_benchmark_card, seed_variance_report,
    run_audit, robust_mean,
)
from p11_1_5_research_labs import synthetic_contextual_log, p11_1_demo, p11_4_demo


PINNED_P11_SHA = "0c236f249ac4503764770135a86e2026cd37fec9"
BEHAVIOR_SUPPORT = {(0, 0):.9,(0, 1):.1,(1, 0):.25,(1, 1):.75}


class CanonicalEvidence(unittest.TestCase):
    def test_canonical_order_independent(self):
        self.assertEqual(digest({"a":1,"b":2}), digest({"b":2,"a":1}))

    def test_hash_sensitive_to_changed_value(self):
        self.assertNotEqual(digest({"x":1}),digest({"x":2}))

    def test_reject_nan(self):
        with self.assertRaises(ValueError):
            canonical_json_bytes({"x":float("nan")})

    def test_dataset_replay_is_byte_stable(self):
        self.assertEqual(frozen_bandit_inputs()["sha256"],
                         frozen_bandit_inputs()["sha256"])

    def test_dataset_changes_across_seeds(self):
        self.assertNotEqual(frozen_bandit_inputs(seed=1101,n=300)["sha256"],
                            frozen_bandit_inputs(seed=1102,n=300)["sha256"])

    def test_no_empty_robust_mean(self):
        with self.assertRaisesRegex(ValueError,"nonempty"):
            robust_mean([])


class AlternativeArithmetic(unittest.TestCase):
    def setUp(self):
        self.rows=synthetic_contextual_log(n=20000,seed=1101)

    def test_ips_agrees_with_original(self):
        self.assertAlmostEqual(alternative_ope(self.rows,{0:.2,1:.7})["ips"],p11_1_demo()["ips"],places=10)

    def test_dr_agrees_with_original(self):
        self.assertAlmostEqual(alternative_ope(self.rows,{0:.2,1:.7})["dr"],p11_1_demo()["doubly_robust"],places=10)

    def test_snips_agrees_with_original(self):
        self.assertAlmostEqual(alternative_ope(self.rows,{0:.2,1:.7})["snips"],p11_1_demo()["snips"],places=10)

    def test_oracle_not_claimed_human(self):
        result=p11_1_demo()
        self.assertEqual(result["method"],"SYNTHETIC_RANDOMIZED_BANDIT_NOT_HUMAN_EFFICACY")

    def test_empty_rows_refused(self):
        with self.assertRaisesRegex(ValueError,"empty"):
            alternative_ope([],{0:.2,1:.7})

    def test_bad_logging_propensity_refused(self):
        xs=list(self.rows[:100])
        xs[0]=replace(xs[0],logged_propensity=0.0)
        with self.assertRaisesRegex(ValueError,"invalid propensity"):
            alternative_ope(xs,{0:.2,1:.7})

    def test_nonbinary_context_refused(self):
        xs=list(self.rows[:100])
        xs[0]=replace(xs[0],context=99)
        with self.assertRaisesRegex(ValueError,"unrecognized"):
            alternative_ope(xs,{0:.2,1:.7})

    def test_alternative_logit_recovers_direction(self):
        bias,slope=alternate_logistic_mle([(-1,0)]*20+[(1,1)]*20)
        self.assertGreater(slope,0)

    def test_alternative_logit_needs_both_bins(self):
        with self.assertRaisesRegex(ValueError,"both x bins"):
            alternate_logistic_mle([(1,1)]*20)

    def test_alternate_negative_transfer_matches_direction(self):
        alt=alternate_negative_transfer()
        ref=p11_4_demo()
        for group in ("A","B"):
            self.assertLess(alt["specialists"][group],alt["pooled"][group])
            self.assertAlmostEqual(alt["specialists"][group],
                                   ref["specific_test_logloss"][group],delta=.03)

    def test_alternate_negative_transfer_repeatable(self):
        self.assertEqual(alternate_negative_transfer(),alternate_negative_transfer())


class LeakageChecks(unittest.TestCase):
    def setUp(self):
        self.records=[
            {"person":f"p{i//2}","study":f"s{i//6}"} for i in range(12)
        ]

    def test_rowwise_split_leaks_person(self):
        with self.assertRaisesRegex(ValueError,"LEAKAGE"):
            group_holdout_integrity(self.records,list(range(0,12,2)),
                                    list(range(1,12,2)),"person")

    def test_holdout_studies_pass(self):
        result=group_holdout_integrity(self.records,list(range(6)),list(range(6,12)),"study")
        self.assertTrue(result["disjoint_groups"])

    def test_overlap_row_refused(self):
        with self.assertRaisesRegex(ValueError,"LEAKAGE"):
            group_holdout_integrity(self.records,[0,1],[1,2],"person")

    def test_same_row_twice_refused(self):
        with self.assertRaisesRegex(ValueError,"duplicate"):
            group_holdout_integrity(self.records,[0,0,1],[2,3],"person")

    def test_missing_groups_refused(self):
        with self.assertRaisesRegex(ValueError,"missing"):
            group_holdout_integrity([{"person":"a"},{}],[0],[1],"person")

    def test_bad_row_index_refused(self):
        with self.assertRaisesRegex(ValueError,"invalid row"):
            group_holdout_integrity(self.records,[1],[99],"study")

    def test_demo_has_detected_naive_leak(self):
        d=artificial_group_split_demo()
        self.assertEqual(d["row_wise_split"],"REJECTED_PERSON_LEAKAGE")
        self.assertTrue(d["study_holdout"]["disjoint_groups"])


class BenchmarkCardContract(unittest.TestCase):
    def setUp(self):
        self.card=run_audit(PINNED_P11_SHA)["benchmark_card"]

    def test_valid_card_passes(self):
        validate_benchmark_card(self.card)

    def test_no_claim_of_human_benefit(self):
        self.assertIs(self.card["human_outcome_claim"],False)

    def test_fabricated_human_claim_refused(self):
        card={**self.card,"human_outcome_claim":True}
        with self.assertRaisesRegex(ValueError,"human efficacy"):
            validate_benchmark_card(card)

    def test_corrupt_digest_refused(self):
        card={**self.card,"dataset_revision_sha256":"deadbeef"}
        with self.assertRaisesRegex(ValueError,"SHA"):
            validate_benchmark_card(card)

    def test_missing_license_rejected(self):
        card={**self.card,"license_status":"UNKNOWN"}
        with self.assertRaisesRegex(ValueError,"license"):
            validate_benchmark_card(card)

    def test_group_leak_in_card_rejected(self):
        card={**self.card,"test_groups":["source-sim-train"]}
        with self.assertRaisesRegex(ValueError,"group-leaked"):
            validate_benchmark_card(card)

    def test_missing_metric_rejected(self):
        card={**self.card}
        card.pop("metric")
        with self.assertRaisesRegex(ValueError,"fields"):
            validate_benchmark_card(card)


class IntegratedP121(unittest.TestCase):
    def test_all_claims_crosschecked(self):
        d=run_audit(PINNED_P11_SHA)
        self.assertLess(d["p11_bandit_replay"]["maximum_numeric_difference"],1e-10)
        self.assertEqual(d["evidence_level"],"SAME_AUTHOR_ALTERNATE_CALCULATION")
        self.assertEqual(d["external_independent_reviewer"],"NOT_PERFORMED")

    def test_fixed_seed_variance_is_reproducible(self):
        self.assertEqual(seed_variance_report(seeds=(11,12),n=100),
                         seed_variance_report(seeds=(11,12),n=100))

    def test_bad_source_sha_refused(self):
        with self.assertRaisesRegex(ValueError,"SHA"):
            run_audit("fake")

    def test_valid_length_but_wrong_original_revision_refused(self):
        with self.assertRaisesRegex(ValueError, "immutable original"):
            run_audit("a"*40)

    def test_no_real_bfm_claim(self):
        d=run_audit(PINNED_P11_SHA)
        self.assertEqual(d["actual_shared_BFM_training"],"NOT_PERFORMED")

    def test_source_hash_present(self):
        self.assertEqual(len(frozen_bandit_inputs()["sha256"]),64)


if __name__=="__main__":
    unittest.main()
