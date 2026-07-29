import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from job_search_loop.ledger import Ledger
from job_search_loop.state import InvalidTransition
from job_search_loop.submission_confirmation import reconcile_confirmation_threads


class SubmissionConfirmationTests(unittest.TestCase):
    def _unknown_submission(
        self,
        root: Path,
        *,
        company: str = "Dream AI",
        title: str = "Agent Product Engineer",
        url: str = (
            "https://jobs.ashbyhq.com/dream/"
            "agent-product-engineer/application"
        ),
    ) -> tuple[Ledger, str, str]:
        ledger = Ledger(root / "ledger.sqlite3")
        application_id = ledger.add_application(
            company,
            title,
            url,
        )
        ledger.transition(application_id, "qualified")
        ledger.transition(application_id, "materials_ready")

        resume = root / "resume.pdf"
        resume.write_bytes(b"%PDF-1.4\nresume\n")
        resume_sha256 = hashlib.sha256(resume.read_bytes()).hexdigest()
        snapshot = root / "ats-snapshot.json"
        snapshot.write_text(
            json.dumps(
                {
                    "version": 1,
                    "url": url,
                    "navigation_committed": True,
                    "frames": [
                        {
                            "url": url,
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
        snapshot_sha256 = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        intent = ledger.claim_submission(
            application_id,
            "2026-07-29",
            "payload",
            resume_path=resume,
            resume_sha256=resume_sha256,
            ats_snapshot_path=snapshot,
            ats_snapshot_sha256=snapshot_sha256,
        )
        ledger.complete_submission(
            intent.intent_id, intent.fence, "submit_unknown"
        )
        return ledger, application_id, intent.intent_id

    def test_late_confirmation_promotes_every_row_once_without_resubmit(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger, application_id, intent_id = self._unknown_submission(
                Path(directory)
            )
            received_at = (
                datetime.now(timezone.utc) + timedelta(minutes=1)
            ).isoformat()

            first = ledger.reconcile_submission_confirmation(
                intent_id=intent_id,
                message_id="gmail-message-1",
                thread_id="gmail-thread-1",
                evidence_sha256="a" * 64,
                received_at=received_at,
            )
            second = ledger.reconcile_submission_confirmation(
                intent_id=intent_id,
                message_id="gmail-message-1",
                thread_id="gmail-thread-1",
                evidence_sha256="a" * 64,
                received_at=received_at,
            )

            self.assertEqual(first, "reconciled")
            self.assertEqual(second, "duplicate")
            self.assertEqual(
                ledger.connection.execute(
                    "SELECT current_state FROM applications WHERE id = ?",
                    (application_id,),
                ).fetchone()[0],
                "submitted",
            )
            self.assertEqual(
                ledger.connection.execute(
                    "SELECT status FROM submit_intents WHERE intent_id = ?",
                    (intent_id,),
                ).fetchone()[0],
                "submitted",
            )
            self.assertEqual(
                ledger.connection.execute(
                    "SELECT status FROM submission_attempts WHERE intent_id = ?",
                    (intent_id,),
                ).fetchone()[0],
                "submitted",
            )
            self.assertEqual(
                ledger.connection.execute(
                    "SELECT status FROM daily_slots WHERE application_id = ?",
                    (application_id,),
                ).fetchone()[0],
                "submitted",
            )
            self.assertEqual(
                ledger.connection.execute(
                    "SELECT COUNT(*) FROM submission_confirmations"
                ).fetchone()[0],
                1,
            )
            transitions = ledger.connection.execute(
                """
                SELECT from_state, to_state
                FROM events
                WHERE application_id = ?
                ORDER BY created_at, rowid
                """,
                (application_id,),
            ).fetchall()
            self.assertEqual(
                [tuple(row) for row in transitions][-1],
                ("submit_unknown", "submitted"),
            )
            ledger.close()

    def test_generic_transition_cannot_bypass_confirmation_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger, application_id, _ = self._unknown_submission(
                Path(directory)
            )

            with self.assertRaises(InvalidTransition):
                ledger.transition(application_id, "submitted")

            self.assertEqual(
                ledger.connection.execute(
                    "SELECT current_state FROM applications WHERE id = ?",
                    (application_id,),
                ).fetchone()[0],
                "submit_unknown",
            )
            self.assertEqual(
                ledger.connection.execute(
                    "SELECT COUNT(*) FROM submission_confirmations"
                ).fetchone()[0],
                0,
            )
            ledger.close()

    def test_exact_late_ashby_receipt_reconciles_and_marks_thread_seen(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger, application_id, _ = self._unknown_submission(root)
            ledger.close()
            received = datetime.now(timezone.utc) + timedelta(minutes=1)
            wrapped_subject = (
                '<<<EXTERNAL_UNTRUSTED_CONTENT id="subject-1">>>\n'
                "Source: google_api\n---\n"
                "Application received: Agent Product Engineer at Dream AI\n"
                '<<<END_EXTERNAL_UNTRUSTED_CONTENT id="subject-1">>>'
            )
            wrapped_body = (
                '<<<EXTERNAL_UNTRUSTED_CONTENT id="body-1">>>\n'
                "Source: google_api\n---\n"
                "Thank you for applying to Agent Product Engineer at Dream AI.\n"
                '<<<END_EXTERNAL_UNTRUSTED_CONTENT id="body-1">>>'
            )
            payload = {
                "thread": {
                    "id": "gmail-thread-2",
                    "messages": [
                        {
                            "id": "gmail-message-2",
                            "threadId": "gmail-thread-2",
                            "internalDate": int(received.timestamp() * 1000),
                            "headers": {
                                "from": "Dream AI Recruiting <notifications@ashbyhq.com>",
                                "subject": wrapped_subject,
                            },
                            "body": wrapped_body,
                        }
                    ],
                }
            }

            result = reconcile_confirmation_threads(
                ledger_path=root / "ledger.sqlite3",
                threads=[
                    {
                        "id": "gmail-thread-2",
                        "subject": "Application received",
                        "from": "notifications@ashbyhq.com",
                    }
                ],
                thread_loader=lambda thread_id: payload,
                seen_state=root / "inbox-seen.json",
            )

            self.assertEqual(
                result,
                {
                    "version": 1,
                    "checked_threads": 1,
                    "reconciled": [
                        {
                            "application_id": application_id,
                            "message_id": "gmail-message-2",
                            "thread_id": "gmail-thread-2",
                            "status": "reconciled",
                        }
                    ],
                    "blocked": [],
                },
            )
            reopened = Ledger(root / "ledger.sqlite3")
            self.assertEqual(
                reopened.connection.execute(
                    "SELECT current_state FROM applications WHERE id = ?",
                    (application_id,),
                ).fetchone()[0],
                "submitted",
            )
            reopened.close()
            self.assertEqual(
                json.loads(
                    (root / "inbox-seen.json").read_text(encoding="utf-8")
                ),
                {"version": 2, "message_ids": ["gmail-message-2"]},
            )

    def test_spoofed_sender_cannot_promote_or_acknowledge_thread(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger, application_id, _ = self._unknown_submission(root)
            ledger.close()
            received = datetime.now(timezone.utc) + timedelta(minutes=1)
            payload = {
                "thread": {
                    "id": "gmail-thread-spoof",
                    "messages": [
                        {
                            "id": "gmail-message-spoof",
                            "threadId": "gmail-thread-spoof",
                            "internalDate": int(received.timestamp() * 1000),
                            "headers": {
                                "from": (
                                    "Dream AI Recruiting "
                                    "<notifications@ashbyhq.com.evil.example>"
                                ),
                                "subject": (
                                    "Application received: "
                                    "Agent Product Engineer at Dream AI"
                                ),
                            },
                            "body": (
                                "Thank you for applying to "
                                "Agent Product Engineer at Dream AI."
                            ),
                        }
                    ],
                }
            }

            result = reconcile_confirmation_threads(
                ledger_path=root / "ledger.sqlite3",
                threads=[
                    {
                        "id": "gmail-thread-spoof",
                        "subject": "Application received",
                    }
                ],
                thread_loader=lambda thread_id: payload,
                seen_state=root / "inbox-seen.json",
            )

            self.assertEqual(result["reconciled"], [])
            self.assertEqual(
                result["blocked"][0]["status"],
                "no_exact_uncertain_application",
            )
            reopened = Ledger(root / "ledger.sqlite3")
            self.assertEqual(
                reopened.connection.execute(
                    "SELECT current_state FROM applications WHERE id = ?",
                    (application_id,),
                ).fetchone()[0],
                "submit_unknown",
            )
            reopened.close()
            self.assertFalse((root / "inbox-seen.json").exists())

    def test_ambiguous_company_and_role_match_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, _, _ = self._unknown_submission(root)
            first.close()
            second, _, _ = self._unknown_submission(
                root,
                url=(
                    "https://jobs.ashbyhq.com/dream/"
                    "agent-product-engineer-2/application"
                ),
            )
            second.close()
            received = datetime.now(timezone.utc) + timedelta(minutes=1)
            payload = {
                "thread": {
                    "id": "gmail-thread-ambiguous",
                    "messages": [
                        {
                            "id": "gmail-message-ambiguous",
                            "threadId": "gmail-thread-ambiguous",
                            "internalDate": int(received.timestamp() * 1000),
                            "headers": {
                                "from": (
                                    "Dream AI Recruiting "
                                    "<notifications@ashbyhq.com>"
                                ),
                                "subject": (
                                    "Application received: "
                                    "Agent Product Engineer at Dream AI"
                                ),
                            },
                            "body": (
                                "Thank you for applying to "
                                "Agent Product Engineer at Dream AI."
                            ),
                        }
                    ],
                }
            }

            result = reconcile_confirmation_threads(
                ledger_path=root / "ledger.sqlite3",
                threads=[
                    {
                        "id": "gmail-thread-ambiguous",
                        "subject": "Application received",
                    }
                ],
                thread_loader=lambda thread_id: payload,
                seen_state=root / "inbox-seen.json",
            )

            self.assertEqual(result["reconciled"], [])
            self.assertEqual(
                result["blocked"][0]["status"],
                "ambiguous_application_match",
            )
            self.assertFalse((root / "inbox-seen.json").exists())

    def test_inbox_driver_reconciles_and_delivers_before_model_scan(self):
        script = (
            Path(__file__).parents[1] / "scripts" / "run-inbox.sh"
        ).read_text(encoding="utf-8")

        reconcile_at = script.index(
            "-m job_search_loop.submission_confirmation reconcile"
        )
        delivery_at = script.index(
            "-m job_search_loop.application_reporting deliver"
        )
        scan_at = script.index("-m job_search_loop.inbox scan")
        summary_at = script.index("-m job_search_loop.summary")

        self.assertLess(reconcile_at, delivery_at)
        self.assertLess(delivery_at, scan_at)
        self.assertLess(summary_at, scan_at)


if __name__ == "__main__":
    unittest.main()
