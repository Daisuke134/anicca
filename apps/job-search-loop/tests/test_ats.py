import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ats import detect_provider, evaluate_snapshot


FIXTURES = Path(__file__).parent / "fixtures" / "ats"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class AtsReadinessTests(unittest.TestCase):
    def test_required_group_labels_fill_verified_contact_and_block_unknowns_once(self):
        from job_search_loop.ats import build_non_submit_fill_plan

        url = "https://jobs.ashbyhq.com/acme/role/application"
        snapshot = {
            "version": 1,
            "url": url,
            "navigation_committed": True,
            "frames": [
                {
                    "url": url,
                    "controls": [
                        {"tag": "input", "type": "tel", "label": "Phone Number", "group_label": "Phone Number*", "required": True},
                        {"tag": "input", "type": "text", "label": "Start typing...", "group_label": "Where are you currently located?*", "required": True},
                        {"tag": "input", "type": "text", "label": "Pick date...", "group_label": "When can you start a new role?*", "required": True},
                        {"tag": "button", "type": "button", "text": "Yes", "group_label": "Are you authorized to work in Japan?*", "required": True},
                        {"tag": "button", "type": "button", "text": "No", "group_label": "Are you authorized to work in Japan?*", "required": True},
                        {"tag": "input", "type": "checkbox", "label": "I confirm", "group_label": "I certify these answers are true.*", "required": True},
                        {"tag": "button", "type": "submit", "text": "Submit Application"},
                    ],
                }
            ],
        }
        result = build_non_submit_fill_plan(
            snapshot,
            answers={
                "phone": {"value": "+81-00-0000-0000", "fact_ids": ["profile.phone"]},
                "location": {"value": "Tokyo, Japan", "fact_ids": ["profile.base"]},
            },
            resume_path="/private/resume.pdf",
            resume_sha256="a" * 64,
        )

        self.assertEqual(
            [action["field_key"] for action in result["actions"]],
            ["phone", "location"],
        )
        self.assertEqual(
            result["blockers"],
            [
                "When can you start a new role?*",
                "Are you authorized to work in Japan?*",
                "I certify these answers are true.*",
            ],
        )

    def test_ashby_single_name_field_uses_grounded_full_name(self):
        from job_search_loop.ats import build_non_submit_fill_plan

        snapshot = load_fixture("ashby-application-surface.json")
        result = build_non_submit_fill_plan(
            snapshot,
            answers={
                "full_name": {"value": "Daisuke Narita", "fact_ids": ["profile.name"]},
                "email": {"value": "candidate@example.test", "fact_ids": ["profile.email"]},
            },
            resume_path="/private/resume.pdf",
            resume_sha256="a" * 64,
        )

        self.assertEqual(
            [action["field_key"] for action in result["actions"]],
            ["resume", "full_name", "email"],
        )
        self.assertEqual(result["actions"][1]["question"], "Name")
        self.assertEqual(result["actions"][1]["fact_ids"], ["profile.name"])

    def test_executes_and_receipts_verified_fields_without_submit_capability(self):
        from job_search_loop import ats

        self.assertTrue(
            hasattr(ats, "execute_non_submit_fill_plan"),
            "bounded ATS fill executor is missing",
        )

        class FakePageAdapter:
            def __init__(self):
                self.values = {}
                self.uploads = {}

            def fill(self, frame_index, control_index, value):
                self.values[(frame_index, control_index)] = value

            def read_value(self, frame_index, control_index):
                return self.values[(frame_index, control_index)]

            def upload(self, frame_index, control_index, path):
                self.uploads[(frame_index, control_index)] = path

            def upload_matches(self, frame_index, control_index, path):
                return self.uploads[(frame_index, control_index)] == path

            def screenshot(self, path):
                Path(path).write_bytes(b"pre-submit-image")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resume = root / "resume.pdf"
            resume.write_bytes(b"verified resume")
            resume_sha256 = hashlib.sha256(resume.read_bytes()).hexdigest()
            url = "https://jobs.ashbyhq.com/acme/role/application"
            snapshot = {
                "version": 1,
                "url": url,
                "navigation_committed": True,
                "frames": [
                    {
                        "url": url,
                        "controls": [
                            {"tag": "input", "type": "text", "label": "First Name", "required": True},
                            {"tag": "input", "type": "email", "label": "Email", "required": True},
                            {"tag": "input", "type": "file", "label": "Resume/CV", "required": True},
                            {"tag": "button", "type": "submit", "text": "Submit Application"},
                        ],
                    }
                ],
            }
            plan = ats.build_non_submit_fill_plan(
                snapshot,
                answers={
                    "first_name": {"value": "Daisuke", "fact_ids": ["profile.first_name"]},
                    "email": {"value": "candidate@example.test", "fact_ids": ["profile.email"]},
                },
                resume_path=str(resume),
                resume_sha256=resume_sha256,
            )
            screenshot = root / "pre-submit.png"
            receipt_path = root / "fill-receipt.json"

            receipt = ats.execute_non_submit_fill_plan(
                plan,
                adapter=FakePageAdapter(),
                owner_receipt={"lease_id": "lease-1", "fence": 9, "holder_pid": 123},
                snapshot_sha256="b" * 64,
                screenshot_path=screenshot,
                receipt_path=receipt_path,
            )

            self.assertEqual(receipt["status"], "claim_ready")
            self.assertFalse(receipt["submit_clicked"])
            self.assertEqual(receipt["owner_fence"], 9)
            self.assertEqual(receipt["resume_sha256"], resume_sha256)
            self.assertEqual(receipt["answers"][0]["question"], "First Name")
            self.assertEqual(receipt["answers"][0]["answer"], "Daisuke")
            self.assertEqual(receipt["answers"][0]["fact_ids"], ["profile.first_name"])
            self.assertRegex(receipt["plan_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(receipt["screenshot_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(receipt_path.stat().st_mode & 0o777, 0o600)
            self.assertTrue(screenshot.is_file())

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
