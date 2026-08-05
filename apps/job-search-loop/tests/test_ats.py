import json
import unittest
from pathlib import Path

from job_search_loop.ats import detect_provider, evaluate_snapshot


FIXTURES = Path(__file__).parent / "fixtures" / "ats"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class AtsReadinessTests(unittest.TestCase):
    def test_five_supported_ats_build_grounded_non_submit_fill_plans(self):
        from job_search_loop import ats

        self.assertTrue(
            hasattr(ats, "build_non_submit_fill_plan"),
            "ATS non-submit fill planner is missing",
        )
        urls = {
            "ashby": "https://jobs.ashbyhq.com/acme/role/application",
            "greenhouse": "https://job-boards.greenhouse.io/acme/jobs/123",
            "lever": "https://jobs.lever.co/acme/role-123",
            "workable": "https://apply.workable.com/acme/j/ROLE123/",
            "workday": "https://acme.wd5.myworkdayjobs.com/jobs/role",
        }
        answers = {
            "first_name": {"value": "Daisuke", "fact_ids": ["profile.first_name"]},
            "last_name": {"value": "Narita", "fact_ids": ["profile.last_name"]},
            "email": {"value": "candidate@example.test", "fact_ids": ["profile.email"]},
        }
        for provider, url in urls.items():
            with self.subTest(provider=provider):
                snapshot = {
                    "version": 1,
                    "url": url,
                    "navigation_committed": True,
                    "frames": [
                        {
                            "url": url,
                            "controls": [
                                {"tag": "input", "type": "text", "label": "First Name", "required": True},
                                {"tag": "input", "type": "text", "label": "Last Name", "required": True},
                                {"tag": "input", "type": "email", "label": "Email", "required": True},
                                {"tag": "input", "type": "file", "label": "Resume/CV", "required": True},
                                {"tag": "input", "type": "text", "label": "Unverified Required Question", "required": True},
                                {"tag": "button", "type": "submit", "text": "Submit Application"},
                            ],
                        }
                    ],
                }
                result = ats.build_non_submit_fill_plan(
                    snapshot,
                    answers=answers,
                    resume_path="/private/resume.pdf",
                    resume_sha256="a" * 64,
                )
                self.assertEqual(result["provider"], provider)
                self.assertFalse(any(action["kind"] == "submit" for action in result["actions"]))
                self.assertEqual(
                    [action["field_key"] for action in result["actions"]],
                    ["first_name", "last_name", "email", "resume"],
                )
                self.assertEqual(result["actions"][0]["question"], "First Name")
                self.assertEqual(result["actions"][0]["fact_ids"], ["profile.first_name"])
                self.assertEqual(result["actions"][-1]["resume_sha256"], "a" * 64)
                self.assertEqual(result["blockers"], ["Unverified Required Question"])

    def test_provider_detection_uses_hostname_boundaries(self):
        cases = {
            "https://jobs.ashbyhq.com/acme/role/application": "ashby",
            "https://app.ashbyhq.com/applicationForm": "ashby",
            "https://acme.wd5.myworkdayjobs.com/jobs/role": "workday",
            "https://wd1.myworkdaysite.com/acme/job/role": "workday",
            "https://boards.greenhouse.io/acme/jobs/123": "greenhouse",
            "https://job-boards.greenhouse.io/acme/jobs/123": "greenhouse",
            "https://jobs.lever.co/acme/role-123": "lever",
            "https://jobs.eu.lever.co/acme/role-123": "lever",
            "https://apply.workable.com/acme/j/ROLE123/": "workable",
            "https://ashbyhq.com.example.test/role": "generic",
            "https://jobs.lever.co.example.test/acme/role": "generic",
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
                "claim_ready": True,
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
                "claim_ready": False,
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
                "claim_ready": False,
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
        self.assertFalse(result["claim_ready"])

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

    def test_workday_apply_choice_is_ready_but_not_claim_ready(self):
        self.assertEqual(
            evaluate_snapshot(load_fixture("workday-apply-choice-surface.json")),
            {
                "provider": "workday",
                "ready": True,
                "claim_ready": False,
                "surface": "workday_apply_choice",
                "frame_index": 0,
                "wait_until": "commit",
                "blockers": [],
            },
        )

    def test_workday_create_account_is_ready_but_not_claim_ready(self):
        self.assertEqual(
            evaluate_snapshot(load_fixture("workday-create-account-surface.json")),
            {
                "provider": "workday",
                "ready": True,
                "claim_ready": False,
                "surface": "workday_account_create",
                "frame_index": 0,
                "wait_until": "commit",
                "blockers": [],
            },
        )

    def test_workday_create_account_requires_two_password_controls(self):
        snapshot = load_fixture("workday-create-account-surface.json")
        controls = snapshot["frames"][0]["controls"]
        password_indexes = [
            index
            for index, control in enumerate(controls)
            if control.get("type") == "password"
        ]
        controls.pop(password_indexes[-1])
        result = evaluate_snapshot(snapshot)
        self.assertFalse(result["ready"])
        self.assertFalse(result["claim_ready"])
        self.assertEqual(result["surface"], "none")

    def test_generic_application_surface_is_claim_ready(self):
        snapshot = {
            "version": 1,
            "url": "https://careers.example.com/role",
            "navigation_committed": True,
            "frames": [
                {
                    "url": "https://careers.example.com/role",
                    "controls": [
                        {"tag": "input", "type": "email"},
                        {"tag": "input", "type": "file"},
                        {
                            "tag": "button",
                            "type": "submit",
                            "text": "Submit Application",
                        },
                    ],
                }
            ],
        }
        result = evaluate_snapshot(snapshot)
        self.assertTrue(result["ready"])
        self.assertTrue(result["claim_ready"])
        self.assertEqual(result["surface"], "generic_application")


if __name__ == "__main__":
    unittest.main()
