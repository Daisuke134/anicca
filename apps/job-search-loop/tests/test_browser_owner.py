import json
import inspect
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from job_search_loop import browser_owner
from job_search_loop.browser_owner import BrowserLease, probe_cdp


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/json/version":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(
            {
                "Browser": "Chrome/140",
                "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/abc",
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


class BrowserOwnerTests(unittest.TestCase):
    def test_default_attach_probe_is_direct_playwright_cdp(self):
        source = inspect.getsource(browser_owner)
        self.assertIn("from playwright", source)
        self.assertNotIn("PinnedBrowserUseBackend", source)
        self.assertNotIn("kickstart", source)
        self.assertNotIn("job-search-browser", source)
        self.assertIn('default="interactive:dais"', source)
        default = inspect.signature(
            browser_owner.acquire_with_attach
        ).parameters["attach_probe"].default
        self.assertEqual(default.__name__, "attach_playwright_cdp")

    def test_attach_failure_releases_once_without_restart_or_retry(self):
        events = []

        class Lease:
            receipt_path = Path("/unused")

            def acquire(self):
                events.append("acquire")
                return {"status": "leased", "endpoint": "http://127.0.0.1:9222"}

            def release(self):
                events.append("release")
                return True

        def attach(endpoint):
            events.append("attach")
            raise TimeoutError("CDP initialization timed out")

        with self.assertRaisesRegex(TimeoutError, "timed out"):
            browser_owner.acquire_with_attach(Lease(), attach_probe=attach)

        self.assertEqual(events, ["acquire", "attach", "release"])

    def test_successful_attach_uses_existing_browser_once(self):
        class Lease:
            receipt_path = Path("/unused")

            def acquire(self):
                return {"status": "leased", "endpoint": "http://127.0.0.1:9222"}

            def release(self):
                return True

        endpoints = []

        def attach(endpoint):
            endpoints.append(endpoint)
            return {"browser": "Chrome/140", "context_count": 1}

        result = browser_owner.acquire_with_attach(Lease(), attach_probe=attach)

        self.assertEqual(endpoints, ["http://127.0.0.1:9222"])
        self.assertEqual(result["attach_attempts"], 1)
        self.assertEqual(result["status"], "ready")

    def test_running_cdp_is_declared_ready_for_the_existing_loop_owner(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            endpoint = f"http://127.0.0.1:{server.server_port}"
            self.assertEqual(
                probe_cdp(endpoint),
                {
                    "status": "ready",
                    "endpoint": endpoint,
                    "browser": "Chrome/140",
                    "websocket": "ws://127.0.0.1:9222/devtools/browser/abc",
                },
            )
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_acquire_writes_fenced_receipt_bound_to_holder_and_browser(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lease = root / "interactive_dais.lease"
            receipt = root / "browser-owner.json"
            fence = root / "browser-fence"
            lease.write_text(json.dumps({"identity": "interactive:dais", "pid": os.getpid(), "host": "test-host", "port": 49152, "uuid": "browser-uuid", "acquired_at": 1785924000}))
            completed = type("Completed", (), {"returncode": 0, "stdout": "http://127.0.0.1:49152\n", "stderr": ""})()
            with patch("job_search_loop.browser_owner.subprocess.run", return_value=completed), patch("job_search_loop.browser_owner.socket.gethostname", return_value="test-host"):
                result = BrowserLease(
                    guard=Path("/guard"), identity="interactive:dais", owner="ai.anicca.job-search-daily",
                    receipt_path=receipt, lease_path=lease, fence_path=fence,
                    holder_pid=os.getpid(), browser_pid_reader=lambda port: 777,
                ).acquire()
            self.assertEqual(result["version"], 2)
            self.assertEqual(result["holder_pid"], os.getpid())
            self.assertEqual(result["browser_pid"], 777)
            self.assertEqual(result["endpoint"], "http://127.0.0.1:49152")
            self.assertEqual(result["fence"], 1)
            self.assertNotIn("uuid", result)
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
            self.assertEqual(fence.stat().st_mode & 0o777, 0o600)

    def test_receipt_is_not_ready_until_playwright_attach_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lease_path = root / "interactive_dais.lease"
            receipt_path = root / "browser-owner.json"
            fence_path = root / "browser-fence"
            lease_path.write_text(
                json.dumps(
                    {
                        "identity": "interactive:dais",
                        "pid": os.getpid(),
                        "host": "test-host",
                        "port": 49152,
                        "uuid": "browser-uuid",
                        "acquired_at": 1785924000,
                    }
                )
            )
            completed = type(
                "Completed",
                (),
                {
                    "returncode": 0,
                    "stdout": "http://127.0.0.1:49152\n",
                    "stderr": "",
                },
            )()
            observed = []

            def attach(endpoint):
                observed.append(
                    json.loads(receipt_path.read_text(encoding="utf-8"))["status"]
                )
                return {"browser": "Chrome/140", "context_count": 1}

            with patch(
                "job_search_loop.browser_owner.subprocess.run", return_value=completed
            ), patch(
                "job_search_loop.browser_owner.socket.gethostname",
                return_value="test-host",
            ):
                result = browser_owner.acquire_with_attach(
                    BrowserLease(
                        guard=Path("/guard"),
                        identity="interactive:dais",
                        owner="ai.anicca.job-search-daily",
                        receipt_path=receipt_path,
                        lease_path=lease_path,
                        fence_path=fence_path,
                        holder_pid=os.getpid(),
                        browser_pid_reader=lambda port: 777,
                    ),
                    attach_probe=attach,
                )

            self.assertEqual(observed, ["leased"])
            self.assertEqual(result["status"], "ready")
            self.assertEqual(
                json.loads(receipt_path.read_text(encoding="utf-8"))["status"],
                "ready",
            )

    def test_busy_acquire_fails_closed_without_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed = type("Completed", (), {"returncode": 9, "stdout": "", "stderr": "guard: BUSY"})()
            with patch("job_search_loop.browser_owner.subprocess.run", return_value=completed):
                owner = BrowserLease(guard=Path("/guard"), identity="interactive:dais", owner="ai.anicca.job-search-daily", receipt_path=root / "receipt", lease_path=root / "lease", fence_path=root / "fence")
                with self.assertRaisesRegex(RuntimeError, "busy"):
                    owner.acquire()
            self.assertFalse((root / "receipt").exists())

    def test_release_refuses_to_remove_a_lease_replaced_by_another_holder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lease, receipt = root / "lease", root / "receipt.json"
            lease.write_text(json.dumps({"identity": "interactive:dais", "pid": 999}))
            receipt.write_text(json.dumps({"version": 2, "status": "ready", "owner": "ai.anicca.job-search-daily", "identity": "interactive:dais", "holder_pid": 123, "lease_acquired_at": 1785924000}))
            with patch("job_search_loop.browser_owner.subprocess.run") as run:
                released = BrowserLease(guard=Path("/guard"), identity="interactive:dais", owner="ai.anicca.job-search-daily", receipt_path=receipt, lease_path=lease, fence_path=root / "fence", holder_pid=123).release()
            self.assertFalse(released)
            run.assert_not_called()
            self.assertTrue(lease.exists())

    def test_release_accepts_same_lease_after_heartbeat_refreshes_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lease_path = root / "interactive_dais.lease"
            receipt_path = root / "browser-owner.json"
            fence_path = root / "browser-fence"
            original = {
                "identity": "interactive:dais",
                "pid": 123,
                "host": "test-host",
                "port": 49152,
                "uuid": "browser-uuid",
                "acquired_at": 1785924000,
            }
            lease_path.write_text(json.dumps(original) + "\n", encoding="utf-8")
            completed = type(
                "Completed",
                (),
                {"returncode": 0, "stdout": "http://127.0.0.1:49152\n", "stderr": ""},
            )()
            owner = BrowserLease(
                guard=Path("/guard"),
                identity="interactive:dais",
                owner="ai.anicca.job-search-daily",
                receipt_path=receipt_path,
                lease_path=lease_path,
                fence_path=fence_path,
                holder_pid=123,
                browser_pid_reader=lambda port: 777,
            )
            with patch(
                "job_search_loop.browser_owner.subprocess.run", return_value=completed
            ), patch(
                "job_search_loop.browser_owner.socket.gethostname",
                return_value="test-host",
            ):
                owner.acquire()
                refreshed = {**original, "acquired_at": original["acquired_at"] + 300}
                lease_path.write_text(json.dumps(refreshed) + "\n", encoding="utf-8")
                self.assertTrue(owner.release())

            self.assertEqual(
                json.loads(receipt_path.read_text(encoding="utf-8"))["status"],
                "released",
            )


if __name__ == "__main__":
    unittest.main()
