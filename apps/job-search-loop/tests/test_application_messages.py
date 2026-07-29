import json
import unittest
from pathlib import Path

from job_search_loop.application_messages import (
    MessageError,
    build_application_message,
    validate_application_message,
)


class ApplicationMessageTests(unittest.TestCase):
    def setUp(self):
        fact_ids = (
            "muit_agent_crm",
            "muit_genie_logs",
            "muit_rm_summary",
            "mufg",
            "anicca_consumer",
            "life_manager",
            "a10_marketing",
            "agent_club",
            "iclr",
        )
        self.profile = {
            "candidate": {"name": "Daisuke Narita"},
            "facts": [
                {
                    "id": fact_id,
                    "claim": f"Approved evidence for {fact_id}.",
                    "evidence": "fixture",
                }
                for fact_id in fact_ids
            ],
        }
        self.job = {
            "company": "Example AI",
            "role": "AI Product Manager",
            "grounded_role_reason": (
                "the role connects regulated AI delivery with customer adoption"
            ),
            "job_source_span": "Build AI products with enterprise customers.",
        }

    def _build(self, family):
        return build_application_message(
            self.profile,
            role_family=family,
            **self.job,
        )

    def test_all_role_templates_are_committed_and_versioned(self):
        path = (
            Path(__file__).parents[1]
            / "templates"
            / "application-messages.v1.json"
        )
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(value["version"], 1)
        self.assertEqual(
            set(value["templates"]),
            {"product", "gtm", "partnerships", "customer_success"},
        )

    def test_each_family_uses_only_its_grounded_fact_bundle(self):
        expected = {
            "product": (
                "muit_agent_crm",
                "mufg",
                "anicca_consumer",
                "life_manager",
            ),
            "gtm": (
                "mufg",
                "muit_rm_summary",
                "a10_marketing",
                "anicca_consumer",
            ),
            "partnerships": (
                "mufg",
                "muit_agent_crm",
                "iclr",
                "a10_marketing",
            ),
            "customer_success": (
                "muit_rm_summary",
                "muit_genie_logs",
                "agent_club",
                "anicca_consumer",
            ),
        }
        for family, fact_ids in expected.items():
            with self.subTest(family=family):
                value = self._build(family)
                self.assertEqual(tuple(value["fact_ids"]), fact_ids)
                for fact_id in fact_ids:
                    self.assertIn(
                        f"Approved evidence for {fact_id}.",
                        value["body"],
                    )
                validate_application_message(value, self.profile)

    def test_job_reason_requires_a_source_span(self):
        job = {**self.job, "job_source_span": " "}
        with self.assertRaisesRegex(MessageError, "source"):
            build_application_message(
                self.profile,
                role_family="product",
                **job,
            )

    def test_unknown_role_family_fails_closed(self):
        with self.assertRaisesRegex(MessageError, "role family"):
            self._build("generic_business")

    def test_validator_rejects_unapproved_or_missing_claims(self):
        value = self._build("product")
        value["fact_ids"].append("invented")
        with self.assertRaisesRegex(MessageError, "fact"):
            validate_application_message(value, self.profile)

        value = self._build("product")
        value["body"] = value["body"].replace(
            "Approved evidence for mufg.", ""
        )
        with self.assertRaisesRegex(MessageError, "claim"):
            validate_application_message(value, self.profile)

    def test_schema_is_strict_and_matches_output_contract(self):
        path = (
            Path(__file__).parents[1]
            / "schemas"
            / "application-message.v1.schema.json"
        )
        schema = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["required"]),
            {
                "version",
                "role_family",
                "company",
                "role",
                "body",
                "fact_ids",
                "job_source_span",
            },
        )


if __name__ == "__main__":
    unittest.main()
