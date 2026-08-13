import tempfile
import unittest
from pathlib import Path

from job_search_loop import recovery
from job_search_loop.ledger import Ledger


class RecoveryTests(unittest.TestCase):
    def test_every_wake_searches_all_buckets_and_sources_without_a_fixed_target(self):
        plan = recovery.build_discovery_plan(confirmed_count=1_000)

        self.assertEqual(plan["version"], 2)
        self.assertEqual(plan["status"], "active")
        self.assertEqual(plan["confirmed_count"], 1_000)
        self.assertEqual(
            {row["bucket"] for row in plan["queries"]},
            {"dream", "strong_fit", "adjacent"},
        )
        self.assertEqual(
            set(plan["source_scopes"]),
            {scope for tier in recovery.SOURCE_TIERS for scope in tier},
        )
        self.assertEqual(set(plan["hard_gates"]), set(recovery.HARD_GATES))
        self.assertNotIn("portfolio_deficit", plan)
        self.assertNotIn("quota_met", plan.values())

    def test_historical_quota_events_do_not_stop_continuous_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            event = ledger.record_quota_deficit(
                japan_day="2026-08-05",
                confirmed_count=10,
                portfolio_confirmed={"dream": 2, "strong_fit": 5, "adjacent": 3},
                portfolio_deficit={"dream": 0, "strong_fit": 0, "adjacent": 0},
                reason="historical",
            )
            plan = recovery.build_runtime_plan(ledger, day="2026-08-05")
            events = ledger.quota_deficit_events("2026-08-05")
            ledger.close()

        self.assertEqual(events[0]["event_id"], event["event_id"])
        self.assertEqual(plan["status"], "active")
        self.assertGreater(len(plan["queries"]), 0)
