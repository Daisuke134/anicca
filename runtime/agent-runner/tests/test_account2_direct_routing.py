#!/usr/bin/env python3
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "runtime" / "agent-runner" / "config.json"


class CodexProfileRoutingTest(unittest.TestCase):
    def test_every_codex_route_names_the_single_supported_profile(self):
        config = json.loads(CONFIG.read_text()); provider = config["providers"]["codex"]
        self.assertNotIn("accounts", provider)
        self.assertEqual(set(provider["profiles"]), {"acct2"})
        codex = [candidate for task in config["task_classes"].values()
                 for candidate in task["candidates"] if candidate["provider"] == "codex"]
        self.assertTrue(codex)
        self.assertEqual({candidate.get("profile_alias") for candidate in codex}, {"acct2"})


if __name__ == "__main__": unittest.main()
