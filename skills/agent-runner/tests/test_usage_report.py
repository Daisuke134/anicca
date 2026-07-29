import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "usage_report.py"


def load_module():
    spec = importlib.util.spec_from_file_location("usage_report", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load usage_report")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UsageReportTest(unittest.TestCase):
    def setUp(self):
        self.report = load_module()

    def test_daily_summary_groups_loop_and_preserves_unavailable_attempts(self):
        rows = [
            {
                "timestamp": "2026-07-22T15:30:00+00:00",
                "loop": "gig",
                "provider": "codex",
                "model": "gpt-5.6-terra",
                "effort": "medium",
                "status": "success",
                "duration_ms": 100,
                "tokens": {
                    "input": 100,
                    "cached_input": 60,
                    "output": 10,
                    "total": 110,
                },
                "measurement": "provider_reported",
                "provider_cost_usd": 0.25,
                "cost_basis": "api_equivalent_estimate",
            },
            {
                "timestamp": "2026-07-22T16:00:00+00:00",
                "loop": "gig",
                "provider": "codex",
                "model": "gpt-5.6-terra",
                "effort": "medium",
                "status": "failed",
                "duration_ms": 200,
                "tokens": {
                    "input": None,
                    "cached_input": None,
                    "output": None,
                    "total": None,
                },
                "measurement": "unavailable",
                "provider_cost_usd": None,
            },
        ]

        summary = self.report.summarize_events(rows, "2026-07-23")

        self.assertEqual(summary["totals"]["total_tokens"], 110)
        self.assertEqual(summary["totals"]["unavailable_attempts"], 1)
        self.assertEqual(summary["groups"][0]["loop"], "gig")
        self.assertEqual(summary["totals"]["api_equivalent_cost_usd"], 0.25)
        self.assertEqual(summary["totals"]["actual_billed_cost_usd"], 0.0)

    def test_markdown_labels_estimates_and_actual_bills_separately(self):
        summary = self.report.summarize_events([], "2026-07-23")

        rendered = self.report.render_markdown(summary)

        self.assertIn("API-equivalent estimate USD", rendered)
        self.assertIn("Actual billed USD", rendered)


if __name__ == "__main__":
    unittest.main()
