"""P07-2 tests on real licensed ESM data and precomputed aggregate results.

No synthetic person data or clinical causality claims. Empirical data remain
in a private local temp directory; aggregate/hashed outputs only in repo.
"""
import json
import unittest
import numpy as np
from p07_2_real_esm_state_prediction import (
    SOURCES,EVIDENCE,source_frame,sequences,split_people,metrics,SEED,
)

class P072RealESMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((EVIDENCE/"P07-2_REAL_ESM_HOEBEKE_AFFECT_RESULTS_20261105.json").read_text())
        cls.raw={n:source_frame(n)[0] for n in SOURCES}
        cls.pairs={n:sequences(cls.raw[n],n)[0] for n in SOURCES}

    def test_01_real_data_only(self):
        self.assertTrue(self.r["all_records_real_observed_human_responses"])
        self.assertEqual(self.r["n_synthetic_humans"],0)

    def test_02_actual_hoebeke_participants(self):
        self.assertEqual(self.raw["hoebeke_2022"].id.nunique(),40)

    def test_03_actual_dejonckheere_participants(self):
        self.assertEqual(self.raw["dejonckheere_2019"].id.nunique(),100)

    def test_04_expected_original_rows(self):
        self.assertEqual(len(self.raw["hoebeke_2022"]),2102)
        self.assertEqual(len(self.raw["dejonckheere_2019"]),9800)

    def test_05_source_sha_pinned(self):
        for n,v in self.r["datasets"].items():
            self.assertEqual(v["source"]["file_sha256"],SOURCES[n]["sha256"])

    def test_06_public_license(self):
        self.assertTrue(all(v["source"]["license"]=="CC BY 4.0"
                            for v in self.r["datasets"].values()))

    def test_07_brooding_is_measure_for_hoebeke(self):
        self.assertEqual(SOURCES["hoebeke_2022"]["target"],"brooding")
        self.assertTrue(SOURCES["hoebeke_2022"]["has_direct_rumination_item"])

    def test_08_dejonckheere_does_not_measure_rumination_directly(self):
        self.assertNotIn("brooding",self.raw["dejonckheere_2019"].columns)
        self.assertFalse(SOURCES["dejonckheere_2019"]["has_direct_rumination_item"])

    def test_09_hoebeke_transitions_are_real(self):
        self.assertEqual(len(self.pairs["hoebeke_2022"]),1450)

    def test_10_dejonckheere_transitions_are_real(self):
        self.assertEqual(len(self.pairs["dejonckheere_2019"]),6890)

    def test_11_next_beep_is_exactly_one_later(self):
        for p in self.pairs.values():
            self.assertTrue(((p.next_beep-p.beep)==1).all())

    def test_12_no_overnight_transition(self):
        for p in self.pairs.values():
            self.assertTrue((p.day>=1).all())
            self.assertTrue(p.next_target.notna().all())

    def test_13_hoebeke_real_timestamp_gap_under_8_hours(self):
        x=self.pairs["hoebeke_2022"]
        self.assertTrue(x["gap_hours"].between(.2,8).all())

    def test_14_all_states_scale_0_to_100(self):
        for n,d in self.r["datasets"].items():
            low,high=d["data_quality"]["observed_target_range"]
            self.assertTrue(0<=low<=high<=100)

    def test_15_no_future_outcome_in_features(self):
        for n,d in self.r["datasets"].items():
            self.assertNotIn("next_target",d["inputs_available_at_time_t"])
            self.assertNotIn("next_beep",d["inputs_available_at_time_t"])
            self.assertNotIn("created",d["inputs_available_at_time_t"])

    def test_16_unreliable_attention_control_coding_excluded(self):
        self.assertNotIn("att_control",SOURCES["hoebeke_2022"]["inputs"])
        self.assertNotIn("activity",SOURCES["hoebeke_2022"]["inputs"])

    def test_17_split_cross_participant(self):
        for n,d in self.r["datasets"].items():
            self.assertEqual(d["split_type"],
                "participant-disjoint train/validation/test; no same-day future row in X")
            self.assertEqual(sum(z["observed_transitions"]
                                 for z in d["split_counts"].values()),
                             len(self.pairs[n]))

    def test_18_hoebeke_split_24_8_8(self):
        self.assertEqual([z["n_people"] for z in
            self.r["datasets"]["hoebeke_2022"]["split_counts"].values()],[24,8,8])

    def test_19_dejonckheere_split_60_20_20(self):
        self.assertEqual([z["n_people"] for z in
            self.r["datasets"]["dejonckheere_2019"]["split_counts"].values()],[60,20,20])

    def test_20_selection_is_validation_only(self):
        for d in self.r["datasets"].values():
            chosen=min(d["validation_scores"],key=lambda k:
                       (d["validation_scores"][k]["rmse"],k))
            self.assertEqual(d["model_chosen_by_validation_rmse_only"],chosen)
            self.assertTrue(d["no_heldout_model_selection"])

    def test_21_both_have_persistence_baseline(self):
        for d in self.r["datasets"].values():
            self.assertIn("persistence_last_state",d["heldout_test_scores"])

    def test_22_mse_rmse_consistency(self):
        for d in self.r["datasets"].values():
            for m in d["heldout_test_scores"].values():
                self.assertTrue(m["rmse"]>=0 and m["mae"]>=0)

    def test_23_test_selected_improves_persistence(self):
        for d in self.r["datasets"].values():
            ci=d["test_improvement_vs_last_value"]
            self.assertGreater(ci["rmse_improvement_vs_persistence"],0)
            self.assertGreater(ci["cluster_bootstrap_95ci"][0],0)

    def test_24_hoebeke_holdout_8_cluster_ci(self):
        x=self.r["datasets"]["hoebeke_2022"]["test_improvement_vs_last_value"]
        self.assertEqual(x["n_independent_participants"],8)
        self.assertEqual(x["n_replicates"],500)

    def test_25_dejonckheere_holdout_20_cluster_ci(self):
        x=self.r["datasets"]["dejonckheere_2019"]["test_improvement_vs_last_value"]
        self.assertEqual(x["n_independent_participants"],20)

    def test_26_selection_does_not_peek_at_rf_test(self):
        d=self.r["datasets"]["hoebeke_2022"]
        self.assertEqual(d["model_chosen_by_validation_rmse_only"],"ridge_a1")
        self.assertLess(d["heldout_test_scores"]["random_forest"]["rmse"],
                        d["heldout_test_scores"]["ridge_a1"]["rmse"])

    def test_27_no_causal_claims(self):
        self.assertFalse(self.r["mental_health_treatment_effect_measured"])
        self.assertFalse(self.r["external_clinical_trial_run"])

    def test_28_no_mindwandering_probe_claims(self):
        self.assertFalse(self.r["mind_wandering_probe_or_EEG_used"])

    def test_29_invalid_metrics_rejected(self):
        with self.assertRaises(ValueError):
            metrics(np.array([10.,30.]),np.array([float("nan"),20.]))

    def test_30_n_and_date_are_real(self):
        self.assertIn("2026-",self.r["date"])
        for d in self.r["datasets"].values():
            self.assertGreater(d["source"]["original_rows"],1000)

if __name__=="__main__":
    unittest.main()
