import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from job_search_loop.guardian import gmail_health


class GuardianGmailTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.gog = root / "gog"
        self.gog.write_text("#!/bin/sh\nexit 0\n")
        self.gog.chmod(0o555)
        self.checkpoint = root / "inbox-seen.json"
        self.checkpoint.write_text(
            json.dumps({"version": 2, "message_ids": ["message-1"]})
        )
        self.checkpoint.chmod(0o600)
        self.calls = []

    def tearDown(self):
        self.tempdir.cleanup()

    def runner(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        stdout = json.dumps({"checks": []})
        if argv[1:3] == ["gmail", "search"]:
            stdout = json.dumps({"threads": [{"id": "private-thread"}]})
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    def health(self, runner=None):
        return gmail_health(
            account="candidate@example.com",
            checkpoint_path=self.checkpoint,
            executable=self.gog,
            runner=runner or self.runner,
        )

    def test_auth_real_read_and_private_checkpoint_are_healthy(self):
        report = self.health()
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(report["checkpoint_message_count"], 1)
        self.assertEqual(report["probe_thread_count"], 1)
        self.assertNotIn("candidate@example.com", str(report))
        self.assertNotIn("private-thread", str(report))
        self.assertIn("--check", self.calls[0][0])
        self.assertIn("--gmail-no-send", self.calls[1][0])
        self.assertIn("--no-input", self.calls[1][0])
        self.assertEqual(self.calls[1][0][self.calls[1][0].index("--max") + 1], "1")

    def test_failed_auth_does_not_attempt_gmail_read(self):
        def failed(argv, **kwargs):
            self.calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 1, "", "private error")

        report = self.health(failed)
        self.assertEqual(report["status"], "unhealthy")
        self.assertEqual(report["reasons"], ["gmail_auth_check_failed"])
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("private error", str(report))

    def test_invalid_api_json_is_unhealthy_without_leaking_output(self):
        def invalid(argv, **kwargs):
            if argv[1:3] == ["gmail", "search"]:
                return subprocess.CompletedProcess(argv, 0, "private garbage", "")
            return subprocess.CompletedProcess(argv, 0, "{}", "")

        report = self.health(invalid)
        self.assertEqual(report["status"], "unhealthy")
        self.assertIn("gmail_read_invalid", report["reasons"])
        self.assertNotIn("private garbage", str(report))

    def test_checkpoint_permissions_and_duplicate_ids_are_unhealthy(self):
        self.checkpoint.write_text(
            json.dumps({"version": 2, "message_ids": ["same", "same"]})
        )
        self.checkpoint.chmod(0o644)
        report = self.health()
        self.assertEqual(report["status"], "unhealthy")
        self.assertIn("gmail_checkpoint_permissions_invalid", report["reasons"])
        self.assertIn("gmail_checkpoint_invalid", report["reasons"])


if __name__ == "__main__":
    unittest.main()
