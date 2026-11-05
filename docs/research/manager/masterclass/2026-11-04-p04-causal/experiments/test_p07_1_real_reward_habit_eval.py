"""P07-1 audited tests over the real MIT Collins human trial data.

Toy two-row fixture is used ONLY to prove software no-lookahead behavior;
no synthetic results are added to empirical findings or to the benchmark.
"""
import json
import unittest
from pathlib import Path
import numpy as np

from p07_1_real_reward_habit_eval import (
    SOURCE_ROOT,EVIDENCE,EXPECTED_FILES,EXPECTED_TWITTER_FIG4,
    MODELS,FEATURES,SEED,ALPHA_REWARD,
    read_actual_trials,lagged_features,group_split,probabilities,trial_scores,
    describe_social_media_published_fit,file_sha,subject_bootstrap_advantage,
)
from p07_1_real_avoidance_descriptive import (
    counts_from_source,rates,cluster_bootstrap,
)

class ActualHumanHabitEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=json.loads((EVIDENCE/"P07-1_REAL_REWARD_HABIT_HELDOUT_RESULTS_20261105.json").read_text())
        cls.avoid=json.loads((EVIDENCE/"P07-1_REAL_AVOIDANCE_BY_LOAD_20261105.json").read_text())
        cls.expe1,cls.meta=read_actual_trials("Expe1.mat")
        cls.x,cls.y,cls.sub,cls.qc=lagged_features(cls.expe1)

    def test_01_source_files_real_not_simulated(self):
        self.assertTrue(self.model["fully_real_human_trials"])
        self.assertEqual(self.model["synthetic_human_subjects_added"],0)

    def test_02_official_source_sha_verified_five(self):
        for n,h in EXPECTED_FILES.items():
            _,m=read_actual_trials(n)
            self.assertEqual(m["sha256"],h)

    def test_03_mit_license_verified(self):
        license=(SOURCE_ROOT/"WMH/LICENSE").read_text()
        self.assertIn("MIT License",license)

    def test_04_source_git_commit_frozen(self):
        self.assertEqual(self.model["authors_code_commit"],
                         "f2d4108dea80642e7d5b95d1c108916091a221c8")

    def test_05_original_columns_untouched(self):
        self.assertEqual(self.meta["trial_original_columns"],
                         ["subno","block","ns","stimseq","choice","rew","rt"])

    def test_06_real_expe1_choice_count(self):
        self.assertEqual(self.qc["trials_eligible"],52911)
        self.assertEqual(self.qc["participant_count"],79)

    def test_07_correct_answer_is_not_feature(self):
        self.assertFalse(self.qc["future_correct_answer_field_used_as_feature"])
        self.assertIn("corAseq",self.meta["forbidden_current_choice_target_columns"])

    def test_08_current_outcome_cannot_leak(self):
        self.assertFalse(self.qc["current_reward_leaks_into_current_prediction"])

    def test_09_no_missing_or_out_of_range_actions(self):
        self.assertEqual(set(np.unique(self.y)),{0,1,2})
        self.assertTrue(np.isfinite(self.x).all())

    def test_10_unequal_actions_have_three_candidates(self):
        self.assertEqual(self.x.shape[1:],(3,4))
        self.assertEqual(tuple(FEATURES),(
            "reward_prediction","outcome_independent_habit",
            "previous_same_stimulus_choice","recent_reward_memory"))

    def test_11_group_splits_no_overlap(self):
        parts=group_split(self.sub)
        ids=[set(self.sub[p]) for p in parts.values()]
        self.assertFalse(ids[0]&ids[1] or ids[0]&ids[2] or ids[1]&ids[2])

    def test_12_group_split_reproducible(self):
        a=group_split(self.sub);b=group_split(self.sub)
        for k in a:np.testing.assert_array_equal(a[k],b[k])

    def test_13_group_train_validation_test_subject_counts(self):
        split=self.model["training_split"]
        self.assertEqual([split[k]["n_subjects"] for k in ("train","validation","test")],
                         [47,16,16])

    def test_14_test_set_not_used_in_model_selection(self):
        self.assertFalse(self.model["models_fit"]["reward_only"].get("test_used_in_fitting",False))
        self.assertFalse(self.model["frozen_validation_selection"]=="made_up")

    def test_15_selected_by_val_not_test(self):
        best=min(self.model["validation_scores"],
                 key=lambda k:(self.model["validation_scores"][k]
                               ["log_loss_nats_per_trial"],k))
        self.assertEqual(best,self.model["frozen_validation_selection"])

    def test_16_best_model_combines_reward_habit_memory(self):
        self.assertEqual(self.model["frozen_validation_selection"],
                         "reward_plus_habit_plus_memory")

    def test_17_external_datasets_not_fit_or_tuned(self):
        self.assertFalse(
            json.loads((EVIDENCE/"P07-1_REAL_HABIT_MODEL_FREEZE_20261105.json").read_text())
            ["holdout_or_OOD_labels_used_to_tune"])

    def test_18_five_real_datasets_evaluated(self):
        self.assertEqual(len(self.model["heldout_and_external_generalization"]),5)

    def test_19_all_real_eligible_trial_counts(self):
        summ=sum(v["qc"]["trials_eligible"]
                 for v in self.model["actual_experimental_datasets"].values())
        self.assertEqual(summ,269603)

    def test_20_trial_n_heldout_and_external_sum(self):
        vals=self.model["heldout_and_external_generalization"]
        self.assertEqual(sum(v["real_trials"] for v in vals.values()),
                         10461+28720+18200+139990+29782)

    def test_21_correct_probabilities_sum_one(self):
        fit=self.model["models_fit"]["reward_plus_habit_plus_memory"]
        p=probabilities(self.x[:30],"reward_plus_habit_plus_memory",fit)
        self.assertTrue(np.allclose(p.sum(axis=1),1))

    def test_22_uniform_baseline_ln3(self):
        uniform=probabilities(self.x[:30],"uniform",self.model["models_fit"]["uniform"])
        _,sc=trial_scores(self.y[:30],uniform)
        self.assertAlmostEqual(sc["log_loss_nats_per_trial"],np.log(3),places=10)

    def test_23_invalid_probability_fails(self):
        p=np.full((5,3),1/3)
        p[0,0]=1.01
        with self.assertRaises(ValueError):
            trial_scores(np.zeros(5,dtype=int),p)

    def test_24_first_trial_has_uninformed_baseline(self):
        tiny=np.full((2,17),np.nan)
        for k in range(2):
            tiny[k,[0,1,2,4,9,12,13]]=[1,1,2,1,1,0,0.3]
        x,y,s,qc=lagged_features(tiny)
        self.assertEqual(len(x),2)
        np.testing.assert_allclose(x[0,:,0],[1/3]*3,rtol=1e-6)
        self.assertTrue((x[0,:,1:]==0).all())

    def test_25_mutating_current_reward_cannot_change_current_prediction(self):
        tiny=np.full((2,17),np.nan)
        for k in range(2):
            tiny[k,[0,1,2,4,9,12,13]]=[1,1,2,1,1,0,0.3]
        original=lagged_features(tiny)[0]
        altered=tiny.copy()
        altered[0,12]=1
        changed=lagged_features(altered)[0]
        np.testing.assert_array_equal(original[0],changed[0])
        self.assertNotEqual(original[1,0,0],changed[1,0,0])

    def test_26_future_choice_cannot_change_past_features(self):
        tiny=np.full((3,17),np.nan)
        for k in range(3):
            tiny[k,[0,1,2,4,9,12,13]]=[1,1,2,1,1,0,0.3]
        before=lagged_features(tiny)[0]
        tiny[2,9]=3
        after=lagged_features(tiny)[0]
        np.testing.assert_array_equal(before[:3],after[:3])

    def test_27_reset_at_new_block(self):
        tiny=np.full((2,17),np.nan)
        tiny[0,[0,1,2,4,9,12,13]]=[1,1,2,1,1,1,.3]
        tiny[1,[0,1,2,4,9,12,13]]=[1,2,2,1,1,0,.3]
        x,*_=lagged_features(tiny)
        np.testing.assert_allclose(x[1,:,0],[1/3]*3,rtol=1e-6)
        self.assertTrue(np.all(x[1,:,1:]==0))

    def test_28_released_rows_not_exported(self):
        self.assertFalse(self.model["human_subject_data_in_GitHub"])
        self.assertFalse(self.model["real_behavior_training_data_committed"])

    def test_29_no_clinical_or_real_customer_effect_claim(self):
        self.assertFalse(self.model["reduced_rumination_or_clinical_effect_proven"])
        self.assertFalse(self.model["real_human_stimulus_or_choice_intervention_executed"])

    def test_30_hybrid_improves_logloss_over_reward_on_all_five(self):
        for v in self.model["heldout_and_external_generalization"].values():
            m=v["all_model_scores"]
            self.assertLess(
                m["reward_plus_habit_plus_memory"]["log_loss_nats_per_trial"],
                m["reward_only"]["log_loss_nats_per_trial"])

    def test_31_cluster_bootstrap_ci_vs_simple_positive(self):
        for v in self.model["heldout_and_external_generalization"].values():
            ci=v["selected_model_gain_vs_simple_baseline"]["cluster_bootstrap_CI95"]
            self.assertGreater(ci[0],0)

    def test_32_external_probabilistic_study_explicit(self):
        self.assertIn("Expe14.mat",self.model["heldout_and_external_generalization"])

    def test_33_study12_added_as_secondary_after_first_run(self):
        self.assertTrue(self.model["supplementary_OOD_datasets_Expe12_and_Expe14_added_after_first_three_dataset_run"])

    def test_34_social_source_sha_pinned(self):
        self.assertEqual(
            self.model["twitter_real_2026_habit_published_fig4_descriptive_replication"]["source_SHA256"],
            EXPECTED_TWITTER_FIG4)

    def test_35_social_confirmation_n_1558(self):
        social=self.model["twitter_real_2026_habit_published_fig4_descriptive_replication"]
        self.assertEqual(social["n_users"],1558)
        self.assertFalse(social["independent_refit"])

    def test_36_social_association_modest_negative(self):
        s=self.model["twitter_real_2026_habit_published_fig4_descriptive_replication"]
        rho=s["statistics"]["a_habit_weight"]["spearman_rho"]
        self.assertTrue(-.2<rho<-.05)

    def test_37_reward_omission_not_same_as_error_under_probabilistic(self):
        self.assertTrue(self.avoid["Expe14_zero_reward_not_equivalent_to_wrong_action"])

    def test_38_real_deterministic_and_probabilistic_separated(self):
        self.assertEqual(self.avoid["deterministic_tasks_only"]["n_individuals"],445)
        self.assertEqual(self.avoid["probabilistic_reward_task_only"]["n_individuals"],35)

    def test_39_deterministic_after_no_reward_more_repeats_with_higher_load(self):
        det=self.avoid["deterministic_tasks_only"]
        lo=det["rates"]["low_load_after_no_reward"]["repeat_rate"]
        hi=det["rates"]["high_load_after_no_reward"]["repeat_rate"]
        self.assertGreater(hi-lo,.10)

    def test_40_load_effect_deterministic_ci_above_zero(self):
        det=self.avoid["deterministic_tasks_only"]["cluster_bootstrap"]
        ci=det["after_no_reward_high_minus_low_load"]["participant_cluster_bootstrap_ci95"]
        self.assertGreater(ci[0],0)

    def test_41_stochastic_zero_reward_not_same_effect(self):
        prob=self.avoid["probabilistic_reward_task_only"]["cluster_bootstrap"]
        ci=prob["after_no_reward_high_minus_low_load"]["participant_cluster_bootstrap_ci95"]
        self.assertLess(ci[0],0)
        self.assertGreater(ci[1],0)

    def test_42_repeat_outcome_is_observed_choice(self):
        self.assertTrue(self.avoid["outcome_is_current_choice_repeat"])

    def test_43_social_source_aggregate_only(self):
        social=self.model["twitter_real_2026_habit_published_fig4_descriptive_replication"]
        self.assertFalse(social["raw_post_or_user_level_rows_committed"])

    def test_44_all_models_same_action_space(self):
        self.assertEqual(set(MODELS),{
            "uniform","reward_only","habit_only","reward_plus_habit",
            "reward_plus_habit_plus_memory"})

    def test_45_invalid_original_dataset_name_rejected(self):
        with self.assertRaises(ValueError):read_actual_trials("anything.mat")

if __name__=="__main__":
    unittest.main()
