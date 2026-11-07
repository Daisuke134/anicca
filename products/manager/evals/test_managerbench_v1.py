"""G1 contract regression tests: real P09 receipts plus synthetic HBCP/Qwen records."""
import copy
import json
import unittest
from pathlib import Path

from managerbench_v1 import build_report

ROOT = Path(__file__).resolve().parents[3]
P09 = ROOT / "docs/research/manager/masterclass/2026-11-04-p04-causal/evidence/P09-2_TO_P09-5_REAL_TWO_DOMAIN_EVAL_20261107.json"
NATURE = ROOT / "docs/research/manager/masterclass/2026-11-04-p04-causal/evidence/P09-1_NATURE_FIG1_RESULT_20261107.json"

def sample():
    nature = json.loads(NATURE.read_text())
    p09 = json.loads(P09.read_text())
    hbcp = {
        "sha256":"eec4ba6ffc51961fda1308f690a97a60111d93858fa67ca19ffd4392fd49679b",
        "n_studies":405, "n_trial_arms":971, "n_numeric_features":93,
        "study_holdout":"5-fold non-overlapping study groups, fixed deterministic greedy balance; training-only median impute/scale",
        "train_mean":{"mae":9.98677813675426,"rmse":13.392746174542356,"n":971},
        "ridge_alpha30":{"mae":9.924668001628204,"rmse":13.298148614232657,"n":971},
        "study_cluster_bootstrap_95ci_mae_improvement":[-.46087866722271015,.510891571449389],
        "folds":[{"n_test_arms":195}]+[{"n_test_arms":194}]*4,
    }
    qwen = {
        "status":"REAL_QWEN3_4B_CPU_TEXT_ONLY_HUMAN_AGGREGATE_EVAL",
        "model_forward_pass_executed":True,
        "model_sha256":"2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e",
        "n_cases":24,
        "file_sha256":{
            "score.csv":"aad13533093fe9d2fcf80d0299c1abcaf751d3016e7d897b37604924abf56568"},
        "scores":{
            "n_total":24,"n_human_non_tied":18,"n_ties":6,"n_model_invalid":0,
            "model_strict_win_accuracy_including_invalid":10/18,
            "baseline_strict_win_accuracy":11/18,
        }
    }
    return nature,p09,hbcp,qwen

class ManagerBenchContractTests(unittest.TestCase):
    def test_real_nature_and_mame_distinct_units(self):
        report=build_report(*sample())
        self.assertEqual(report["schema"],"managerbench.v1")
        self.assertEqual(len(report["tracks"]),4)
        self.assertEqual(len(set(t["unit"] for t in report["tracks"])),4)
        self.assertEqual(report["global_accuracy"],None)
        by={t["task_id"]:t for t in report["tracks"]}
        self.assertAlmostEqual(by["nature_effect"]["candidate"],.0802566267)
        self.assertEqual(by["mame_rating"]["status"],"NOT_DEMONSTRATED")
        self.assertEqual(by["hbcp_quit_rate"]["n_groups"],405)
        self.assertEqual(by["mame_qwen_pairwise"]["status"],"NOT_DEMONSTRATED")
        self.assertEqual(by["mame_qwen_pairwise"]["candidate"],10/18)
        self.assertEqual(by["mame_qwen_pairwise"]["baseline"],11/18)

    def test_wrong_hbcp_hash_rejected(self):
        values=list(sample())
        values[2]["sha256"]="0"*64
        with self.assertRaises(ValueError):build_report(*values)

    def test_nonfinite_and_out_of_range_rejected(self):
        for bad in (float("nan"),float("inf"),-1.):
            values=list(sample());values[2]["ridge_alpha30"]["mae"]=bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):build_report(*values)

    def test_meme_context_overlap_rejected(self):
        values=list(sample())
        ids=values[1]["p09_5_meme_distinct_task_holdout"]
        ids["test_ids"][0]=ids["train_ids"][0]
        with self.assertRaisesRegex(ValueError,"split"):build_report(*values)

    def test_qwen_no_forward_or_invalid_score_rejected(self):
        values=list(sample());values[3]["model_forward_pass_executed"]=False
        with self.assertRaises(ValueError):build_report(*values)
        values=list(sample());values[3]["scores"]["model_strict_win_accuracy_including_invalid"]=1.1
        with self.assertRaises(ValueError):build_report(*values)

    def test_missing_qwen_is_explicit_not_model_success(self):
        nature,p09,hbcp,_=sample()
        report=build_report(nature,p09,hbcp,None)
        self.assertEqual(len(report["tracks"]),3)
        self.assertNotIn("mame_qwen_pairwise",[t["task_id"] for t in report["tracks"]])

    def test_hbcp_fold_counts_must_match_971(self):
        values=list(sample());values[2]["folds"][0]["n_test_arms"]=500
        with self.assertRaisesRegex(ValueError,"fold"):build_report(*values)

    def test_model_delta_is_metric_specific(self):
        report=build_report(*sample())
        for task in report["tracks"]:
            expected=(task["baseline"]-task["candidate"]) if task["lower_is_better"] else (task["candidate"]-task["baseline"])
            self.assertAlmostEqual(task["delta"],expected)
        self.assertFalse(report["all_tracks_better_than_baseline"])

if __name__=="__main__":
    unittest.main()
