import json
import unittest
from pathlib import Path

from job_search_loop.ats import detect_provider, evaluate_snapshot


FIXTURES = Path(__file__).parent / "fixtures" / "ats"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class AtsReadinessTests(unittest.TestCase):
    def test_provider_detection_uses_hostname_boundaries(self):
        cases = {
            "https://jobs.ashbyhq.com/acme/role/application": "ashby",
            "https://app.ashbyhq.com/applicationForm": "ashby",
            "https://acme.wd5.myworkdayjobs.com/jobs/role": "workday",
            "https://wd1.myworkdaysite.com/acme/job/role": "workday",
            "https://ashbyhq.com.example.test/role": "generic",
            "https://careers.example.com/role": "generic",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(detect_provider(url), expected)

    def test_ashby_commit_replays_as_ready_without_domcontentloaded(self):
        self.assertEqual(
            evaluate_snapshot(load_fixture("ashby-application-surface.json")),
            {
                "provider": "ashby",
                "ready": True,
                "surface": "ashby_application",
                "frame_index": 0,
                "wait_until": "commit",
                "blockers": [],
            },
        )

    def test_ashby_requires_email_resume_and_submit_controls(self):
        snapshot = load_fixture("ashby-application-surface.json")
        snapshot["frames"][0]["controls"] = [
            control
            for control in snapshot["frames"][0]["controls"]
            if control["type"] != "email"
        ]
        result = evaluate_snapshot(snapshot)
        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"], ["application_surface_not_found"])

    def test_workday_job_surface_replays_as_ready(self):
        self.assertEqual(
            evaluate_snapshot(load_fixture("workday-job-surface.json")),
            {
                "provider": "workday",
                "ready": True,
                "surface": "workday_job",
                "frame_index": 0,
                "wait_until": "commit",
                "blockers": [],
            },
        )

    def test_committed_page_without_application_surface_fails_closed(self):
        self.assertEqual(
            evaluate_snapshot(load_fixture("committed-without-surface.json")),
            {
                "provider": "ashby",
                "ready": False,
                "surface": "none",
                "frame_index": None,
                "wait_until": "commit",
                "blockers": ["application_surface_not_found"],
            },
        )

    def test_uncommitted_navigation_fails_before_surface_evaluation(self):
        snapshot = load_fixture("ashby-application-surface.json")
        snapshot["navigation_committed"] = False
        result = evaluate_snapshot(snapshot)
        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"], ["navigation_not_committed"])

    def test_malformed_snapshot_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "frames must be a non-empty list"):
            evaluate_snapshot(
                {
                    "version": 1,
                    "url": "https://jobs.ashbyhq.com/example/application",
                    "navigation_committed": True,
                    "frames": [],
                }
            )


if __name__ == "__main__":
    unittest.main()
