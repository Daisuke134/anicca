#!/usr/bin/env python3
from __future__ import annotations

import pathlib
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


if __name__ == "__main__":
    unittest.main()
