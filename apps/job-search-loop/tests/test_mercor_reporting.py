import unittest

from job_search_loop.mercor_reporting import build_pass_message


class MercorReportingTests(unittest.TestCase):
    def test_message_is_compact_grounded_and_redacts_private_details(self):
        message = build_pass_message(
            run_id="mercor-test-1",
            result={
                "status": "observed_no_action",
                "inspected_listings": [
                    {
                        "title": "Data quality Evaluator",
                        "decision": "not_submitted_missing_fact",
                    }
                ],
                "submitted": [],
                "needs_human": [],
                "blocked": [],
            },
        )

        self.assertIn("Codex::: Mercor pass mercor-test-1", message)
        self.assertIn("observed_no_action", message)
        self.assertIn("Data quality Evaluator", message)
        self.assertNotIn("profile.json", message)
        self.assertNotIn("resume.pdf", message)

    def test_message_reports_submit_and_human_routes(self):
        message = build_pass_message(
            run_id="mercor-test-2",
            result={
                "status": "submitted",
                "inspected_listings": [],
                "submitted": [{"title": "Japanese Evaluator"}],
                "needs_human": ["interview_required"],
                "blocked": [],
            },
        )

        self.assertIn("submitted=Japanese Evaluator", message)
        self.assertIn("needs_human=interview_required", message)


if __name__ == "__main__":
    unittest.main()
