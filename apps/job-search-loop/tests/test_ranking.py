import json
import unittest
from pathlib import Path

from job_search_loop.jobs import Job
from job_search_loop.ranking import evaluate


class RankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parent / "fixtures" / "jobs.json"
        cls.jobs = {
            item.pop("name"): Job(**item)
            for item in json.loads(path.read_text(encoding="utf-8"))
        }

    def test_tokyo_ai_role_is_eligible_with_component_score(self):
        result = evaluate(self.jobs["tokyo_ai"])
        self.assertTrue(result.eligible)
        self.assertEqual(result.score, 85)
        self.assertEqual(result.components["ai_skill"], 30)
        self.assertEqual(result.components["enterprise"], 20)

    def test_global_remote_unknown_compensation_is_neutral_not_zero(self):
        result = evaluate(self.jobs["global_remote"])
        self.assertTrue(result.eligible)
        self.assertEqual(result.components["compensation"], 5)
        self.assertGreaterEqual(result.score, 75)

    def test_us_only_is_hard_rejected(self):
        result = evaluate(self.jobs["us_only"])
        self.assertFalse(result.eligible)
        self.assertIn("not_available_from_japan", result.reasons)

    def test_clearance_is_hard_rejected(self):
        result = evaluate(self.jobs["clearance"])
        self.assertFalse(result.eligible)
        self.assertIn("clearance_required", result.reasons)

    def test_known_compensation_below_floor_is_hard_rejected(self):
        result = evaluate(self.jobs["low_pay"])
        self.assertFalse(result.eligible)
        self.assertIn("compensation_below_floor", result.reasons)

    def test_pay_above_current_salary_but_below_target_remains_eligible(self):
        job = Job(
            company="Data AI",
            title="Generative AI Engineer",
            url="https://jobs.example.com/genai",
            location="Tokyo",
            japan_eligible=True,
            compensation_min_jpy=5_500_000,
            clearance_required=False,
            skills=["agents", "databricks"],
            domains=["enterprise_ai"],
        )
        result = evaluate(job)
        self.assertTrue(result.eligible)
        self.assertEqual(result.components["compensation"], 7)

    def test_generic_non_ai_role_does_not_auto_apply(self):
        job = Job(
            company="Generic",
            title="Backend Engineer",
            url="https://jobs.example.com/backend",
            location="Tokyo",
            japan_eligible=True,
            compensation_min_jpy=9_000_000,
            clearance_required=False,
            skills=["python"],
            domains=[],
        )
        result = evaluate(job)
        self.assertFalse(result.eligible)
        self.assertLess(result.score, 75)

    def test_ai_literate_business_role_is_eligible(self):
        job = Job(
            company="Enterprise AI",
            title="Strategic Partnerships Manager",
            url="https://jobs.example.com/partnerships",
            location="Tokyo",
            japan_eligible=True,
            compensation_min_jpy=7_000_000,
            clearance_required=False,
            skills=["llm", "agentforce", "product"],
            domains=["enterprise_ai"],
        )
        result = evaluate(job)
        self.assertTrue(result.eligible)
        self.assertEqual(result.components["ai_skill"], 30)
        self.assertGreaterEqual(result.score, 75)

    def test_generic_business_role_without_ai_evidence_is_rejected(self):
        job = Job(
            company="Generic",
            title="Business Development Manager",
            url="https://jobs.example.com/business",
            location="Tokyo",
            japan_eligible=True,
            compensation_min_jpy=9_000_000,
            clearance_required=False,
            skills=["sales", "partnerships"],
            domains=[],
        )
        result = evaluate(job)
        self.assertFalse(result.eligible)
        self.assertEqual(result.components["ai_skill"], 0)
        self.assertIn("score_below_threshold", result.reasons)

    def test_source_spans_are_required_for_model_extracted_fields(self):
        payload = {
            "company": "X",
            "title": "AI Engineer",
            "url": "https://jobs.example.com/x",
            "location": "Tokyo",
            "japan_eligible": True,
            "compensation_min_jpy": None,
            "clearance_required": False,
            "skills": ["agents"],
            "domains": ["enterprise_ai"],
            "extracted": {"japan_eligible": {"value": True}},
        }
        with self.assertRaisesRegex(ValueError, "source_span"):
            Job.from_extracted(payload)


if __name__ == "__main__":
    unittest.main()
