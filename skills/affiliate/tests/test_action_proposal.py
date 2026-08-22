from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "action_proposal.py"


class ActionProposalTests(unittest.TestCase):
    def test_invalid_proposals_fail_before_dispatch_and_valid_action_dispatches_once(self) -> None:
        self.assertTrue(MODULE_PATH.is_file(), f"missing proposal validator: {MODULE_PATH}")
        spec = importlib.util.spec_from_file_location("action_proposal", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        base = {
            "schema_version": 1,
            "goal_id": "goal-1",
            "job_id": "job-1",
            "rationale": "Official money evidence is due.",
            "action": {
                "command": "revenue reconcile",
                "authority": "MONEY_RECONCILE",
                "argv": [],
                "confidence": 0.9,
            },
        }
        invalid = [
            {**base, "extra": True},
            {**base, "rationale": "x" * 1001},
            {**base, "action": {**base["action"], "confidence": 1.1}},
            {**base, "action": {**base["action"], "authority": "WRITE_EXTERNAL"}},
            {**base, "action": {**base["action"], "command": "unknown command"}},
            {**base, "wait": {"reason": "NO_DUE_ACTION", "next_due_at": "2026-08-23T00:00:00Z"}},
            {key: value for key, value in base.items() if key != "action"},
        ]
        calls = []
        for proposal in invalid:
            with self.subTest(proposal=proposal):
                with self.assertRaises(module.ProposalError):
                    module.apply(proposal, lambda action: calls.append(action))
        self.assertEqual(calls, [])

        result = module.apply(base, lambda action: calls.append(action) or {"state": "OK"})
        self.assertEqual(result, {"state": "OK"})
        self.assertEqual(calls, [base["action"]])

    def test_valid_durable_wait_never_dispatches(self) -> None:
        self.assertTrue(MODULE_PATH.is_file(), f"missing proposal validator: {MODULE_PATH}")
        spec = importlib.util.spec_from_file_location("action_proposal_wait", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        calls = []
        proposal = {
            "schema_version": 1, "goal_id": "goal-1", "job_id": "job-1",
            "rationale": "Nothing is due.",
            "wait": {"reason": "NO_DUE_ACTION", "next_due_at": "2026-08-23T00:00:00Z"},
        }
        self.assertEqual(module.apply(proposal, lambda action: calls.append(action)), {
            "state": "WAITING", **proposal["wait"],
        })
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
