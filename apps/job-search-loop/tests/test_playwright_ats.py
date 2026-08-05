import importlib.util
import unittest


class PlaywrightAtsTests(unittest.TestCase):
    def test_builds_contact_answers_without_legal_inference(self):
        self.assertIsNotNone(
            importlib.util.find_spec("job_search_loop.playwright_ats"),
            "release-contained Playwright ATS adapter is missing",
        )
        from job_search_loop.playwright_ats import grounded_profile_answers

        answers = grounded_profile_answers(
            {
                "candidate": {
                    "name": "Daisuke Narita",
                    "application_email": "candidate@example.test",
                    "phone": "+81-00-0000-0000",
                    "phone_status": "verified",
                    "linkedin_url": "https://www.linkedin.com/in/example",
                    "github_url": "https://github.com/example",
                    "nationality": None,
                    "work_authorizations": [],
                }
            }
        )

        self.assertEqual(
            set(answers),
            {"full_name", "first_name", "last_name", "email", "phone", "linkedin", "github"},
        )
        self.assertEqual(answers["full_name"]["fact_ids"], ["profile.name"])
        self.assertNotIn("nationality", answers)
        self.assertNotIn("work_authorization", answers)

    def test_selects_highest_ranked_supported_candidate(self):
        from job_search_loop.playwright_ats import select_pre_submit_candidate

        result = select_pre_submit_candidate(
            {
                "candidates": [
                    {
                        "official_url": "https://careers.example.test/unknown",
                        "ranking_ready": True,
                        "ranking": {"score": 100},
                        "portfolio_bucket": "dream",
                    },
                    {
                        "official_url": "https://jobs.ashbyhq.com/acme/strong",
                        "ranking_ready": True,
                        "ranking": {"score": 80},
                        "portfolio_bucket": "strong_fit",
                    },
                    {
                        "official_url": "https://jobs.ashbyhq.com/acme/dream",
                        "ranking_ready": True,
                        "ranking": {"score": 95},
                        "portfolio_bucket": "dream",
                    },
                ]
            }
        )

        self.assertEqual(result["official_url"], "https://jobs.ashbyhq.com/acme/dream")


if __name__ == "__main__":
    unittest.main()
