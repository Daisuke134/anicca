"""P06-2 synthetic-only randomized what-if ablation tests."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

import numpy as np
from p06_2_whatif_ablation import (
    N_TRAIN,N_VALIDATION,N_TRIAL,COST,
    config,fingerprint,generate,map_policy,fit_whatif,baseline_policy_tables,
    ipw_value,choose_strong_baseline,trial_for_policies,arm_delta,theoretical_gain,run,
)

class P062AblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work=TemporaryDirectory()
        cls.root=Path(cls.work.name)
        cls.result=run(cls.root)
        cls.train=generate(N_TRAIN,20261162)
        cls.val=generate(N_VALIDATION,20261163)
        cls.policy,cls.simulator=fit_whatif(cls.train)
        cls.base_name,cls.base,cls.scores=choose_strong_baseline(cls.train,cls.val)

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def test_preanalysis_exists(self):
        self.assertTrue((self.root/"P06-2_PREANALYSIS_SYNTHETIC.json").is_file())

    def test_freeze_before_trial_results_file(self):
        receipt=json.loads((self.root/"P06-2_POLICY_FREEZE_SYNTHETIC.json").read_text())
        self.assertFalse(receipt["test_outcomes_generated_before_freeze"])

    def test_frozen_plan_hash(self):
        r=json.loads((self.root/"P06-2_POLICY_FREEZE_SYNTHETIC.json").read_text())
        self.assertEqual(r["plan_sha256"],fingerprint(config()))

    def test_both_policy_hashes(self):
        r=json.loads((self.root/"P06-2_POLICY_FREEZE_SYNTHETIC.json").read_text())
        self.assertEqual(r["policy_hashes"]["whatif"],fingerprint(r["whatif_policy"]))
        self.assertEqual(r["policy_hashes"]["baseline"],fingerprint(r["baseline_policy"]))

    def test_no_real_humans_or_profit_claim(self):
        self.assertEqual(config()["actual_users"],0)
        self.assertFalse(config()["actual_business_profit"])

    def test_correct_train_val_trial_n(self):
        self.assertEqual((N_TRAIN,N_VALIDATION,N_TRIAL),(24000,16000,40000))

    def test_train_val_seeds_different(self):
        self.assertEqual(len(set(self.result["train_validation_trial_seeds"])),3)

    def test_independent_seeds_yield_distinct_y(self):
        a=generate(1000,1);b=generate(1000,2)
        self.assertFalse(np.array_equal(a["observed"],b["observed"]))

    def test_train_not_all_one_action(self):
        a=self.train["action"]
        self.assertTrue(0.45<float(np.mean(a))<0.55)

    def test_no_oracle_in_training_input_required(self):
        df={k:self.train[k] for k in ("motivation","fatigue","action","observed")}
        fit,_=fit_whatif(df)
        self.assertEqual(fit,self.policy)

    def test_simulator_four_cells(self):
        self.assertEqual(set(self.simulator),{"0","1","2","3"})

    def test_simulator_probability_in_range(self):
        for row in self.simulator.values():
            self.assertTrue(0<=row["p_observed_given_no_action"]<=1)
            self.assertTrue(0<=row["p_observed_given_action"]<=1)

    def test_learned_policy_has_two_actions(self):
        self.assertEqual(set(self.policy.values()),{0,1})

    def test_no_action_baseline(self):
        x=baseline_policy_tables(self.train)
        self.assertEqual(set(x["NO_ACTION"].values()),{0})

    def test_all_action_baseline(self):
        x=baseline_policy_tables(self.train)
        self.assertEqual(set(x["ALL_ACTION"].values()),{1})

    def test_baseline_chosen_from_predeclared_set(self):
        self.assertIn(self.base_name,config()["baseline_candidates"])

    def test_validated_best_baseline_not_trial(self):
        scores=self.result["baseline_heldout_ipw_selection_scores"]
        choice=self.result["baseline_selected_without_trial_peeking"]
        self.assertEqual(scores[choice]["estimated_utility"],
                         max(row["estimated_utility"] for row in scores.values()))

    def test_policy_map_no_bad_output(self):
        m=np.array([0,0,1,1]);f=np.array([0,1,0,1])
        self.assertTrue(set(map_policy(m,f,self.policy)).issubset({0,1}))

    def test_ipw_nonnegative_utility(self):
        result=ipw_value(self.val,self.base)
        self.assertTrue(0<=result["estimated_utility"]<=1)

    def test_policy_holdout_deterministic(self):
        x=trial_for_policies(self.policy,self.base)
        y=trial_for_policies(self.policy,self.base)
        np.testing.assert_array_equal(x["outcome"],y["outcome"])

    def test_trial_arm_balance(self):
        r=self.result["primary_net_utility_policy_rct"]
        self.assertEqual(r["n_whatif"]+r["n_baseline"],N_TRIAL)
        self.assertTrue(18000<r["n_whatif"]<22000)

    def test_primary_delta_bounds(self):
        r=self.result["primary_net_utility_policy_rct"]
        self.assertTrue(r["ci95"][0]<r["increment"]<r["ci95"][1])

    def test_primary_significant_in_toy_world(self):
        r=self.result["primary_net_utility_policy_rct"]
        self.assertTrue(r["ci95"][0]>0 and r["two_sided_p"]<.05)

    def test_true_difference_not_trained_into_model(self):
        self.assertFalse(self.result["true_effect_used_in_training"])
        self.assertAlmostEqual(self.result["synthetic_true_increment"],.02,places=8)

    def test_primary_equals_secondary_minus_burden(self):
        r=self.result
        primary=r["primary_net_utility_policy_rct"]["increment"]
        completed=r["secondary_task_completion"]["increment"]
        burden=r["secondary_notification_rate"]["increment"]
        self.assertAlmostEqual(primary,completed-COST*burden,places=10)

    def test_blank_policy_rejected(self):
        with self.assertRaises(KeyError):
            map_policy(np.array([0]),np.array([0]),{})

    def test_oracle_display_not_fit(self):
        self.assertGreater(theoretical_gain(self.policy,self.base),0)

    def test_three_artifacts_consistent(self):
        self.assertTrue((self.root/"P06-2_SYNTHETIC_ABLATION_RESULTS.json").is_file())
        for name in ("P06-2_PREANALYSIS_SYNTHETIC.json",
                     "P06-2_POLICY_FREEZE_SYNTHETIC.json",
                     "P06-2_SYNTHETIC_ABLATION_RESULTS.json"):
            self.assertTrue(json.loads((self.root/name).read_text()))

if __name__=="__main__":
    unittest.main()
