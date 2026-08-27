import json
import unittest
from pathlib import Path


class TerraDefaultTest(unittest.TestCase):
    def test_every_executable_agent_class_prefers_terra(self):
        config_path = Path(__file__).resolve().parents[1] / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))

        for name, task_class in config["task_classes"].items():
            candidates = task_class.get("candidates", [])
            if not candidates:
                continue
            with self.subTest(task_class=name):
                expected = [
                    {"provider": "codex", "model": "gpt-5.6-terra", "effort": "medium", "profile_alias": "acct2"},
                ]
                if name == "application-intent-planner":
                    expected = [
                        {"provider": "codex", "model": "gpt-5.6-luna", "effort": "high", "profile_alias": "acct2"},
                        {"provider": "codex", "model": "gpt-5.6-terra", "effort": "medium", "profile_alias": "acct2"},
                    ]
                if name == "reply-semantic-agent":
                    expected = [{"provider": "codex", "model": "gpt-5.6-luna",
                                 "effort": "medium", "timeout_seconds": 120,
                                 "profile_alias": "acct2"}]
                if name == "writer-sol-audit":
                    expected = [{"provider": "codex", "model": "gpt-5.6-sol",
                                 "effort": "medium", "profile_alias": "acct2"}]
                if name == "writer-repair-agent":
                    expected = [{"provider": "codex", "model": "gpt-5.6-terra",
                                 "effort": "medium", "profile_alias": "acct2"}]
                if name == "affiliate-marketing-agent":
                    expected = [{"provider": "codex", "model": "gpt-5.6-terra",
                                 "effort": "high", "profile_alias": "acct2"}]
                if name == "affiliate-escalation-agent":
                    expected = [{"provider": "codex", "model": "gpt-5.6-sol",
                                 "effort": "high", "profile_alias": "acct2"}]
                if name in {"storefront-proposal-agent", "browser-lane-agent", "escalation-agent"}:
                    expected.append(
                        {"provider": "claude", "model": "claude-sonnet-5"}
                    )
                self.assertEqual(candidates, expected)

    def test_a_restricted_candidate_carries_its_escalation_route(self):
        """Without the route the runner raises at the first wake, not at review time."""
        config_path = Path(__file__).resolve().parents[1] / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))

        for name, task_class in config["task_classes"].items():
            restricted = [
                candidate for candidate in task_class.get("candidates", [])
                if candidate.get("effort") in {"high", "xhigh", "max"}
                or "sol" in str(candidate.get("model") or "").lower()
            ]
            if not restricted:
                continue
            with self.subTest(task_class=name):
                self.assertTrue(task_class.get("requires_explicit_escalation"))


if __name__ == "__main__":
    unittest.main()
