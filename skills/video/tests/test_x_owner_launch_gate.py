#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "x-launch" / "gate.py"
SPEC = importlib.util.spec_from_file_location("x_owner_launch_gate", MODULE_PATH)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(gate)


class XOwnerLaunchGateTests(unittest.TestCase):
    def test_live_canonical_spec_blocks_handoff_until_all_core_and_marketing_rows_done(self):
        canonical = Path(__file__).resolve().parents[3] / "docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md"
        result = gate.evaluate(canonical.read_text(encoding="utf-8"), [])
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blockers"], ["9c", "9d"])
        self.assertEqual(result["owner_handoff_allowed"], False)
        self.assertEqual(result["agent_posting_allowed"], False)

    def test_all_done_rows_allow_only_minimal_owner_handoff_never_agent_posting(self):
        spec = "\n".join(
            f"| {row} | feature | requirement | **done (L3)** |"
            for row in gate.REQUIRED_ROWS
        )
        result = gate.evaluate(spec, [])
        self.assertEqual(result["status"], "ready_for_owner_handoff")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["owner_handoff_allowed"], True)
        self.assertEqual(result["agent_posting_allowed"], False)

    def test_missing_rows_fail_closed(self):
        result = gate.evaluate("| 9b | feature | requirement | **done** |", [])
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blockers"], ["8e", "8f", "9c", "9d", "9e"])

    def test_real_x_url_in_append_only_ledger_makes_launch_one_time(self):
        spec = "\n".join(
            f"| {row} | feature | requirement | **done** |"
            for row in gate.REQUIRED_ROWS
        )
        result = gate.evaluate(
            spec,
            [{"status": "published_by_owner", "public_url": "https://x.com/dais/status/123"}],
        )
        self.assertEqual(result["status"], "already_done")
        self.assertEqual(result["owner_handoff_allowed"], False)
        self.assertEqual(result["agent_posting_allowed"], False)

    def test_cli_emits_closed_json_without_mutating_ledger(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec = root / "spec.md"
            spec.write_text("| 9b | feature | requirement | **done** |\n", encoding="utf-8")
            ledger = root / "ledger.jsonl"
            result = gate.run(spec, ledger)
            self.assertEqual(result["status"], "blocked")
            self.assertFalse(ledger.exists())


if __name__ == "__main__":
    unittest.main()
