import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "token_budget.py"


def load_module():
    spec = importlib.util.spec_from_file_location("token_budget", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load token_budget")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TokenBudgetTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.module = load_module()
        self.ledger = self.module.TokenBudgetLedger(self.root / "budget.jsonl")

    def reserve(self, event_id, scope_id, reservation=30):
        return self.ledger.reserve(
            event_id=event_id,
            loop="gig",
            scope_id=scope_id,
            day="2026-07-23",
            daily_scope="gig",
            reservation_tokens=reservation,
            pass_limit=100,
            daily_limit=100,
        )

    def test_actual_charge_replaces_reservation_and_blocks_pass_then_day(self):
        first = self.reserve("event-1", "pass-1")
        self.assertEqual(first["status"], "allowed")
        self.ledger.settle(
            event_id="event-1",
            actual_tokens=80,
            measurement="provider_reported",
        )

        same_pass = self.reserve("event-2", "pass-1")
        self.assertEqual(same_pass["status"], "blocked")
        self.assertEqual(same_pass["reason"], "pass_token_budget_exceeded")

        next_pass = self.reserve("event-3", "pass-2")
        self.assertEqual(next_pass["status"], "blocked")
        self.assertEqual(next_pass["reason"], "loop_daily_token_budget_exceeded")

    def test_unsettled_reservation_remains_charged_after_crash(self):
        first = self.reserve("event-crash", "pass-crash", reservation=60)
        second = self.reserve("event-next", "pass-crash", reservation=50)

        self.assertEqual(first["status"], "allowed")
        self.assertEqual(second["status"], "blocked")
        self.assertEqual(second["pass_consumed_tokens"], 60)


if __name__ == "__main__":
    unittest.main()
