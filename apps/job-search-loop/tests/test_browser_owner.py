import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
