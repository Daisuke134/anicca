import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from job_search_loop.guardian import ledger_health
from job_search_loop.ledger import Ledger


class GuardianLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "ledger.sqlite3"
        self.ledger = Ledger(self.path)
        self.application_id = self.ledger.add_application(
            "Example", "AI Engineer", "https://jobs.example.com/guardian"
        )

    def tearDown(self):
        self.ledger.close()
        self.tempdir.cleanup()

    def health(self):
        return ledger_health(
            self.path, now=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        )

    def test_valid_event_ledger_is_healthy_and_contains_only_counts(self):
        self.ledger.transition(self.application_id, "qualified")
        report = self.health()
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(report["application_count"], 1)
        self.assertEqual(report["event_count"], 2)
        self.assertEqual(report["stale_submission_claim_count"], 0)
        self.assertNotIn(self.application_id, str(report))

    def test_missing_trigger_and_projection_drift_are_reported(self):
        self.ledger.connection.execute("DROP TRIGGER events_no_delete")
        self.ledger.connection.execute(
            "DROP TRIGGER applications_state_requires_event"
        )
        self.ledger.connection.execute(
            "UPDATE applications SET current_state='qualified' WHERE id=?",
            (self.application_id,),
        )
        report = self.health()
        self.assertEqual(report["status"], "unhealthy")
        self.assertIn("required_trigger_missing", report["reasons"])
        self.assertIn("event_projection_mismatch", report["reasons"])
        self.assertIn("events_no_delete", report["missing_triggers"])

    def test_stale_unfinished_submission_fence_is_reported(self):
        self.ledger.connection.execute(
            """
            INSERT INTO submit_intents
              (intent_id, application_id, fence, payload_hash, japan_day, slot,
               status, created_at)
            VALUES ('intent-stale', ?, 1, 'payload', '2026-08-05', 1,
                    'submit_claimed', '2026-08-05T08:00:00+00:00')
            """,
            (self.application_id,),
        )
        report = self.health()
        self.assertEqual(report["status"], "unhealthy")
        self.assertEqual(report["active_submission_claim_count"], 1)
        self.assertEqual(report["stale_submission_claim_count"], 1)
        self.assertIn("stale_submission_claim", report["reasons"])

    def test_permissions_other_than_owner_read_write_are_unhealthy(self):
        os.chmod(self.path, 0o644)
        report = self.health()
        self.assertEqual(report["status"], "unhealthy")
        self.assertIn("ledger_permissions_invalid", report["reasons"])


if __name__ == "__main__":
    unittest.main()
