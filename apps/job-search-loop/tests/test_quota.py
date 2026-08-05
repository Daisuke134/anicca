import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import Ledger


class QuotaTests(unittest.TestCase):
    def quota_module(self):
        try:
            from job_search_loop import quota
        except ImportError:
            self.fail("job_search_loop.quota is missing")
        return quota

    def seed_submitted(self, ledger: Ledger, *, day: str, buckets: list[str]) -> None:
        for index, bucket in enumerate(buckets, start=1):
            application_id = f"application-{day}-{index}"
            ledger.connection.execute(
                "INSERT INTO applications "
                "(id, company, title, canonical_url, current_state, created_at) "
                "VALUES (?, ?, 'AI Role', ?, 'submitted', '2026-08-05T00:00:00Z')",
                (application_id, f"Company {index}", f"https://jobs.example/{application_id}"),
            )
            ledger.connection.execute(
                "INSERT INTO daily_slots "
                "(japan_day, slot, application_id, portfolio_bucket, status) "
                "VALUES (?, ?, ?, ?, 'submitted')",
                (day, index, application_id, bucket),
            )

    def test_deficit_event_is_idempotent_and_records_bucket_shortfall(self):
        quota = self.quota_module()
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            self.seed_submitted(
                ledger,
                day="2026-08-05",
                buckets=["dream", "strong_fit", "strong_fit", "strong_fit", "adjacent", "adjacent"],
            )
            first = quota.record_quota_deficit(
                ledger, day="2026-08-05", reason="hourly_pass_complete"
            )
            second = quota.record_quota_deficit(
                ledger, day="2026-08-05", reason="hourly_pass_complete"
            )
            events = ledger.quota_deficit_events("2026-08-05")
            ledger.close()

        self.assertEqual(first["event_id"], second["event_id"])
        self.assertEqual(len(events), 1)
        self.assertEqual(first["confirmed_count"], 6)
        self.assertEqual(first["deficit_count"], 4)
        self.assertEqual(
            first["portfolio_deficit"],
            {"dream": 1, "strong_fit": 2, "adjacent": 1},
        )

    def test_ten_confirmed_creates_no_deficit_event(self):
        quota = self.quota_module()
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            self.seed_submitted(
                ledger,
                day="2026-08-05",
                buckets=["dream"] * 2 + ["strong_fit"] * 5 + ["adjacent"] * 3,
            )
            result = quota.record_quota_deficit(
                ledger, day="2026-08-05", reason="hourly_pass_complete"
            )
            events = ledger.quota_deficit_events("2026-08-05")
            ledger.close()

        self.assertIsNone(result)
        self.assertEqual(events, [])

    def test_legacy_submitted_slots_count_toward_total_confirmed(self):
        quota = self.quota_module()
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            self.seed_submitted(
                ledger,
                day="2026-08-05",
                buckets=["legacy_unallocated", "dream"],
            )
            event = quota.record_quota_deficit(
                ledger, day="2026-08-05", reason="hourly_pass_complete"
            )
            ledger.close()

        self.assertEqual(event["confirmed_count"], 2)
        self.assertEqual(event["deficit_count"], 8)
