from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "config" / "schemas" / "affiliate-x-distribution-job-v1.json"
)


class AffiliateXDistributionJobSchemaTests(unittest.TestCase):
    def test_schema_accepts_one_public_effect_bound_job_and_rejects_unsafe_variants(self):
        self.assertTrue(SCHEMA.is_file(), f"missing queue contract: {SCHEMA}")
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        job = {
            "schema_version": 1,
            "receipt_type": "AFFILIATE_X_DISTRIBUTION_JOB",
            "state": "QUEUED",
            "job_id": "1" * 64,
            "effect_identity": "2" * 64,
            "placement_id": "elevenlabs-discovered-subtitle-translator-en-1",
            "owned_article_url": "https://aniccaai.com/blog/subtitle-translator",
            "content_sha256": "3" * 64,
            "experiment_lineage": {
                "kind": "EXPERIMENT",
                "decision_id": "4" * 64,
                "control_placement_id": "elevenlabs-discovered-subtitle-translator-en-1",
            },
            "target_x_account": "selawmqt",
            "cadence_class": "AFFILIATE_MONETIZATION",
            "policy_sha256": "5" * 64,
            "source_set_sha256": "6" * 64,
            "created_at": "2026-08-24T00:00:00+00:00",
            "private_tracking_url_state": "NOT_INCLUDED",
            "revenue_credit_state": "NO_REVENUE_CREDIT",
        }
        validator.validate(job)

        invalid = [
            {key: value for key, value in job.items() if key != "effect_identity"},
            {**job, "owned_article_url": "https://try.elevenlabs.io/private"},
            {**job, "target_x_account": "not a handle"},
            {**job, "private_tracking_url": "https://try.elevenlabs.io/private"},
            {**job, "experiment_lineage": {
                **job["experiment_lineage"], "decision_id": "not-a-hash",
            }},
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validator.validate(value)


if __name__ == "__main__":
    unittest.main()
