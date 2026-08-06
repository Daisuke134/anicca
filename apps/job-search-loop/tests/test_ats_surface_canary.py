import hashlib
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ats_surface_canary import run_surface_canary


class FakePage:
    def __init__(self):
        self.url = "about:blank"
        self.closed = False

    def goto(self, url, **_kwargs):
        self.url = url

    def screenshot(self, *, path, **_kwargs):
        Path(path).write_bytes(b"png")

    def close(self):
        self.closed = True


class AtsSurfaceCanaryTests(unittest.TestCase):
    def test_three_ats_surfaces_plan_grounded_fields_without_send_or_submit(self):
        page = FakePage()
        context = type("Context", (), {"new_page": lambda _self: page})()
        browser = type("Browser", (), {"contexts": [context]})()
        chromium = type("Chromium", (), {"connect_over_cdp": lambda _self, _endpoint: browser})()
        playwright = type("Playwright", (), {"chromium": chromium})()
        request = {
            "request_id": "three-ats",
            "targets": [
                {"provider": "ashby", "url": "https://jobs.ashbyhq.com/acme/role/application"},
                {"provider": "greenhouse", "url": "https://boards.greenhouse.io/acme/jobs/1"},
                {"provider": "workday", "url": "https://acme.wd5.myworkdayjobs.com/acme/job/x/apply"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resume = root / "resume.pdf"
            resume.write_bytes(b"resume")
            receipt = run_surface_canary(
                request=request,
                owner_receipt={"status": "ready", "endpoint": "http://127.0.0.1:9222", "lease_id": "lease", "fence": 8},
                profile={"candidate": {"name": "Test Person", "application_email": "test@example.com"}},
                materials_root=root,
                evidence_dir=root / "evidence",
                playwright=playwright,
                snapshotter=lambda current, navigation_committed: {
                    "version": 1,
                    "url": current.url,
                    "navigation_committed": navigation_committed,
                    "frames": [{"url": current.url, "controls": [
                        {"tag": "input", "type": "email", "label": "Email", "required": True},
                        {"tag": "input", "type": "file", "label": "Resume", "required": True},
                        {"tag": "button", "type": "submit", "text": "Submit Application"},
                    ]}],
                },
                resume_selector=lambda **_kwargs: {
                    "resume_path": str(resume),
                    "resume_sha256": hashlib.sha256(resume.read_bytes()).hexdigest(),
                },
            )

        self.assertEqual(receipt["provider_count"], 3)
        self.assertEqual(receipt["submit_count"], 0)
        self.assertEqual(receipt["email_send_count"], 0)
        self.assertTrue(all(item["grounded_action_count"] == 2 for item in receipt["targets"]))
        self.assertTrue(page.closed)


if __name__ == "__main__":
    unittest.main()
