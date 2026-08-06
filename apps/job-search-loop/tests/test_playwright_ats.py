import importlib.util
import unittest


class PlaywrightAtsTests(unittest.TestCase):
    def test_capture_snapshot_collects_group_labels_without_values(self):
        from job_search_loop.playwright_ats import capture_snapshot

        class Locator:
            def evaluate_all(self, script):
                self.script = script
                return [
                    {
                        "tag": "button",
                        "type": "button",
                        "role": "radio",
                        "label": "Yes",
                        "name": "authorized",
                        "text": "Yes",
                        "group_label": "Are you authorized to work in Japan? *",
                        "required": True,
                    }
                ]

        class Frame:
            url = "https://jobs.ashbyhq.com/example/application"

            def __init__(self):
                self.control_locator = Locator()

            def locator(self, selector):
                return self.control_locator

        class Page:
            url = "https://jobs.ashbyhq.com/example/application"

            def __init__(self):
                self.frames = [Frame()]

        page = Page()
        snapshot = capture_snapshot(page, navigation_committed=True)

        self.assertEqual(
            snapshot["frames"][0]["controls"][0]["group_label"],
            "Are you authorized to work in Japan? *",
        )
        script = page.frames[0].control_locator.script
        self.assertIn("group_label", script)
        self.assertIn("needsGroup", script)
        self.assertIn("choiceText", script)
        self.assertIn("groupLabel.includes('?')", script)
        self.assertNotIn("n.value", script)

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
                    "phone_status": "verified_from_sent_resume",
                    "linkedin_url": "https://www.linkedin.com/in/example",
                    "github_url": "https://github.com/example",
                    "base": "Tokyo, Japan",
                    "nationality": None,
                    "work_authorizations": [],
                }
            }
        )

        self.assertEqual(
            set(answers),
            {"full_name", "first_name", "last_name", "email", "phone", "linkedin", "github", "location"},
        )
        self.assertEqual(answers["full_name"]["fact_ids"], ["profile.name"])
        self.assertEqual(answers["location"]["fact_ids"], ["profile.base"])
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

    def test_ranks_multiple_supported_candidates_for_same_pass_fallback(self):
        from job_search_loop.playwright_ats import ranked_pre_submit_candidates

        result = ranked_pre_submit_candidates(
            {
                "candidates": [
                    {
                        "official_url": "https://jobs.ashbyhq.com/acme/strong",
                        "ranking_ready": True,
                        "ranking": {"score": 88},
                        "portfolio_bucket": "strong_fit",
                    },
                    {
                        "official_url": "https://jobs.ashbyhq.com/acme/dream-low",
                        "ranking_ready": True,
                        "ranking": {"score": 90},
                        "portfolio_bucket": "dream",
                    },
                    {
                        "official_url": "https://jobs.ashbyhq.com/acme/dream-high",
                        "ranking_ready": True,
                        "ranking": {"score": 95},
                        "portfolio_bucket": "dream",
                    },
                    {
                        "official_url": "https://careers.example.test/unsupported",
                        "ranking_ready": True,
                        "ranking": {"score": 100},
                        "portfolio_bucket": "dream",
                    },
                ]
            },
            limit=3,
        )

        self.assertEqual(
            [item["official_url"] for item in result],
            [
                "https://jobs.ashbyhq.com/acme/dream-high",
                "https://jobs.ashbyhq.com/acme/dream-low",
                "https://jobs.ashbyhq.com/acme/strong",
            ],
        )

    def test_attempts_next_candidate_after_block_and_stops_at_claim_ready(self):
        from job_search_loop.playwright_ats import attempt_ranked_candidates

        visited = []

        def attempt(candidate):
            visited.append(candidate["official_url"])
            if len(visited) == 1:
                return {"claim_ready": False, "blockers": ["phone"]}
            return {"claim_ready": True, "blockers": []}

        result = attempt_ranked_candidates(
            [
                {"official_url": "https://jobs.ashbyhq.com/acme/first"},
                {"official_url": "https://jobs.ashbyhq.com/acme/second"},
                {"official_url": "https://jobs.ashbyhq.com/acme/third"},
            ],
            attempt,
        )

        self.assertEqual(
            visited,
            [
                "https://jobs.ashbyhq.com/acme/first",
                "https://jobs.ashbyhq.com/acme/second",
            ],
        )
        self.assertEqual(result["attempted_count"], 2)
        self.assertEqual(result["blocked"], ["candidate_1:phone", "pre_submit_claim_ready_no_submit"])

    def test_candidate_exception_is_recorded_and_next_candidate_runs(self):
        from job_search_loop.playwright_ats import attempt_ranked_candidates

        visited = []

        def attempt(candidate):
            visited.append(candidate["official_url"])
            if len(visited) == 1:
                raise RuntimeError("provider-specific failure")
            return {"claim_ready": False, "blockers": ["start_date"]}

        result = attempt_ranked_candidates(
            [
                {"official_url": "https://jobs.ashbyhq.com/acme/first"},
                {"official_url": "https://jobs.ashbyhq.com/acme/second"},
            ],
            attempt,
        )

        self.assertEqual(len(visited), 2)
        self.assertEqual(
            result["blocked"],
            ["candidate_1:error:RuntimeError", "candidate_2:start_date"],
        )


if __name__ == "__main__":
    unittest.main()
