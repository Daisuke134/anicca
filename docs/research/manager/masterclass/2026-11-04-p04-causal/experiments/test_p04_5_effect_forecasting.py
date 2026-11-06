"""P04-5 synthetic frozen study-holdout evaluation tests."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from p04_5_effect_forecasting import (
    SPLITS, build_world, make_release, freeze_predictions, score_frozen, read_rows,
    features, ridge_fit,
)


class P045Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.temp.name)
        make_release(cls.out)
        freeze_predictions(cls.out)
        cls.score = score_frozen(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exact_split_sizes(self):
        rows = build_world()
        self.assertEqual(len(rows), sum(SPLITS.values()))
        self.assertEqual({key: sum(row["split"] == key for row in rows) for key in SPLITS}, SPLITS)

    def test_study_level_holdouts_disjoint(self):
        paths = ["P04-5_TRAIN_SYNTHETIC.csv", "P04-5_VALIDATION_SYNTHETIC.csv",
                 "P04-5_HOLDOUT_METADATA_SYNTHETIC.csv"]
        sets = [{r["study_id"] for r in read_rows(self.out / p)} for p in paths]
        self.assertFalse(sets[0] & sets[1])
        self.assertFalse(sets[0] & sets[2])
        self.assertFalse(sets[1] & sets[2])

    def test_holdout_public_metadata_excludes_gold(self):
        metadata = read_rows(self.out / "P04-5_HOLDOUT_METADATA_SYNTHETIC.csv")
        self.assertEqual(len(metadata), 60)
        self.assertNotIn("observed_trial_effect", metadata[0])
        self.assertNotIn("oracle_effect", metadata[0])

    def test_deterministic_world(self):
        self.assertEqual(build_world(), build_world())

    def test_predictions_frozen_hash(self):
        receipt = json.loads((self.out / "P04-5_FREEZE_RECEIPT.json").read_text())
        self.assertEqual(receipt["prediction_sha256"], self.score["prediction_sha256"])
        self.assertFalse(receipt["gold_read_during_prediction"])

    def test_tampering_refused(self):
        path = self.out / "P04-5_FROZEN_PREDICTIONS_SYNTHETIC.csv"
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n")
            with self.assertRaises(ValueError):
                score_frozen(self.out)
        finally:
            path.write_bytes(original)

    def test_three_baselines_and_two_holdout_domains(self):
        scores = self.score["metrics_by_split"]
        self.assertEqual(scores["in_domain"]["n_studies"], 30)
        self.assertEqual(scores["new_domain"]["n_studies"], 30)
        for part in ("in_domain", "new_domain"):
            self.assertTrue(all(k in scores[part] for k in ("ridge", "mean", "zero")))

    def test_learned_model_beats_mean_in_domain(self):
        z = self.score["metrics_by_split"]["in_domain"]
        self.assertLess(z["ridge"]["rmse"], z["mean"]["rmse"])

    def test_known_label_not_used_as_feature(self):
        rows = read_rows(self.out / "P04-5_TRAIN_SYNTHETIC.csv")
        original = features(rows)
        rows[0]["observed_trial_effect"] = "9999"
        np.testing.assert_array_equal(original, features(rows))

    def test_ridge_regularization_runs(self):
        rows = read_rows(self.out / "P04-5_TRAIN_SYNTHETIC.csv")
        x = features(rows)
        y = np.array([float(r["observed_trial_effect"]) for r in rows])
        pred = x @ ridge_fit(x, y, 0.01)
        self.assertTrue(np.isfinite(pred).all())

    def test_public_validation_status_explicit(self):
        self.assertEqual(self.score["public_rct_out_of_study_validation"], "NOT PERFORMED")


if __name__ == "__main__":
    unittest.main()
