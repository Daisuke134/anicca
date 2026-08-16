from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "composition_owner.py"


class CompositionOwnerTests(unittest.TestCase):
    def test_wake_advances_only_one_due_source_set_and_dedupes_terminal_receipt(self) -> None:
        spec = importlib.util.spec_from_file_location("affiliate_composition_owner", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"
            inbox = state / "composition-inbox"
            inbox.mkdir(parents=True)
            bundle = {
                "schema_version": 1,
                "receipt_type": "COMPOSITION_INPUT",
                "plan_id": "alpha-en",
                "locale": "en",
                "source_set_sha256": "a" * 64,
                "sources": [],
            }
            (inbox / "alpha-en.json").write_text(json.dumps(bundle), encoding="utf-8")
            completed = {
                "state": "READY_FOR_POLICY",
                "plan_id": "alpha-en",
                "locale": "en",
                "source_set_sha256": "a" * 64,
                "result_sha256": "b" * 64,
            }
            run_model = mock.Mock(return_value=completed)
            build_handoff = mock.Mock(return_value="c" * 64)

            first = module.wake(
                root, state, run_model=run_model, handoff_builder=build_handoff
            )
            second = module.wake(
                root, state, run_model=run_model, handoff_builder=build_handoff
            )

            self.assertEqual(first["state"], "READY_FOR_POLICY")
            self.assertEqual(second["state"], "IDLE")
            self.assertEqual(run_model.call_count, 1)
            self.assertEqual(build_handoff.call_count, 1)
            receipt = json.loads(
                (state / "composition-receipts" / "alpha-en.json").read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["source_set_sha256"], "a" * 64)
            self.assertEqual(receipt["handoff_sha256"], "c" * 64)


if __name__ == "__main__":
    unittest.main()
