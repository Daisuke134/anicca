import unittest
import tempfile
from pathlib import Path

from job_search_loop.ledger import Ledger


class RecoveryTests(unittest.TestCase):
    def module(self):
        try:
            from job_search_loop import recovery
        except ImportError:
            self.fail("job_search_loop.recovery is missing")
        return recovery

    def test_deficit_expands_every_missing_bucket_without_weakening_gates(self):
        recovery = self.module()
        plan = recovery.build_recovery_plan(
            portfolio_deficit={"dream": 1, "strong_fit": 2, "adjacent": 1},
            consecutive_deficits=1,
        )

        self.assertEqual(plan["status"], "expanded")
        self.assertEqual(
            {row["bucket"] for row in plan["queries"]},
            {"dream", "strong_fit", "adjacent"},
        )
        self.assertIn("official_company_careers", plan["source_scopes"])
        self.assertIn("ashby", plan["source_scopes"])
        self.assertEqual(set(plan["hard_gates"]), set(recovery.HARD_GATES))
        self.assertTrue(all(row["language"] in {"en", "ja"} for row in plan["queries"]))

    def test_repeated_deficit_adds_sources_and_queries_monotonically(self):
        recovery = self.module()
        first = recovery.build_recovery_plan(
            portfolio_deficit={"dream": 1, "strong_fit": 0, "adjacent": 0},
            consecutive_deficits=1,
        )
        third = recovery.build_recovery_plan(
            portfolio_deficit={"dream": 1, "strong_fit": 0, "adjacent": 0},
            consecutive_deficits=3,
        )

        self.assertTrue(set(first["source_scopes"]) < set(third["source_scopes"]))
        self.assertLess(len(first["queries"]), len(third["queries"]))
        self.assertEqual(first["hard_gates"], third["hard_gates"])

    def test_no_missing_bucket_does_not_expand(self):
        recovery = self.module()
        plan = recovery.build_recovery_plan(
            portfolio_deficit={"dream": 0, "strong_fit": 0, "adjacent": 0},
            consecutive_deficits=0,
        )
        self.assertEqual(plan["status"], "quota_met")
        self.assertEqual(plan["queries"], [])

    def test_empty_new_day_starts_level_one_recovery_without_prior_event(self):
        recovery = self.module()
        self.assertTrue(hasattr(recovery, "build_runtime_plan"))
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            plan = recovery.build_runtime_plan(ledger, day="2026-08-05")
            ledger.close()

        self.assertEqual(plan["status"], "expanded")
        self.assertEqual(plan["expansion_level"], 1)
        self.assertEqual(
            plan["portfolio_deficit"],
            {"dream": 2, "strong_fit": 5, "adjacent": 3},
        )
