"""X20: the daily token breaker must be a real per-day, per-owner circuit breaker.

Measured 2026-07-27 from ~/.local/state/anicca/telemetry/token-budget.jsonl:
every gig LaunchAgent reserved under loop="gig", so the auditor's 262144 daily
limit was evaluated against the revenue pass's spend. 41 of 132 reservations
were blocked with loop_daily_token_budget_exceeded while daily_consumed_tokens
had already reached 1,412,241 against a recorded daily_limit_tokens of 262,144.
That is one shared pool with two disagreeing limits, not two budgets.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent-runner"))

from token_budget import TokenBudgetLedger, budget_day_for  # noqa: E402


class BudgetDayTest(unittest.TestCase):
    """The 'daily' budget must reset at JST midnight, not at 09:00 JST.

    The loop sells to Japanese buyers on a JST calendar. A UTC day boundary
    hands a runaway a fresh full allowance in the middle of the workday.
    """

    def test_jst_evening_belongs_to_the_jst_day_not_the_utc_day(self):
        from datetime import datetime, timezone
        # 2026-07-27 23:30 JST == 2026-07-27 14:30 UTC
        now = datetime(2026, 7, 27, 14, 30, tzinfo=timezone.utc)
        self.assertEqual(budget_day_for(now, "Asia/Tokyo"), "2026-07-27")
        self.assertEqual(budget_day_for(now, "UTC"), "2026-07-27")

    def test_utc_late_evening_is_already_the_next_jst_day(self):
        from datetime import datetime, timezone
        # 2026-07-27 23:30 UTC == 2026-07-28 08:30 JST
        now = datetime(2026, 7, 27, 23, 30, tzinfo=timezone.utc)
        self.assertEqual(budget_day_for(now, "Asia/Tokyo"), "2026-07-28")
        self.assertEqual(budget_day_for(now, "UTC"), "2026-07-27")

    def test_jst_early_morning_is_still_its_own_jst_day(self):
        from datetime import datetime, timezone
        # 2026-07-27 00:30 JST == 2026-07-26 15:30 UTC
        now = datetime(2026, 7, 26, 15, 30, tzinfo=timezone.utc)
        self.assertEqual(budget_day_for(now, "Asia/Tokyo"), "2026-07-27")
        self.assertEqual(budget_day_for(now, "UTC"), "2026-07-26")


class DailyTokenBudgetScopeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = TokenBudgetLedger(Path(self.temp.name) / "token-budget.jsonl")

    def reserve(self, *, event_id, scope_id, daily_scope, day="2026-07-27",
                tokens=100, pass_limit=1000, daily_limit=1000):
        return self.ledger.reserve(
            event_id=event_id,
            loop="gig",
            scope_id=scope_id,
            daily_scope=daily_scope,
            day=day,
            reservation_tokens=tokens,
            pass_limit=pass_limit,
            daily_limit=daily_limit,
        )

    def test_daily_pool_is_shared_across_pass_scopes_of_one_owner(self):
        """A per-pass scope must not hand out a fresh daily allowance."""
        self.reserve(event_id="a", scope_id="pass-1", daily_scope="gig-pass")
        second = self.reserve(event_id="b", scope_id="pass-2", daily_scope="gig-pass")
        self.assertEqual(second["daily_consumed_tokens"], 100)
        self.assertEqual(second["status"], "allowed")

    def test_separate_owners_do_not_drain_each_others_daily_pool(self):
        """The auditor must not be blocked by what the revenue pass spent."""
        for index in range(9):
            allowed = self.reserve(
                event_id=f"pass-{index}", scope_id=f"p{index}",
                daily_scope="gig-pass", daily_limit=1000,
            )
            self.assertEqual(allowed["status"], "allowed")
        auditor = self.reserve(
            event_id="audit-1", scope_id="audit-pass-1",
            daily_scope="gig-auditor", daily_limit=300,
        )
        self.assertEqual(auditor["status"], "allowed")
        self.assertEqual(auditor["daily_consumed_tokens"], 0)

    def test_daily_scope_is_recorded_on_every_reservation(self):
        decision = self.reserve(event_id="a", scope_id="p1", daily_scope="gig-pass")
        self.assertEqual(decision["daily_scope"], "gig-pass")
        row = json.loads(self.ledger.path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["daily_scope"], "gig-pass")

    def test_daily_limit_blocks_once_the_pool_is_exhausted(self):
        self.reserve(event_id="a", scope_id="p1", daily_scope="gig-pass",
                     tokens=900, daily_limit=1000, pass_limit=10000)
        blocked = self.reserve(event_id="b", scope_id="p2", daily_scope="gig-pass",
                               tokens=200, daily_limit=1000, pass_limit=10000)
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["reason"], "loop_daily_token_budget_exceeded")

    def test_next_day_resets_the_pool(self):
        self.reserve(event_id="a", scope_id="p1", daily_scope="gig-pass",
                     tokens=900, daily_limit=1000, pass_limit=10000)
        fresh = self.reserve(event_id="b", scope_id="p2", daily_scope="gig-pass",
                             day="2026-07-28", tokens=200,
                             daily_limit=1000, pass_limit=10000)
        self.assertEqual(fresh["status"], "allowed")
        self.assertEqual(fresh["daily_consumed_tokens"], 0)

    def test_legacy_rows_without_daily_scope_count_against_the_loop_pool(self):
        """History written before X20 has no daily_scope; it must not vanish."""
        self.ledger.path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.path.write_text(json.dumps({
            "version": 1, "type": "reservation", "event_id": "legacy",
            "loop": "gig", "scope_id": "old-pass", "day": "2026-07-27",
            "status": "allowed", "reason": None, "reservation_tokens": 400,
        }) + "\n", encoding="utf-8")
        same = self.reserve(event_id="new", scope_id="p1", daily_scope="gig")
        self.assertEqual(same["daily_consumed_tokens"], 400)
        other = self.reserve(event_id="new2", scope_id="p1", daily_scope="gig-pass")
        self.assertEqual(other["daily_consumed_tokens"], 0)

    def test_daily_scope_must_be_nonempty(self):
        with self.assertRaises(Exception):
            self.reserve(event_id="a", scope_id="p1", daily_scope="")

    def test_settlement_charges_the_owners_pool_not_the_loops(self):
        self.reserve(event_id="a", scope_id="p1", daily_scope="gig-pass",
                     tokens=100, daily_limit=1000, pass_limit=1000)
        self.reserve(event_id="b", scope_id="audit", daily_scope="gig-auditor",
                     tokens=100, daily_limit=1000, pass_limit=1000)
        settled = self.ledger.settle(
            event_id="a", actual_tokens=500, measurement="provider_reported",
        )
        self.assertEqual(settled["daily_consumed_after_tokens"], 500)


if __name__ == "__main__":
    unittest.main()
