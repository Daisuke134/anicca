#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import tempfile
import unittest

import run_contract
import scheduled_runner


class ScheduledRunnerTests(unittest.TestCase):
    def test_registry_has_exactly_the_contract_runners(self):
        registry = scheduled_runner.load_registry()
        self.assertEqual(set(registry), set(run_contract.RUNNERS))

    def test_registry_has_no_openclaw_dependency(self):
        registry = scheduled_runner.load_registry()
        for runner_id, item in registry.items():
            with self.subTest(runner_id=runner_id):
                self.assertNotIn("openclaw", " ".join(item["command"]).lower())

    def test_only_verified_read_lanes_through_current_gate_are_unquarantined(self):
        registry = scheduled_runner.load_registry()
        active = {key for key, value in registry.items() if value["quarantine_reason"] is None}
        self.assertEqual(active, {"mine", "metrics", "dashboard"})
        self.assertEqual(registry["mine"]["command"][-2:], ["intel", "daily"])

    def test_placeholders_resolve_to_existing_entrypoints(self):
        registry = scheduled_runner.load_registry()
        for runner_id, item in registry.items():
            command = scheduled_runner.resolve_command(item["command"])
            with self.subTest(runner_id=runner_id):
                self.assertTrue(pathlib.Path(command[0]).exists())
                if len(command) > 1 and command[1].endswith((".py", ".sh")):
                    self.assertTrue(pathlib.Path(command[1]).exists())

    def test_managed_loop_defaults_are_outside_the_immutable_release(self):
        state, evidence = scheduled_runner.default_roots({
            "LIFE_MANAGER_STATE_ROOT": "/tmp/marketing-dashboard",
        })
        self.assertEqual(state, pathlib.Path("/tmp/marketing-dashboard/state"))
        self.assertEqual(evidence, pathlib.Path("/tmp/marketing-dashboard/evidence/runs"))

    def test_mine_command_seeds_mutable_state_and_routes_all_writes_outside_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            command = scheduled_runner.prepare_mine_command(
                ["lm", "intel", "daily"], root / "state", root / "evidence")
            intel_root = root / "state" / "intel"
            self.assertTrue((intel_root / "sources.json").is_file())
            self.assertTrue((intel_root / "playbook.jsonl").is_file())
            self.assertFalse((intel_root / "intel_daily.py").exists())
            self.assertEqual(command[-4:], [
                "--intel-root", str(intel_root),
                "--evidence-root", str(root / "evidence" / "intel-daily"),
            ])


if __name__ == "__main__":
    unittest.main()
