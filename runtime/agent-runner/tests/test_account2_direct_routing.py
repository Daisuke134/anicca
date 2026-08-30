#!/usr/bin/env python3
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "runtime" / "agent-runner" / "config.json"
sys.path.insert(0, str(CONFIG.parent))
from agent_runner import resolve_provider_profiles  # noqa: E402


class CodexProfileRoutingTest(unittest.TestCase):
    def test_all_task_classes_expand_codex_candidates_through_configured_failover_order(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        provider = config["providers"]["codex"]
        profiles = provider["profiles"]
        order = provider["account_profile_order"]
        self.assertEqual(set(profiles), {"acct1", "acct2"})
        self.assertEqual(order, ["acct1", "acct2"])

        for task_name, task in config["task_classes"].items():
            logical_candidates = task.get("candidates", [])
            resolved = resolve_provider_profiles(logical_candidates, config["providers"])
            cursor = 0
            for logical in logical_candidates:
                if logical.get("provider") != "codex":
                    self.assertEqual(resolved[cursor], logical, task_name)
                    cursor += 1
                    continue

                for position, profile_alias in enumerate(order):
                    with self.subTest(task_class=task_name, model=logical.get("model"), profile=profile_alias):
                        expected = {
                            **logical,
                            "profile_alias": profile_alias,
                            "automation_home": profiles[profile_alias]["automation_home"],
                            "auth_file": profiles[profile_alias]["auth_file"],
                            "account_fallback_next": position == 0,
                        }
                        self.assertEqual(resolved[cursor], expected)
                    cursor += 1

            self.assertEqual(cursor, len(resolved), task_name)


if __name__ == "__main__": unittest.main()
