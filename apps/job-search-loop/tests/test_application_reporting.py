import hashlib
import importlib
import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop import telegram
from job_search_loop.ledger import Ledger


class ApplicationReportingTests(unittest.TestCase):
    def test_document_delivery_is_private_and_at_most_once(self):
        sender = getattr(telegram, "send_document_once", None)
        self.assertIsNotNone(sender)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "resume.pdf"
            source.write_bytes(b"%PDF-1.4\nresume\n")
            media_root = root / "allowed-media"
            executable = root / "fake-openclaw"
            executable.write_text(
                """#!/usr/bin/env python3
import json
import pathlib
import sys

counter = pathlib.Path(__file__).with_suffix(".count")
count = int(counter.read_text() or "0") if counter.exists() else 0
counter.write_text(str(count + 1))
media = pathlib.Path(sys.argv[sys.argv.index("--media") + 1])
assert media.is_file()
assert "--force-document" in sys.argv
print(json.dumps({"messageId": "901"}))
""",
                encoding="utf-8",
            )
            executable.chmod(0o700)
            database = root / "outbox.sqlite3"

            first = sender(
                database=database,
                event_key="application-resume:abc",
                message="Resume used for Example — AI Engineer",
                document=source,
                media_root=media_root,
                executable=str(executable),
            )
            second = sender(
                database=database,
                event_key="application-resume:abc",
                message="Resume used for Example — AI Engineer",
                document=source,
                media_root=media_root,
                executable=str(executable),
            )

            self.assertEqual(first, {"status": "sent", "message_id": "901"})
            self.assertEqual(second, first)
            self.assertEqual(executable.with_suffix(".count").read_text(), "1")
            staged = list(media_root.iterdir())
            self.assertEqual(len(staged), 1)
            self.assertEqual(staged[0].read_bytes(), source.read_bytes())
            self.assertEqual(staged[0].stat().st_mode & 0o777, 0o600)

    def test_submitted_resume_report_uses_ledger_company_role_and_url(self):
        try:
            reporting = importlib.import_module("job_search_loop.application_reporting")
        except ModuleNotFoundError:
            self.fail("job_search_loop.application_reporting is missing")
        deliver = getattr(reporting, "deliver_submitted_resumes", None)
        self.assertIsNotNone(deliver)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resume = root / "resume.pdf"
            resume.write_bytes(b"%PDF-1.4\nresume\n")
            resume_sha256 = hashlib.sha256(resume.read_bytes()).hexdigest()
            ledger_path = root / "ledger.sqlite3"
            ledger = Ledger(ledger_path)
            application_id = ledger.add_application(
                "Dream AI", "Agent Product Engineer", "https://jobs.example/dream"
            )
            ledger.transition(application_id, "qualified")
            ledger.transition(application_id, "materials_ready")
            intent = ledger.claim_submission(
                application_id,
                "2026-07-29",
                "payload",
                resume_path=resume,
                resume_sha256=resume_sha256,
            )
            ledger.complete_submission(intent.intent_id, intent.fence, "submitted")
            ledger.close()
            calls = []

            def fake_sender(**kwargs):
                calls.append(kwargs)
                return {"status": "sent", "message_id": "902"}

            result = deliver(
                ledger_path=ledger_path,
                outbox_path=root / "telegram.sqlite3",
                media_root=root / "media",
                sender=fake_sender,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(
                calls[0]["event_key"],
                f"application-resume:{application_id}:{resume_sha256}",
            )
            self.assertEqual(calls[0]["document"], resume.resolve())
            self.assertIn("Dream AI", calls[0]["message"])
            self.assertIn("Agent Product Engineer", calls[0]["message"])
            self.assertIn("https://jobs.example/dream", calls[0]["message"])
            self.assertEqual(result[0]["message_id"], "902")


if __name__ == "__main__":
    unittest.main()
