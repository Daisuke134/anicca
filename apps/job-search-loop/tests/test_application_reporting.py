import hashlib
import importlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from job_search_loop import telegram
from job_search_loop.ledger import Ledger


class ApplicationReportingTests(unittest.TestCase):
    def test_submission_evidence_archive_is_deterministic_and_complete(self):
        reporting = importlib.import_module("job_search_loop.application_reporting")
        self.assertTrue(hasattr(reporting, "build_submission_evidence_archive"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {}
            for name, content in {
                "resume": b"%PDF resume",
                "pre_submit": b"png pre",
                "post_action": b"png post",
                "terminal": b"png terminal",
                "confirmation": b'{"status":"submitted"}',
            }.items():
                suffix = ".pdf" if name == "resume" else ".json" if name == "confirmation" else ".png"
                path = root / f"{name}{suffix}"
                path.write_bytes(content)
                paths[name] = path
            report = {
                "application_id": "application-1",
                "company": "Example",
                "title": "AI Engineer",
                "canonical_url": "https://jobs.example/1",
                "intent_id": "intent-1",
                "fence": 7,
                "bundle_sha256": "b" * 64,
                "confirmation_source": "ats",
                "confirmation_id": "ats-1",
            }
            for name, path in paths.items():
                report[f"{name}_path"] = str(path)
                report[f"{name}_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()

            first = reporting.build_submission_evidence_archive(report, root / "media")
            first_bytes = first.read_bytes()
            second = reporting.build_submission_evidence_archive(report, root / "media")

            self.assertEqual(first, second)
            self.assertEqual(second.read_bytes(), first_bytes)
            self.assertEqual(first.stat().st_mode & 0o777, 0o600)
            with zipfile.ZipFile(first) as bundle:
                self.assertEqual(
                    sorted(bundle.namelist()),
                    [
                        "confirmation.json",
                        "manifest.json",
                        "post-action.png",
                        "pre-submit.png",
                        "resume.pdf",
                        "terminal.png",
                    ],
                )
                manifest = json.loads(bundle.read("manifest.json"))
                self.assertEqual(manifest["bundle_sha256"], "b" * 64)
                self.assertEqual(manifest["intent_id"], "intent-1")
                self.assertNotIn(str(root), bundle.read("manifest.json").decode())

    def test_complete_evidence_bundle_is_delivered_under_one_idempotency_key(self):
        reporting = importlib.import_module("job_search_loop.application_reporting")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = {
                "application_id": "application-1",
                "company": "Example",
                "title": "AI Engineer",
                "canonical_url": "https://jobs.example/1",
                "intent_id": "intent-1",
                "fence": 7,
                "bundle_sha256": "c" * 64,
                "confirmation_source": "gmail",
                "confirmation_id": "gmail-message-1",
            }
            for name, suffix in {
                "resume": ".pdf",
                "pre_submit": ".png",
                "post_action": ".png",
                "terminal": ".png",
                "confirmation": ".json",
            }.items():
                path = root / f"{name}{suffix}"
                path.write_bytes(f"evidence:{name}".encode())
                report[f"{name}_path"] = str(path)
                report[f"{name}_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            calls = []

            result = reporting.deliver_submitted_evidence_bundles(
                ledger_path=root / "ledger.sqlite3",
                outbox_path=root / "outbox.sqlite3",
                media_root=root / "media",
                report_reader=lambda path: [report],
                sender=lambda **kwargs: calls.append(kwargs)
                or {"status": "sent", "message_id": "903"},
            )

            self.assertEqual(len(calls), 1)
            self.assertEqual(
                calls[0]["event_key"],
                f"application-evidence:application-1:{'c' * 64}",
            )
            self.assertEqual(calls[0]["document"].suffix, ".zip")
            self.assertIn("gmail-message-1", calls[0]["message"])
            self.assertEqual(result[0]["message_id"], "903")

    def test_ledger_and_reporter_expose_fenced_submission_evidence_bundle(self):
        self.assertTrue(hasattr(Ledger, "record_submission_evidence_bundle"))
        reporting = importlib.import_module("job_search_loop.application_reporting")
        self.assertTrue(hasattr(reporting, "deliver_submitted_evidence_bundles"))

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
            ats_snapshot = root / "ats-snapshot.json"
            ats_snapshot.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "url": "https://jobs.example/dream",
                        "navigation_committed": True,
                        "frames": [
                            {
                                "url": "https://jobs.example/dream",
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
                ),
                encoding="utf-8",
            )
            ats_snapshot_sha256 = hashlib.sha256(
                ats_snapshot.read_bytes()
            ).hexdigest()
            fill_receipt = root / "fill-receipt.json"
            fill_receipt.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "status": "claim_ready",
                        "job_url": "https://jobs.example/dream",
                        "snapshot_sha256": ats_snapshot_sha256,
                        "resume_sha256": resume_sha256,
                        "owner_lease_id": "lease-test",
                        "owner_fence": 1,
                        "owner_holder_pid": 123,
                        "blockers": [],
                        "submit_clicked": False,
                    }
                ),
                encoding="utf-8",
            )
            fill_receipt_sha256 = hashlib.sha256(fill_receipt.read_bytes()).hexdigest()
            intent = ledger.claim_submission(
                application_id,
                "2026-07-29",
                "payload",
                resume_path=resume,
                resume_sha256=resume_sha256,
                ats_snapshot_path=ats_snapshot,
                ats_snapshot_sha256=ats_snapshot_sha256,
                fill_receipt_path=fill_receipt,
                fill_receipt_sha256=fill_receipt_sha256,
            )
            ledger.record_submission_materials(
                intent_id=intent.intent_id,
                fence=intent.fence,
                resume_path=resume,
                resume_sha256=resume_sha256,
                cover_letter=None,
                employer_answers=[],
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
