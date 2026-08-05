import sqlite3
import tempfile
import unittest
from pathlib import Path

from job_search_loop.guardian import telegram_outbox_health


class GuardianTelegramOutboxTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "outbox.sqlite3"
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            """CREATE TABLE outbox(
              event_key TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL,
              fence TEXT, telegram_message_id TEXT, created_at TEXT NOT NULL,
              claimed_at TEXT, send_started_at TEXT, completed_at TEXT)"""
        )
        self.connection.execute(
            "INSERT INTO outbox VALUES('daily','body','sent','fence','701',?,NULL,?,?)",
            ("2026-08-05T11:00:00+00:00", "2026-08-05T11:01:00+00:00", "2026-08-05T11:01:01+00:00"),
        )
        self.connection.commit()
        self.path.chmod(0o600)

    def tearDown(self):
        self.connection.close()
        self.tempdir.cleanup()

    def test_valid_sent_rows_are_healthy_and_payload_is_private(self):
        report = telegram_outbox_health(self.path)
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(report["counts"], {"sent": 1})
        self.assertNotIn("body", str(report))
        self.assertNotIn("701", str(report))

    def test_send_started_is_uncertain_and_never_retried_by_health(self):
        self.connection.execute(
            "INSERT INTO outbox VALUES('x','secret','send_started','f',NULL,?, ?, ?, NULL)",
            ("2026-08-05T11:00:00+00:00", "2026-08-05T11:00:01+00:00", "2026-08-05T11:00:02+00:00"),
        )
        self.connection.commit()
        report = telegram_outbox_health(self.path)
        self.assertEqual(report["uncertain_count"], 1)
        self.assertIn("telegram_side_effect_uncertain", report["reasons"])
        self.assertEqual(self.connection.execute("SELECT status FROM outbox WHERE event_key='x'").fetchone()[0], "send_started")

    def test_legacy_schema_without_lease_timestamps_is_unhealthy(self):
        self.connection.close()
        self.path.unlink()
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            "CREATE TABLE outbox(event_key TEXT PRIMARY KEY,payload TEXT NOT NULL,status TEXT NOT NULL,fence TEXT,telegram_message_id TEXT)"
        )
        self.connection.commit(); self.path.chmod(0o600)
        report = telegram_outbox_health(self.path)
        self.assertIn("telegram_outbox_timestamps_missing", report["reasons"])


if __name__ == "__main__": unittest.main()
