import hashlib
import importlib
import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop import telegram
from job_search_loop.ledger import Ledger


class ApplicationReportingTests(unittest.TestCase):
    def test_wake_report_prefers_semantic_failure_over_runner_success(self):
        reporting = importlib.import_module("job_search_loop.application_reporting")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger_path = root / "ledger.sqlite3"
            ledger = Ledger(ledger_path)
            application_id = ledger.add_application(
                "NVIDIA",
                "AI Role",
                "https://nvidia.wd5.myworkdayjobs.com/job/JR-semantic",
            )
            ledger.close()
            discovery = root / "workday-discovery.json"
            discovery.write_text(
                json.dumps(
                    {
                        "status": "queue_present",
                        "queued_application_ids": [application_id],
                    }
                ),
                encoding="utf-8",
            )
            result = root / "result.json"
            result.write_text(
                json.dumps(
                    {
                        "status": "transport_failed",
                        "submitted": [],
                        "submit_unknown": [],
                        "blocked": ["NVIDIA — AI Role"],
                        "report_message_id": None,
                    }
                ),
                encoding="utf-8",
            )
            summary = root / "summary.json"
            summary.write_text(
                json.dumps({"status": "success", "result_path": str(result)}),
                encoding="utf-8",
            )
            (root / "semantic-validation.json").write_text(
                json.dumps(
                    {"status": "failed", "reason": "transport_failed_without_command_failure"}
                ),
                encoding="utf-8",
            )
            calls = []

            def sender(**kwargs):
                calls.append(kwargs)
                return {"status": "sent", "message_id": "902", "event_key": "key"}

            receipt = reporting.deliver_wake_report(
                ledger_path=ledger_path,
                outbox_path=root / "outbox.sqlite3",
                run_id="daily-semantic",
                japan_day="2026-08-24",
                runner_summary_path=summary,
                discovery_path=discovery,
                output_path=root / "wake-report.json",
                sender=sender,
            )

            self.assertEqual(receipt["outcome"], "failed")
            self.assertEqual(
                receipt["reason"],
                "transport_failed_without_command_failure",
            )
            self.assertIn("outcome=failed", calls[0]["message"])
    def test_quota_failed_wake_reports_queued_company_role_and_next_action(self):
        reporting = importlib.import_module("job_search_loop.application_reporting")
        deliver = getattr(reporting, "deliver_wake_report", None)
        self.assertIsNotNone(deliver)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger_path = root / "ledger.sqlite3"
            ledger = Ledger(ledger_path)
            application_id = ledger.add_application(
                "NVIDIA",
                "Senior AI Partner Manager",
                "https://nvidia.wd5.myworkdayjobs.com/job/JR-test",
            )
            ledger.transition(application_id, "qualified")
            ledger.transition(application_id, "materials_ready")
            ledger.close()
            discovery = root / "workday-discovery.json"
            discovery.write_text(
                json.dumps(
                    {
                        "status": "queue_present",
                        "queued_application_ids": [application_id],
                    }
                ),
                encoding="utf-8",
            )
            attempts = root / "attempts.jsonl"
            attempts.write_text(
                json.dumps(
                    {"error_class": "transient_quota", "adapter_error": None}
                )
                + "\n",
                encoding="utf-8",
            )
            summary = root / "summary.json"
            summary.write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "attempts_path": str(attempts),
                    }
                ),
                encoding="utf-8",
            )
            calls = []

            def sender(**kwargs):
                calls.append(kwargs)
                return {
                    "status": "sent",
                    "message_id": "wake-901",
                    "event_key": "job-search-daily:test",
                }

            output = root / "wake-report.json"
            receipt = deliver(
                ledger_path=ledger_path,
                outbox_path=root / "telegram.sqlite3",
                run_id="daily-test",
                japan_day="2026-08-24",
                runner_summary_path=summary,
                discovery_path=discovery,
                output_path=output,
                sender=sender,
            )

            message = calls[0]["message"]
            self.assertIn("Codex:::", message)
            self.assertIn("NVIDIA — Senior AI Partner Manager", message)
            self.assertIn("outcome=failed", message)
            self.assertIn("reason=transient_quota", message)
            self.assertIn(
                "next_action=retry_with_available_provider_capacity",
                message,
            )
            self.assertEqual(receipt["message_id"], "wake-901")
            self.assertEqual(receipt, json.loads(output.read_text(encoding="utf-8")))
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_reconciled_receipt_sends_authoritative_submitted_correction_once(self):
        reporting = importlib.import_module("job_search_loop.application_reporting")
        deliver = reporting.deliver_reconciled_outcomes
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = Ledger(root / "ledger.sqlite3")
            application_id = ledger.add_application(
                "Dream AI", "Agent Engineer", "https://dream.wd1.myworkdayjobs.com/job/1"
            )
            ledger.transition(application_id, "qualified")
            ledger.transition(application_id, "materials_ready")
            resume = root / "resume.pdf"
            resume.write_bytes(b"%PDF-1.4\nresume\n")
            snapshot = root / "ats.json"
            snapshot.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "url": "https://dream.wd1.myworkdayjobs.com/job/1",
                        "navigation_committed": True,
                        "frames": [
                            {
                                "url": "https://dream.wd1.myworkdayjobs.com/job/1",
                                "controls": [
                                    {"tag": "input", "type": "email"},
                                    {"tag": "input", "type": "file"},
                                    {"tag": "button", "type": "submit", "text": "Submit"},
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            intent = ledger.claim_submission(
                application_id,
                "2026-08-23",
                "payload",
                resume_path=resume,
                resume_sha256=hashlib.sha256(resume.read_bytes()).hexdigest(),
                ats_snapshot_path=snapshot,
                ats_snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            )
            ledger.complete_submission_verified(
                intent.intent_id,
                intent.fence,
                outcome="submit_unknown",
                evidence_sha256="f" * 64,
                evidence_class="no_authoritative_completion_ui",
            )
            ledger.reconcile_submission_confirmation(
                intent_id=intent.intent_id,
                message_id="gmail-1",
                thread_id="thread-1",
                evidence_sha256="e" * 64,
                received_at="2099-01-01T00:00:00+00:00",
            )
            ledger.close()
            calls = []

            def fake_sender(**kwargs):
                calls.append(kwargs)
                return {"status": "sent", "message_id": "903"}

            result = deliver(
                ledger_path=root / "ledger.sqlite3",
                outbox_path=root / "telegram.sqlite3",
                sender=fake_sender,
            )

            self.assertEqual(result[0]["message_id"], "903")
            self.assertEqual(
                calls[0]["event_key"],
                f"application-submitted:{application_id}:gmail-1",
            )
            self.assertIn("会社: Dream AI", calls[0]["message"])
            self.assertIn("求人: Agent Engineer", calls[0]["message"])
            self.assertIn("確認: authoritative_receipt_email", calls[0]["message"])

    def test_document_delivery_is_private_and_at_most_once(self):
        sender = getattr(telegram, "send_document_once", None)
        self.assertIsNotNone(sender)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "resume.pdf"
            source.write_bytes(b"%PDF-1.4\nresume\n")
            media_root = root / "allowed-media"
            database = root / "outbox.sqlite3"
            requests = []

            def requester(**kwargs):
                requests.append(kwargs)
                return {"ok": True, "result": {"message_id": 901}}

            first = sender(
                database=database,
                event_key="application-resume:abc",
                message="Resume used for Example — AI Engineer",
                document=source,
                media_root=media_root,
                requester=requester,
            )
            second = sender(
                database=database,
                event_key="application-resume:abc",
                message="Resume used for Example — AI Engineer",
                document=source,
                media_root=media_root,
                requester=requester,
            )

            self.assertEqual(first, {"status": "sent", "message_id": "901"})
            self.assertEqual(second, first)
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0]["method"], "sendDocument")
            self.assertEqual(requests[0]["document"], source.resolve())

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
            intent = ledger.claim_submission(
                application_id,
                "2026-07-29",
                "payload",
                resume_path=resume,
                resume_sha256=resume_sha256,
                ats_snapshot_path=ats_snapshot,
                ats_snapshot_sha256=ats_snapshot_sha256,
            )
            ledger.complete_submission_verified(
                intent.intent_id,
                intent.fence,
                outcome="submitted",
                evidence_sha256="e" * 64,
                evidence_class="exact_completion_ui",
            )
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
