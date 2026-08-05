import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from job_search_loop.guardian_recovery import bounded_recovery, main
from job_search_loop.outbox import Outbox


class GuardianRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.database = self.root / "outbox.sqlite3"

    def tearDown(self):
        self.tempdir.cleanup()

    def test_outbox_records_each_side_effect_boundary_timestamp(self):
        outbox = Outbox(self.database)
        outbox.enqueue("one", "body")
        fence = outbox.claim("one")
        outbox.mark_send_started("one", fence)
        outbox.mark_sent("one", fence, "701")
        columns = {row[1] for row in outbox.connection.execute("PRAGMA table_info(outbox)")}
        row = outbox.connection.execute(
            "SELECT created_at,claimed_at,send_started_at,completed_at FROM outbox"
        ).fetchone()
        outbox.close()
        self.assertTrue({"created_at", "claimed_at", "send_started_at", "completed_at"}.issubset(columns))
        self.assertTrue(all(row))

    def test_only_stale_pre_send_claim_is_recovered(self):
        outbox = Outbox(self.database)
        outbox.enqueue("safe", "body")
        safe_fence = outbox.claim("safe")
        outbox.enqueue("unsafe", "body")
        unsafe_fence = outbox.claim("unsafe")
        outbox.mark_send_started("unsafe", unsafe_fence)
        outbox.connection.execute(
            "UPDATE outbox SET claimed_at='2026-08-05T08:00:00+00:00'"
        )
        alerts = []
        report = bounded_recovery(
            outbox_database=self.database,
            private_paths=[],
            now=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
            alert=lambda value: alerts.append(value),
        )
        safe = outbox.status("safe")
        unsafe = outbox.status("unsafe")
        outbox.close()
        self.assertEqual(safe["status"], "pending")
        self.assertEqual(unsafe["status"], "send_started")
        self.assertEqual(report["recovered_pre_send_claim_count"], 1)
        self.assertEqual(report["uncertain_side_effect_count"], 1)
        self.assertEqual(len(alerts), 1)
        self.assertNotIn(safe_fence, str(report))
        self.assertNotIn(unsafe_fence, str(report))

    def test_recovery_is_bounded_to_three_claims_and_one_alert(self):
        outbox = Outbox(self.database)
        for index in range(5):
            key = f"event-{index}"
            outbox.enqueue(key, "body")
            outbox.claim(key)
        outbox.connection.execute(
            "UPDATE outbox SET claimed_at='2026-08-05T08:00:00+00:00'"
        )
        alerts = []
        report = bounded_recovery(
            outbox_database=self.database,
            private_paths=[],
            now=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
            alert=lambda value: alerts.append(value),
        )
        remaining = outbox.connection.execute(
            "SELECT COUNT(*) FROM outbox WHERE status='claimed'"
        ).fetchone()[0]
        outbox.close()
        self.assertEqual(report["recovered_pre_send_claim_count"], 3)
        self.assertEqual(remaining, 2)
        self.assertEqual(len(alerts), 1)

    def test_private_permission_repair_is_bounded_and_verified(self):
        paths = [self.root / f"report-{index}.json" for index in range(4)]
        for path in paths:
            path.write_text("{}")
            path.chmod(0o644)
        report = bounded_recovery(
            outbox_database=self.database,
            private_paths=paths,
            now=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
            alert=lambda value: None,
        )
        self.assertEqual(report["repaired_permission_count"], 3)
        self.assertEqual(sum((path.stat().st_mode & 0o777) == 0o600 for path in paths), 3)

    def test_alert_transport_failure_is_not_retried(self):
        calls = []
        report = bounded_recovery(
            outbox_database=self.database,
            private_paths=[],
            now=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
            alert=lambda value: (calls.append(value), (_ for _ in ()).throw(RuntimeError("fail")))[1],
        )
        self.assertEqual(len(calls), 1)
        self.assertFalse(report["alert_sent"])

    def test_cli_migrates_legacy_schema_before_counting_uncertain_rows(self):
        connection = sqlite3.connect(self.database)
        connection.execute(
            "CREATE TABLE outbox(event_key TEXT PRIMARY KEY,payload TEXT NOT NULL,status TEXT NOT NULL,fence TEXT,telegram_message_id TEXT)"
        )
        connection.execute(
            "INSERT INTO outbox VALUES('unknown','body','send_started','fence',NULL)"
        )
        connection.commit(); connection.close()
        executable = self.root / "fake-openclaw"
        executable.write_text("#!/bin/sh\necho '{\"messageId\":\"801\"}'\n")
        executable.chmod(0o700)
        output = self.root / "recovery.json"
        self.assertEqual(main([
            "--outbox", str(self.database), "--output", str(output),
            "--openclaw", str(executable),
        ]), 0)
        report = __import__("json").loads(output.read_text())
        self.assertEqual(report["uncertain_side_effect_count"], 1)
        connection = sqlite3.connect(self.database)
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(outbox)")
        }
        connection.close()
        self.assertIn("send_started_at", columns)


if __name__ == "__main__": unittest.main()
