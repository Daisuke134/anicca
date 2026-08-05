import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from job_search_loop.guardian import browser_owner_health


class GuardianBrowserOwnerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.receipt = Path(self.tempdir.name) / "browser-owner.json"
        self.value = {
            "version": 2,
            "status": "ready",
            "owner": "ai.anicca.job-search-daily",
            "endpoint": "http://127.0.0.1:9222",
            "lease_id": "lease-abc",
            "fence": 4,
            "holder_pid": 123,
            "acquired_at": "2026-08-05T11:55:00+00:00",
            "expires_at": "2026-08-05T12:05:00+00:00",
        }
        self.write(self.value)

    def tearDown(self):
        self.tempdir.cleanup()

    def write(self, value):
        self.receipt.write_text(json.dumps(value))
        self.receipt.chmod(0o600)

    def health(self, **overrides):
        options = {
            "receipt_path": self.receipt,
            "endpoint": "http://127.0.0.1:9222",
            "now": datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
            "cdp_probe": lambda endpoint: {"status": "ready"},
            "listener_reader": lambda port: [{"pid": 123, "address": "127.0.0.1"}],
            "pid_alive": lambda pid: pid == 123,
        }
        options.update(overrides)
        return browser_owner_health(**options)

    def test_live_fenced_owner_and_single_loopback_listener_are_healthy(self):
        report = self.health()
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(report["owner_state"], "leased")
        self.assertEqual(report["listener_count"], 1)
        self.assertNotIn("lease-abc", str(report))
        self.assertNotIn("123", str(report))

    def test_expired_lease_is_unhealthy(self):
        self.value["expires_at"] = "2026-08-05T11:59:59+00:00"
        self.write(self.value)
        report = self.health()
        self.assertIn("browser_owner_lease_expired", report["reasons"])

    def test_multiple_or_non_loopback_listeners_are_unhealthy(self):
        report = self.health(
            listener_reader=lambda port: [
                {"pid": 123, "address": "127.0.0.1"},
                {"pid": 456, "address": "0.0.0.0"},
            ]
        )
        self.assertIn("browser_listener_not_unique", report["reasons"])
        self.assertIn("browser_listener_not_loopback", report["reasons"])

    def test_legacy_claim_without_lease_proof_is_unhealthy(self):
        self.write(
            {
                "status": "ready",
                "owner": "ai.anicca.job-search-daily",
                "endpoint": "http://127.0.0.1:9222",
                "browser": "Chrome/145",
                "websocket": "ws://127.0.0.1:9222/devtools/browser/private",
            }
        )
        report = self.health()
        self.assertIn("browser_owner_receipt_invalid", report["reasons"])
        self.assertNotIn("private", str(report))


if __name__ == "__main__":
    unittest.main()
