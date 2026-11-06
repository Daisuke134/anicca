"""Synthetic *software tests* for plain JSON outcome-model weights."""
import unittest
from manager_hbcp_ridge_head import MODEL_ID, predict_json


class ModelSerializationTests(unittest.TestCase):
    def setUp(self):
        self.model = {
            "model_id": MODEL_ID,
            "feature_names": ["bct_a", "context_b"],
            "median_imputation": [0.3, 0.4],
            "missing_indicator_feature_indices": [1],
            "coefficients": [2, 3, 4],
            "intercept": 10,
            "individual_level_predictions": False,
            "causal_effect_estimated": False,
            "trained_behavioral_foundation_model": False,
        }

    def test_numeric_and_missing(self):
        self.assertAlmostEqual(
            predict_json(self.model, {"bct_a": 1, "context_b": None}), 17.2
        )

    def test_clamp_to_meaningful_percentage(self):
        m = {**self.model, "intercept": 200}
        self.assertEqual(predict_json(m, {"bct_a": 0, "context_b": 0}), 100)
        m = {**self.model, "intercept": -200}
        self.assertEqual(predict_json(m, {"bct_a": 0, "context_b": 0}), 0)

    def test_reject_extra_identity_or_labels(self):
        with self.assertRaises(ValueError):
            predict_json(self.model, {"doc": "not-allowed", "bct_a": 1})

    def test_reject_unknown_checkpoint(self):
        with self.assertRaises(ValueError):
            predict_json({**self.model, "model_id": "fake"}, {"bct_a": 1})

    def test_reject_invalid_weight_shapes(self):
        with self.assertRaises(ValueError):
            predict_json({**self.model, "coefficients": [2]}, {"bct_a": 1})

    def test_no_misleading_foundation_or_therapy_claim(self):
        self.assertIs(self.model["trained_behavioral_foundation_model"], False)
        self.assertIs(self.model["causal_effect_estimated"], False)
        self.assertIs(self.model["individual_level_predictions"], False)


if __name__ == "__main__":
    unittest.main()
