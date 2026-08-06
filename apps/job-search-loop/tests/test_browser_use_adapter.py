import hashlib
import json
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

    def open_application(self, frame_index, control_index):
        self.calls.append(("open_application", frame_index, control_index))

    def screenshot(self):
        self.calls.append(("screenshot",))
        return b"real-png-bytes"


class FakeElement:
    def __init__(self, *, tag="input", role="", text=""):
        self.value = ""
        self.tag = tag
        self.role = role
        self.text = text
        self.click_count = 0
        self._backend_node_id = 17
        self._session_id = "session-1"
        self._client = FakeCDPClient(self)

    async def fill(self, value):
        self.value = value

    async def evaluate(self, script):
        if "tagName" in script:
            return json.dumps({"tag": self.tag, "role": self.role, "text": self.text})
        return self.value

    async def click(self):
        self.click_count += 1


class FakeDOM:
    def __init__(self, element):
        self.element = element

    async def setFileInputFiles(self, *, params, session_id):
        assert params["backendNodeId"] == 17
        assert session_id == "session-1"
        self.element.value = f"C:\\fakepath\\{Path(params['files'][0]).name}"


class FakeSend:
    def __init__(self, element):
        self.DOM = FakeDOM(element)


class FakeCDPClient:
    def __init__(self, element):
        self.send = FakeSend(element)


class FakePage:
    def __init__(self):
        self.element = FakeElement()

    async def evaluate(self, _script):
        return json.dumps([{"tag": "input", "type": "text", "required": True}])

    async def get_elements_by_css_selector(self, _selector):
        return [self.element]


class FakeAsyncBrowserSession:
    def __init__(self, **settings):
        self.settings = settings
        self.page = FakePage()
        self.calls = []

    async def start(self):
        self.calls.append("start")

    async def navigate_to(self, url):
        self.calls.append(("navigate", url))

    async def get_current_page(self):
        return self.page

    async def take_screenshot(self):
        return b"browser-use-screenshot"

    async def stop(self):
        self.calls.append("stop")


class BrowserUseAdapterTests(unittest.TestCase):
    def test_backend_opens_only_semantic_application_entry_controls(self):
        backend = PinnedBrowserUseBackend(
            "http://127.0.0.1:9222",
            allowed_domains=["jobs.ashbyhq.com"],
            version_getter=lambda _: "0.13.7",
            session_factory=FakeAsyncBrowserSession,
        )
        backend.connect()
        application = FakeElement(tag="a", role="tab", text="Application")
        backend.session.page.element = application

        backend.open_application(0, 0)

        self.assertEqual(application.click_count, 1)
        backend.session.page.element = FakeElement(tag="button", text="Submit Application")
        with self.assertRaisesRegex(BrowserUsePolicyError, "application entry"):
            backend.open_application(0, 0)
        backend.close()

    def test_adapter_authorizes_semantic_application_open_but_never_generic_click(self):
        backend = FakeBrowserUseSession()
        adapter = AuthorizedBrowserUseAdapter(
            backend,
            owner_receipt={"lease_id": "lease-1", "fence": 7, "holder_pid": 42},
        )

        adapter.open_application(0, 3)

        self.assertEqual(backend.calls[-1], ("open_application", 0, 3))
        with self.assertRaisesRegex(BrowserUsePolicyError, "not authorized"):
            adapter.perform("click", 0, 3)

    def test_pinned_backend_runs_async_browser_session_on_one_bridge(self):
        backend = PinnedBrowserUseBackend(
            "http://127.0.0.1:9222",
            allowed_domains=["jobs.ashbyhq.com"],
            version_getter=lambda _: "0.13.7",
            session_factory=FakeAsyncBrowserSession,
        )
        backend.connect()
        backend.navigate("https://jobs.ashbyhq.com/example/application")
        snapshot = backend.snapshot()
        backend.fill(0, 0, "Daisuke")

        self.assertEqual(snapshot["frames"][0]["controls"][0]["tag"], "input")
        self.assertEqual(backend.read_value(0, 0), "Daisuke")
        self.assertEqual(backend.screenshot(), b"browser-use-screenshot")
        with self.assertRaisesRegex(BrowserUsePolicyError, "frame"):
            backend.fill(1, 0, "forbidden")
        with self.assertRaisesRegex(BrowserUsePolicyError, "allowlist"):
            backend.navigate("https://attacker.example/application")
        backend.close()
        self.assertIn("stop", backend.session.calls)

    def test_pinned_backend_uploads_only_an_existing_file_and_verifies_basename(self):
        backend = PinnedBrowserUseBackend(
            "http://127.0.0.1:9222",
            allowed_domains=["jobs.ashbyhq.com"],
            version_getter=lambda _: "0.13.7",
            session_factory=FakeAsyncBrowserSession,
        )
        backend.connect()
        with tempfile.TemporaryDirectory() as directory:
            resume = Path(directory) / "resume.pdf"
            resume.write_bytes(b"pdf")
            backend.upload(0, 0, str(resume))
            self.assertTrue(backend.upload_matches(0, 0, str(resume)))
            with self.assertRaisesRegex(BrowserUsePolicyError, "missing"):
                backend.upload(0, 0, str(Path(directory) / "missing.pdf"))
        backend.close()

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
