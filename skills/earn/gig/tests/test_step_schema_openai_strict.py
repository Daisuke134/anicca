"""The step schema must satisfy OpenAI structured-output strictness.

X24, measured 2026-07-28: B2 -- the application lane, the money entrance -- failed
every four hours from 20:31 with HTTP 400:

    invalid_json_schema: In context=('properties','applications','items'),
    'required' is required to be supplied and to be an array including every key
    in properties. Missing 'category'.

X8b had added applications[] with required=['request_id'] on purpose, so that a
missing category could never fail a step whose application had already succeeded in
the browser. That intent is right, but OpenAI's strict mode does not express
optionality by omission from `required` -- it demands every key be listed, and
optionality be carried by a nullable type. The result was worse than the thing we
were avoiding: not a lane that under-reports, but a lane that cannot run at all.

This pins the rule for the whole file, not just the row that broke, because the next
person adding a property will otherwise reintroduce it.
"""

import json
import unittest
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "gig_b2_result.schema.json"


def objects_with_properties(node, path="$"):
    if isinstance(node, dict):
        if isinstance(node.get("properties"), dict):
            yield path, node
        for key, value in node.items():
            yield from objects_with_properties(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from objects_with_properties(value, f"{path}[{index}]")


class StepSchemaStrictTest(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_every_property_is_listed_in_required(self):
        for path, node in objects_with_properties(self.schema):
            with self.subTest(path=path):
                self.assertEqual(
                    set(node["properties"]),
                    set(node.get("required") or []),
                    f"{path}: OpenAI strict mode rejects a schema whose required omits "
                    "a property; express optionality with a nullable type instead",
                )

    def test_optional_application_fields_are_nullable(self):
        items = self.schema["properties"]["applications"]["items"]
        # request_id is the identity: required AND non-null, or the row cannot be
        # attributed to a posting at all.
        self.assertEqual(items["properties"]["request_id"]["type"], "string")
        self.assertEqual(
            items["properties"]["bucket"]["enum"],
            ["single", "retainer"],
        )
        for name in (
            "category",
            "title",
            "price_jpy",
            "deliver_date",
            "url",
            "compensation_type",
            "weekly_days",
            "weekly_hours_min",
            "weekly_hours_max",
        ):
            with self.subTest(field=name):
                self.assertIn(
                    "null", items["properties"][name]["type"],
                    f"{name} must stay omittable in substance: a real application that "
                    "lacks it must still be reportable",
                )

    def test_application_report_cannot_claim_more_than_hourly_hard_cap(self):
        applications = self.schema["properties"]["applications"]
        self.assertEqual(applications.get("maxItems"), 7)

    def test_b2_reports_how_many_eligible_jobs_it_observed(self):
        eligible = self.schema["properties"]["eligible_count"]
        self.assertIn("null", eligible["type"])
        self.assertIn("eligible_count", self.schema["required"])

    def test_b2_reports_structured_candidate_facts_for_the_code_gate(self):
        current = self.schema["properties"]["current_b2"]
        self.assertEqual(current["type"], "object")
        self.assertEqual(
            set(current["required"]),
            {
                "context_path",
                "context_sha256",
                "marketplace_url",
                "marketplace_screenshot_path",
                "marketplace_live_dom_path",
                "inspected_requests",
                "search_sources",
            },
        )
        inspected = current["properties"]["inspected_requests"]
        fields = inspected["items"]["properties"]
        self.assertEqual(
            set(fields),
            {
                "request_id",
                "bucket",
                "url",
                "applicants",
                "contracted",
                "budget_max_jpy",
                "compensation_type",
                "compensation_min_jpy",
                "compensation_max_jpy",
                "weekly_days",
                "weekly_hours_min",
                "weekly_hours_max",
                "remote",
                "synchronous_interview_required",
                "human_identity_required",
                "accepting_applications",
                "outcome",
                "reason",
            },
        )
        self.assertEqual(
            set(inspected["items"]["required"]),
            set(fields),
            "OpenAI strict requires every observation field; unknown values are nullable",
        )
        sources = current["properties"]["search_sources"]
        self.assertEqual(sources["maxItems"], 100)
        self.assertEqual(
            set(sources["items"]["required"]),
            set(sources["items"]["properties"]),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
