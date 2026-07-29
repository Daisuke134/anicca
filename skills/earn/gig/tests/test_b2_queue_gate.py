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
    def test_every_unresolved_higher_priority_class_blocks_b2_generically(self):
        for queue_class in sorted(gate.BLOCKING_QUEUE_CLASSES):
            with self.subTest(queue_class=queue_class):
                reason = gate.policy_skip_reason(
                    {"items": [{"queue_class": queue_class, "contract_id": "dynamic-1"}]}
                )
                self.assertEqual(
                    reason,
                    f"B2:unresolved_higher_priority_queue:{queue_class}:dynamic-1",
                )

    def test_clear_lower_priority_queue_allows_b2(self):
        self.assertIsNone(gate.policy_skip_reason({"items": []}))
        self.assertIsNone(
            gate.policy_skip_reason(
                {"items": [{"queue_class": "nurture", "contract_id": "dynamic-2"}]}
            )
        )

    def test_invalid_queue_fails_closed_with_exit_two(self):
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


if __name__ == "__main__":
    unittest.main()
