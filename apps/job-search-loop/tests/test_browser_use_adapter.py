import hashlib
import tempfile
import unittest
from pathlib import Path

from job_search_loop.browser_use_adapter import (
    AuthorizedBrowserUseAdapter,
    BrowserUsePolicyError,
    PinnedBrowserUseBackend,
)


class FakeBrowserUseSession:
    def __init__(self):
        self.calls = []

    def navigate(self, url):
        self.calls.append(("navigate", url))

    def snapshot(self):
        self.calls.append(("snapshot",))
        return {"url": "https://jobs.example.test/apply", "frames": []}

    def fill(self, frame_index, control_index, value):
        self.calls.append(("fill", frame_index, control_index, value))

    def read_value(self, frame_index, control_index):
        self.calls.append(("read_value", frame_index, control_index))
        return "Daisuke"

    def upload(self, frame_index, control_index, path):
        self.calls.append(("upload", frame_index, control_index, path))

    def upload_matches(self, frame_index, control_index, path):
        self.calls.append(("upload_matches", frame_index, control_index, path))
        return True

    def screenshot(self):
        self.calls.append(("screenshot",))
        return b"real-png-bytes"


class BrowserUseAdapterTests(unittest.TestCase):
    def test_backend_requires_exact_pin_and_disables_captcha_solver(self):
        captured = []

        def session_factory(**settings):
            captured.append(settings)
            return object()

        backend = PinnedBrowserUseBackend(
            "http://127.0.0.1:9222",
            allowed_domains=["jobs.ashbyhq.com"],
            version_getter=lambda _: "0.13.7",
            session_factory=session_factory,
        )

        self.assertIsNotNone(backend.session)
        self.assertEqual(captured[0]["cdp_url"], "http://127.0.0.1:9222")
        self.assertEqual(captured[0]["allowed_domains"], ["jobs.ashbyhq.com"])
        self.assertFalse(captured[0]["captcha_solver"])
        self.assertTrue(captured[0]["keep_alive"])
        self.assertTrue(captured[0]["is_local"])

        with self.assertRaisesRegex(BrowserUsePolicyError, "pinned version"):
            PinnedBrowserUseBackend(
                "http://127.0.0.1:9222",
                allowed_domains=["jobs.ashbyhq.com"],
                version_getter=lambda _: "0.13.8",
                session_factory=session_factory,
            )
        with self.assertRaisesRegex(BrowserUsePolicyError, "loopback"):
            PinnedBrowserUseBackend(
                "https://remote-browser.example/ws",
                allowed_domains=["jobs.ashbyhq.com"],
                version_getter=lambda _: "0.13.7",
                session_factory=session_factory,
            )

    def test_adapter_exposes_only_non_submit_actions(self):
        backend = FakeBrowserUseSession()
        adapter = AuthorizedBrowserUseAdapter(
            backend,
            owner_receipt={"lease_id": "lease-1", "fence": 7, "holder_pid": 42},
        )

        adapter.navigate("https://jobs.example.test/apply")
        adapter.fill(0, 1, "Daisuke")
        self.assertEqual(adapter.read_value(0, 1), "Daisuke")

        for action in ("click", "submit", "solve_captcha", "mark_success"):
            with self.subTest(action=action):
                with self.assertRaisesRegex(BrowserUsePolicyError, "not authorized"):
                    adapter.perform(action)

        self.assertNotIn("click", adapter.authorized_actions)
        self.assertNotIn("submit", adapter.authorized_actions)

    def test_adapter_captures_only_fenced_before_after_terminal_evidence(self):
        backend = FakeBrowserUseSession()
        adapter = AuthorizedBrowserUseAdapter(
            backend,
            owner_receipt={"lease_id": "lease-1", "fence": 7, "holder_pid": 42},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipts = [adapter.capture_evidence(stage, root) for stage in ("before", "after", "terminal")]

            self.assertEqual([item["stage"] for item in receipts], ["before", "after", "terminal"])
            for receipt in receipts:
                path = Path(receipt["path"])
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(receipt["lease_id"], "lease-1")
                self.assertEqual(receipt["fence"], 7)
                self.assertEqual(receipt["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            with self.assertRaisesRegex(BrowserUsePolicyError, "evidence stage"):
                adapter.capture_evidence("success", root)


if __name__ == "__main__":
    unittest.main()
