"""A13: the apply lane no longer depends on the paid queue's contents.

This file used to assert the opposite -- that any unresolved paid item shut B2 --
and its sibling ``test_b2_queue_gate_ledger_done.py`` asserted which paid items
counted as resolved. Both encoded the dependency that
`docs/loop-engineering/35-gig-no-head-of-line-blocking-design.md` §4 rule 3
removes, so the sibling is deleted and this one now pins the new contract:
★ a readable queue never closes the apply lane, whatever is in it. ★
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "b2_queue_gate.py"
SPEC = importlib.util.spec_from_file_location("b2_queue_gate", SCRIPT)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class B2QueueGateTest(unittest.TestCase):
    def test_no_paid_class_in_any_state_closes_the_apply_lane(self):
        # The live 2026-08-08 jam: 91000001 stuck at buyer_feedback_or_revision with
        # a live blocker shut B2 on six consecutive passes.
        for queue_class in sorted(gate.BLOCKING_QUEUE_CLASSES):
            with self.subTest(queue_class=queue_class):
                self.assertIsNone(
                    gate.policy_skip_reason(
                        {
                            "items": [
                                {
                                    "queue_class": queue_class,
                                    "request_id": "91000001",
                                    "delivery_action": "formal",
                                    "blockers": ["formal_delivery_not_confirmed"],
                                }
                            ]
                        }
                    )
                )

    def test_a_stuck_paid_order_does_not_hide_a_later_lower_priority_item(self):
        self.assertIsNone(
            gate.policy_skip_reason(
                {
                    "items": [
                        {"queue_class": "buyer_feedback_or_revision", "request_id": "91000001"},
                        {"queue_class": "listing_apply_learn", "contract_id": "dynamic-2"},
                    ]
                }
            )
        )

    def test_clear_lower_priority_queue_allows_b2(self):
        self.assertIsNone(gate.policy_skip_reason({"items": []}))
        self.assertIsNone(
            gate.policy_skip_reason(
                {"items": [{"queue_class": "nurture", "contract_id": "dynamic-2"}]}
            )
        )

    def test_a_projects_root_is_accepted_and_ignored(self):
        # Kept in the signature so the CLI and its call sites did not have to change
        # in the same edit; no ledger is consulted any more.
        self.assertIsNone(
            gate.policy_skip_reason(
                {"items": [{"queue_class": "other_paid_work", "talkroom_id": "90000004"}]},
                projects_root="/nonexistent/projects",
            )
        )

    def test_invalid_queue_fails_closed_with_exit_two(self):
        # A queue that cannot be parsed, or that carries a routing value no consumer
        # in this repository knows, is a statement about the FILE. That still refuses.
        for invalid in (
            {},
            {"items": {}},
            {"items": ["not-an-object"]},
            {"items": [{}]},
            {"items": [{"queue_class": "unknown-future-state"}]},
        ):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "queue.json"
                path.write_text(json.dumps(invalid), encoding="utf-8")
                self.assertEqual(gate.main([str(path)]), 2)

    def test_a_well_formed_queue_exits_one_so_the_pass_runs_b2(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "queue.json"
            path.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "queue_class": "buyer_feedback_or_revision",
                                "request_id": "91000001",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            # gig_pass.sh runs B2 on any non-zero rc that is not 2.
            self.assertEqual(gate.main([str(path)]), 1)


if __name__ == "__main__":
    unittest.main()
