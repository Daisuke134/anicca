"""BehaviorBench/Psych-101 learning lab tests, entirely fictional data."""
import unittest
from dataclasses import replace
from copy import deepcopy
from math import isfinite

from behaviorbench_psych101_data_contract import (
    make_synthetic_decisions,split_by_person_within_study,
    assert_disjoint_groups,leave_one_study_out,session_to_psych101_style,
    response_only_character_mask,training_example_from_history,
    bernoulli_nll,brier,tvd_binary,fit_toy_logistic,predict_toy,
    enforce_data_rights,synthetic_training_evidence,
)


class LearningDataTests(unittest.TestCase):
    def setUp(self):
        self.records=make_synthetic_decisions()

    def test_training_fixture_total(self):
        self.assertEqual(len(self.records),4*32*9)

    def test_every_record_explicitly_synthetic(self):
        self.assertTrue(all(x["synthetic"] for x in self.records))

    def test_seed_reproducibility(self):
        self.assertEqual(make_synthetic_decisions(seed=123),
                         make_synthetic_decisions(seed=123))

    def test_different_seeds_differ(self):
        self.assertNotEqual(make_synthetic_decisions(seed=123),
                            make_synthetic_decisions(seed=124))

    def test_person_split_has_no_overlap(self):
        s=split_by_person_within_study(self.records)
        assert_disjoint_groups(s,"person")
        self.assertEqual(sum(map(len,s.values())),len(self.records))

    def test_person_ids_reused_across_studies_are_composite(self):
        s=split_by_person_within_study(self.records)
        self.assertEqual(len({(x["study_id"],x["participant_id"])
                              for a in s.values() for x in a}),4*32)

    def test_no_split_can_use_actual_person_labels_in_lab(self):
        rows=self.records[:10]+[{**self.records[10],"synthetic":False}]
        with self.assertRaisesRegex(ValueError,"only synthetic"):
            split_by_person_within_study(rows)

    def test_row_split_with_same_person_is_rejected(self):
        s={"train":[self.records[0]],"test":[self.records[1]]}
        with self.assertRaisesRegex(ValueError,"LEAKAGE"):
            assert_disjoint_groups(s,"person")

    def test_invalid_split_fraction_refused(self):
        with self.assertRaisesRegex(ValueError,"invalid split"):
            split_by_person_within_study(self.records,train_fraction=.99,val_fraction=.1)

    def test_study_split_is_disjoint(self):
        s=leave_one_study_out(self.records,"toy-study-3")
        assert_disjoint_groups(s,"study")
        self.assertEqual(len(s["test"]),32*9)

    def test_study_holdout_missing_refused(self):
        with self.assertRaisesRegex(ValueError,"valid held-out study"):
            leave_one_study_out(self.records,"toy-study-999")

    def test_trainer_sees_only_train_persons(self):
        s=split_by_person_within_study(self.records)
        train={(x["study_id"],x["participant_id"]) for x in s["train"]}
        test={(x["study_id"],x["participant_id"]) for x in s["test"]}
        self.assertFalse(train&test)

    def test_no_real_person_data(self):
        self.assertTrue(all(x["participant_id"].startswith("toy-") for x in self.records))


class ResponseOnlySupervisionTests(unittest.TestCase):
    def setUp(self):
        records=make_synthetic_decisions(studies=2,persons_per_study=6,trials=5)
        self.session=[x for x in records if x["study_id"]=="toy-study-0"
                      and x["participant_id"]=="toy-participant-0"]

    def test_one_session_yields_psych101_style_record(self):
        x=session_to_psych101_style(self.session)
        self.assertEqual(x["experiment"],"toy-study-0")
        self.assertEqual(x["participant"],"toy-participant-0")
        self.assertEqual(x["text"].count("<<"),5)

    def test_mask_only_supervises_choice_letters(self):
        t=session_to_psych101_style(self.session)["text"]
        m=response_only_character_mask(t)
        supervised="".join(c for c,flag in zip(t,m) if flag)
        self.assertEqual(len(supervised),5)
        self.assertEqual(set(supervised)-{"L","R"},set())

    def test_unmarked_instruction_gets_zero_loss_weight(self):
        t=session_to_psych101_style(self.session)["text"]
        m=response_only_character_mask(t)
        self.assertEqual(m[0],0)
        self.assertEqual(m[t.index("instructions")],0)

    def test_reject_missing_choices(self):
        with self.assertRaisesRegex(ValueError,"choice delimiters"):
            response_only_character_mask("Choose L or R.")

    def test_reject_invalid_label(self):
        with self.assertRaisesRegex(ValueError,"choice delimiters"):
            response_only_character_mask("You press <<X>>.")

    def test_reject_malformed_delimiters(self):
        with self.assertRaisesRegex(ValueError,"choice delimiters"):
            response_only_character_mask("You press <<L>.")

    def test_reject_cross_participant_transcript(self):
        recs=make_synthetic_decisions(studies=2,persons_per_study=6,trials=5)
        with self.assertRaisesRegex(ValueError,"one participant"):
            session_to_psych101_style([recs[0],recs[5]])

    def test_history_never_contains_future_choice(self):
        e=training_example_from_history(self.session,3)
        self.assertEqual(e["history_length"],3)
        self.assertEqual(e["target_trial"],3)
        self.assertEqual(e["assistant"],"R" if self.session[3]["observed_choice"] else "L")

    def test_first_trial_has_empty_history(self):
        e=training_example_from_history(self.session,0)
        self.assertIn("Past choices: []",e["user"])

    def test_target_index_out_of_range(self):
        with self.assertRaisesRegex(ValueError,"target trial"):
            training_example_from_history(self.session,500)


class MetricsAndTraining(unittest.TestCase):
    def test_nll_rewards_calibration(self):
        p=.7
        y=[1]*70+[0]*30
        exact=bernoulli_nll([.7]*100,y)
        overconfident=bernoulli_nll([.99]*100,y)
        self.assertLess(exact,overconfident)

    def test_brier_exact(self):
        self.assertAlmostEqual(brier([.8,.2],[1,0]),.04)

    def test_tvd_binary(self):
        self.assertAlmostEqual(tvd_binary(.7,1.),.3)

    def test_tvd_invalid(self):
        with self.assertRaisesRegex(ValueError,"distribution"):
            tvd_binary(1.1,.5)

    def test_nll_missing_data(self):
        with self.assertRaisesRegex(ValueError,"nonempty"):
            bernoulli_nll([],[])

    def test_actual_gradient_fit_updates_weights(self):
        rows=make_synthetic_decisions()
        params=fit_toy_logistic(split_by_person_within_study(rows)["train"])
        self.assertTrue(any(abs(x)>.01 for x in params))

    def test_toy_training_improves_over_baseline(self):
        x=synthetic_training_evidence()
        self.assertLess(x["toy_trained_nll"],x["baseline_nll"])
        self.assertLess(x["toy_trained_brier"],x["baseline_brier"])

    def test_evidence_says_not_a_behavior_fm(self):
        x=synthetic_training_evidence()
        self.assertFalse(x["actual_foundation_model_trained"])
        self.assertFalse(x["real_human_responses_used"])
        self.assertFalse(x["commercial_model_rights_cleared"])


class DatasetAccessGate(unittest.TestCase):
    def test_cannot_train_on_behaviorbench_test(self):
        with self.assertRaisesRegex(PermissionError,"eval-only"):
            enforce_data_rights("befm/BehaviorBench","commercial_model_training")

    def test_cannot_treat_public_psych101_card_as_full_rights(self):
        with self.assertRaisesRegex(PermissionError,"rights"):
            enforce_data_rights("marcelbinz/Psych-101","commercial_model_training")

    def test_gated_test_always_refused(self):
        with self.assertRaisesRegex(PermissionError,"gated"):
            enforce_data_rights("marcelbinz/Psych-101-test","academic_evaluation")

    def test_behaviorbench_academic_eval_only(self):
        self.assertEqual(enforce_data_rights("befm/BehaviorBench","academic_evaluation"),
                         "ACADEMIC_EVALUATION_ONLY_WITH_UPSTREAM_TERMS")

    def test_unknown_dataset_refused(self):
        with self.assertRaisesRegex(PermissionError,"unreviewed"):
            enforce_data_rights("random-source","source_review")

    def test_synthetic_can_be_reviewed(self):
        self.assertEqual(enforce_data_rights("self-authored-synthetic","source_review"),
                         "SYNTHETIC_LEARNING_ONLY")


if __name__=="__main__":
    unittest.main()
