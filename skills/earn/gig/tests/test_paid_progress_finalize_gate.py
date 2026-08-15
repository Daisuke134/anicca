import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "paid_progress_finalize_gate.py"
SPEC = importlib.util.spec_from_file_location("paid_progress_finalize_gate", SCRIPT)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class PaidProgressFinalizeGateTest(unittest.TestCase):
    def test_only_validated_progress_with_formal_pending_qualifies(self):
        item = {
            "queue_class": "buyer_feedback_or_revision",
            "delivery_action": "progress",
            "blockers": ["formal_delivery_not_confirmed"],
        }
        self.assertEqual(
            gate.finalize_reason(item),
            "validated_paid_progress_formal_pending:buyer_feedback_or_revision",
        )

    def test_formal_action_or_unexpected_blocker_does_not_qualify(self):
        base = {
            "queue_class": "other_paid_work",
            "delivery_action": "progress",
            "blockers": ["formal_delivery_not_confirmed"],
        }
        for patch in (
            {"delivery_action": "formal"},
            {"delivery_action": "none"},
            {"blockers": []},
            {"blockers": ["formal_delivery_not_confirmed", "unexpected_blocker"]},
        ):
            with self.subTest(patch=patch):
                self.assertIsNone(gate.finalize_reason({**base, **patch}))

    def test_malformed_input_fails_closed_with_exit_two(self):
        for invalid in ({}, {"queue_class": "paid", "delivery_action": "progress", "blockers": "bad"}):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "item.json"
                path.write_text(json.dumps(invalid), encoding="utf-8")
                self.assertEqual(gate.main([str(path)]), 2)


if __name__ == "__main__":
    unittest.main()
