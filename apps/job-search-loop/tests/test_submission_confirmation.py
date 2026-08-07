import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from job_search_loop.guardian import ledger_health
from job_search_loop.ledger import FenceError, Ledger
from job_search_loop.state import InvalidTransition
from job_search_loop.submission_confirmation import reconcile_confirmation_threads, _gmail_confirmation_threads
from job_search_loop.summary import build_summary_v2


class RecordingSpan:
    recording = True
    def __init__(self, name, attributes): self.name, self.attributes = name, attributes or {}
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def set_attributes(self, attributes): self.attributes.update(attributes)


class RecordingTelemetry:
    def __init__(self): self.spans = []
    def span(self, name, attributes=None):
        span = RecordingSpan(name, attributes); self.spans.append(span); return span


class SubmissionConfirmationTests(unittest.TestCase):
    def test_confirmation_search_uses_supported_read_only_gog_flags(self):
        completed = type("Completed", (), {"stdout": '{"threads": []}'})()
        with patch("job_search_loop.submission_confirmation.subprocess.run", return_value=completed) as run:
            self.assertEqual(_gmail_confirmation_threads("candidate@example.com", "/opt/gog"), [])
        argv = run.call_args.args[0]
        self.assertIn("--wrap-untrusted", argv)
        self.assertIn("--gmail-no-send", argv)
        self.assertIn("--no-input", argv)
        self.assertIn("--max", argv)
        self.assertNotIn("--limit", argv)

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
        confirmed_browser: bool = False,
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
        fill_receipt = root / f"fill-{application_id}.json"
        fill_receipt.write_text(
            json.dumps(
                {
                    "version": 1,
                    "status": "claim_ready",
                    "job_url": url,
                    "snapshot_sha256": snapshot_sha256,
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
            ats_snapshot_path=snapshot,
            ats_snapshot_sha256=snapshot_sha256,
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
        if confirmed_browser:
            ledger.mark_submission_click_phase(intent.intent_id, intent.fence, "clicked")
            ledger.mark_submission_request_started(intent.intent_id, intent.fence)
            ledger.mark_submission_click_phase(intent.intent_id, intent.fence, "confirmed")
        ledger.complete_submission(
            intent.intent_id, intent.fence, "submit_unknown"
        )
        return ledger, application_id, intent.intent_id

    def _authoritative_ashby_projection(
        self,
        root: Path,
        *,
        evidence_source: str = "ashby_graphql_plus_visible_success",
        evidence_sha256: str = (
            "e73a212752d3ca020b16bae36ca19578ba437dcf434b054daff414e467cb430b"
        ),
        event_fence: int = 1,
        event_intent_id: str | None = None,
    ) -> tuple[Ledger, str, str]:
        ledger, application_id, intent_id = self._unknown_submission(
            root,
            company="Neural Concept",
            title="Solution Engineer - Japan",
            url="https://jobs.ashbyhq.com/neuralconcept/solution-engineer/application",
            confirmed_browser=True,
        )
        with ledger._transaction():
            ledger._append_event(
                application_id,
                "submit_unknown",
                "submitted",
                {
                    "evidence_sha256": evidence_sha256,
                    "evidence_source": evidence_source,
                    "fence": event_fence,
                    "intent_id": event_intent_id or intent_id,
                },
            )
            ledger.connection.execute(
                "UPDATE submit_intents SET status = 'submitted' "
                "WHERE intent_id = ? AND fence = 1 AND status = 'submit_unknown'",
                (intent_id,),
            )
            ledger.connection.execute(
                "UPDATE submission_attempts SET status = 'submitted' "
                "WHERE intent_id = ? AND fence = 1 AND status = 'submit_unknown'",
                (intent_id,),
            )
            ledger.connection.execute(
                "UPDATE daily_slots SET status = 'submitted' "
                "WHERE application_id = ? AND status = 'submit_unknown'",
                (application_id,),
            )
            ledger.connection.execute(
                "UPDATE applications SET current_state = 'submitted' WHERE id = ?",
                (application_id,),
            )
        return ledger, application_id, intent_id

    def test_authoritative_ashby_projection_without_bundle_is_counted_in_summary_and_guardian(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger, application_id, intent_id = self._authoritative_ashby_projection(
                Path(directory)
            )
            self.assertIsNone(
                ledger.connection.execute(
                    "SELECT 1 FROM submission_evidence_bundles "
                    "WHERE intent_id = ? AND fence = 1",
                    (intent_id,),
                ).fetchone()
            )
            self.assertIsNone(
                ledger.connection.execute(
                    "SELECT 1 FROM application_artifacts WHERE application_id = ?",
                    (application_id,),
                ).fetchone()
            )
            summary = next(
                row
                for row in ledger.event_summary_rows()
                if row["application_id"] == application_id
            )

            self.assertTrue(summary["ever_submitted"])
            self.assertTrue(summary["submission_attempted"])
            self.assertEqual(ledger_health(ledger.path)["status"], "healthy")
            summary_value = build_summary_v2(
                day="2026-08-07",
                applications=[
                    {
                        **summary,
                        "canonical_url": (
                            "https://jobs.ashbyhq.com/neuralconcept/"
                            "solution-engineer/application"
                        ),
                    }
                ],
            )
            self.assertEqual(
                summary_value["ats_progress"]["confirmed_adapters"], ["ashby"]
            )
            ledger.close()

    def test_ashby_projection_without_bundle_rejects_unbound_source_or_evidence(self):
        cases = (
            {
                "evidence_source": "untrusted_browser_claim",
            },
            {
                "evidence_source": "ashby_graphql_plus_visible_success",
                "evidence_sha256": "f" * 64,
            },
            {"event_fence": 2},
            {"event_intent_id": "other-intent"},
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                ledger, _, _ = self._authoritative_ashby_projection(
                    Path(directory),
                    **case,
                )

                with self.assertRaises(FenceError):
                    ledger.event_summary_rows()
                self.assertEqual(ledger_health(ledger.path)["status"], "unhealthy")
                ledger.close()

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
            outcomes = ledger.funnel_outcomes(application_id)
            self.assertEqual(len(outcomes), 1)
            self.assertEqual(
                {
                    key: outcomes[0][key]
                    for key in (
                        "funnel_stage",
                        "disposition",
                        "evidence_source",
                        "evidence_sha256",
                        "occurred_at",
                        "observed_at",
                        "observation_policy_version",
                    )
                },
                {
                    "funnel_stage": "confirmed_application",
                    "disposition": "positive",
                    "evidence_source": "gmail",
                    "evidence_sha256": "a" * 64,
                    "occurred_at": received_at,
                    "observed_at": received_at,
                    "observation_policy_version": None,
                },
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

            telemetry = RecordingTelemetry()
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
                telemetry=telemetry,
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
            self.assertEqual([span.name for span in telemetry.spans], ["confirmation.observe"])
            attributes = telemetry.spans[0].attributes
            self.assertEqual(attributes["application.id"], application_id)
            self.assertTrue(attributes["confirmation.observed"])
            self.assertRegex(attributes["evidence.sha256"], r"^[a-f0-9]{64}$")
            self.assertNotIn("gmail-message-2", json.dumps(attributes))

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

            telemetry = RecordingTelemetry()
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
                telemetry=telemetry,
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
            self.assertEqual([span.name for span in telemetry.spans], ["confirmation.observe"])
            self.assertFalse(telemetry.spans[0].attributes["confirmation.observed"])
            self.assertEqual(
                telemetry.spans[0].attributes["failure.code"],
                "no_exact_uncertain_application",
            )

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
