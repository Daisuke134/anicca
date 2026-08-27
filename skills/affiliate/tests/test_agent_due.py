from __future__ import annotations

import importlib.util
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "agent_due.py"


class AgentDueTests(unittest.TestCase):
    def test_not_due_skips_runner_and_due_calls_once_with_receipt(self) -> None:
        self.assertTrue(MODULE_PATH.is_file(), f"missing due gate: {MODULE_PATH}")
        spec = importlib.util.spec_from_file_location("agent_due", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        now = datetime(2026, 8, 22, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            calls = []
            not_due = module.run(
                state, goal_id="goal-1", job_id="job-1",
                next_due_at="2026-08-23T00:00:00+00:00", now=now,
                invoke_budgeted_runner=lambda: calls.append(True),
            )
            self.assertEqual(not_due["state"], "NOT_DUE")
            self.assertEqual(not_due["model_call_count"], 0)
            self.assertEqual(calls, [])

            summary = {
                "status": "success", "attempt_count": 1,
                "budget": {"status": "allowed", "reservation_tokens": 32768},
            }
            first = module.run(
                state, goal_id="goal-1", job_id="job-1",
                next_due_at="2026-08-21T00:00:00+00:00", now=now,
                invoke_budgeted_runner=lambda: calls.append(True) or summary,
            )
            duplicate = module.run(
                state, goal_id="goal-1", job_id="job-1",
                next_due_at="2026-08-21T00:00:00+00:00", now=now,
                invoke_budgeted_runner=lambda: calls.append(True) or summary,
            )
            self.assertEqual(first["state"], "MODEL_CALLED")
            self.assertEqual(first["model_call_count"], 1)
            self.assertEqual(duplicate, first)
            self.assertEqual(calls, [True])

    def test_budget_blocked_summary_proves_zero_model_calls(self) -> None:
        self.assertTrue(MODULE_PATH.is_file(), f"missing due gate: {MODULE_PATH}")
        spec = importlib.util.spec_from_file_location("agent_due_blocked", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as root:
            calls = []
            receipt = module.run(
                Path(root), goal_id="goal-1", job_id="job-1",
                next_due_at="2026-08-21T00:00:00Z",
                now=datetime(2026, 8, 22, tzinfo=timezone.utc),
                invoke_budgeted_runner=lambda: calls.append("blocked") or {
                    "status": "budget_blocked", "attempt_count": 0,
                    "budget": {"status": "blocked", "reason": "pass_token_budget_exceeded"},
                },
            )
            self.assertEqual(receipt["state"], "BUDGET_BLOCKED")
            self.assertEqual(receipt["model_call_count"], 0)
            next_day = module.run(
                Path(root), goal_id="goal-1", job_id="job-1",
                next_due_at="2026-08-21T00:00:00Z",
                now=datetime(2026, 8, 23, tzinfo=timezone.utc),
                invoke_budgeted_runner=lambda: calls.append("allowed") or {
                    "status": "success", "attempt_count": 1,
                    "budget": {"status": "allowed", "reservation_tokens": 32768},
                },
            )
            self.assertEqual(next_day["state"], "MODEL_CALLED")
            self.assertEqual(calls, ["blocked", "allowed"])


if __name__ == "__main__":
    unittest.main()
