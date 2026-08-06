import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from job_search_loop.gog_application_transport import GogApplicationTransport


class GogApplicationTransportTests(unittest.TestCase):
    def test_uses_body_file_attachment_and_authoritative_message_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            message = root / "message.txt"
            message.write_text("private message", encoding="utf-8")
            resume = root / "resume.pdf"
            resume.write_bytes(b"resume")
            calls = []

            def runner(argv, **kwargs):
                calls.append((argv, kwargs))
                return subprocess.CompletedProcess(
                    argv, 0, stdout=json.dumps({"messageId": "msg-42"}), stderr=""
                )

            receipt = GogApplicationTransport(
                account="candidate@example.test",
                subject="Application — AI Engineer",
                runner=runner,
            )(
                recipient="jobs@example.test",
                route_kind="recruiting_email",
                message_path=str(message),
                resume_path=str(resume),
                idempotency_key="route-1:7",
            )

            argv = calls[0][0]
            self.assertEqual(argv[:3], ["/opt/homebrew/bin/gog", "gmail", "send"])
            self.assertIn("--body-file", argv)
            self.assertEqual(argv[argv.index("--body-file") + 1], str(message))
            self.assertIn("--attach", argv)
            self.assertEqual(argv[argv.index("--attach") + 1], str(resume))
            self.assertNotIn("--body", argv)
            self.assertNotIn("--dry-run", argv)
            self.assertEqual(receipt["status"], "delivered")
            self.assertEqual(receipt["provider_id"], "gmail:msg-42")
            self.assertEqual(len(receipt["evidence_sha256"]), 64)

    def test_missing_ack_or_nonzero_exit_fails_for_unknown_delivery_fencing(self):
        def missing_ack(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

        transport = GogApplicationTransport(
            account="candidate@example.test",
            subject="Application",
            runner=missing_ack,
        )
        with self.assertRaises(RuntimeError):
            transport(
                recipient="jobs@example.test",
                route_kind="recruiting_email",
                message_path="/private/message.txt",
                resume_path="/private/resume.pdf",
                idempotency_key="route-1:8",
            )


if __name__ == "__main__":
    unittest.main()
