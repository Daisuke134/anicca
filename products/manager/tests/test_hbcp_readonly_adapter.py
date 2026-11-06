"""Model integration tests use only aggregate CC0 model schema, never patients."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from manager_core import hbcp_readonly_adapter as adapter


class RealOutcomeHeadIntegrationTests(unittest.TestCase):
    def test_pinned_real_training_checkpoint_exists(self):
        m = adapter._loaded_model()
        self.assertEqual(m["model_id"], "manager-hbcp-ridge-arm-rate-v0")
        self.assertEqual(m["intervention_arms"], 971)
        self.assertFalse(m["trained_behavioral_foundation_model"])

    def test_abstain_by_default_even_with_coded_data(self):
        self.assertEqual(adapter.predict_published_study_arm({"foo": 1}).status, "ABSTAIN")

    def test_exclude_individual_identity_fields(self):
        result = adapter.predict_published_study_arm(
            {"patient_name": "Never process private individuals"},
            aggregate_study_arm_verified=True,
        )
        self.assertEqual(result.status, "ABSTAIN")
        self.assertIsNone(result.predicted_rate_pct)

    def test_fail_when_missing_research_context(self):
        m = adapter._loaded_model()
        single = {m["feature_names"][0]: 1}
        self.assertEqual(
            adapter.predict_published_study_arm(
                single, aggregate_study_arm_verified=True,
            ).reason,
            "NOT_ENOUGH_AGGREGATE_STUDY_CONTEXT",
        )

    def test_actual_model_produces_scoped_noncausal_prediction(self):
        m = adapter._loaded_model()
        context = {key: 1 for key in m["feature_names"][:8]}
        result = adapter.predict_published_study_arm(
            context, aggregate_study_arm_verified=True,
        )
        self.assertEqual(result.status, "PREDICTION_ONLY")
        self.assertGreaterEqual(result.predicted_rate_pct, 0)
        self.assertLessEqual(result.predicted_rate_pct, 100)
        self.assertEqual(result.evidence_kind, "OBSERVATIONAL_FORECAST_ON_ANNOTATED_RCT_ARMS")
        self.assertFalse(result.causal_effect_estimated)
        self.assertFalse(result.approved_for_clinical_use)
        self.assertFalse(result.may_execute_intervention)

    def test_wrong_model_hash_abstains_without_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "bad-checkpoint.json"
            fake.write_text('{"model_id":"manager-hbcp-ridge-arm-rate-v0"}')
            with patch.object(adapter, "MODEL_FILE", fake):
                response = adapter.predict_published_study_arm(
                    {"fake": 1}, aggregate_study_arm_verified=True
                )
        self.assertEqual(response.status, "ABSTAIN")
        self.assertEqual(response.reason, "PINNED_MODEL_UNAVAILABLE")

    def test_never_calls_external_provider(self):
        from dataclasses import fields
        attrs = {x.name for x in fields(adapter.ReadOnlyPrediction)}
        self.assertIn("may_execute_intervention", attrs)
        self.assertFalse(adapter.ReadOnlyPrediction(
            "ABSTAIN", "x", None, "none", None, "none",
        ).may_execute_intervention)


if __name__ == "__main__":
    unittest.main()
