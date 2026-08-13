import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_runner import provider_process_env


class ApplicationIntentIsolationTest(unittest.TestCase):
    def setUp(self):
        self.source = {
            "PATH": "/usr/bin:/bin",
            "CODEX_HOME": "/tmp/codex",
            "LANCERS_CDP_URL": "http://127.0.0.1:9227",
            "PLAYWRIGHT_WS_ENDPOINT": "ws://localhost:9227/devtools/browser/secret",
            "MARKETPLACE_TOKEN": "fixture-token",
        }

    def test_application_intent_planner_removes_browser_routes_only(self):
        child_env = provider_process_env(
            "codex",
            {},
            self.source,
            task_class="application-intent-planner",
        )

        self.assertEqual(child_env["PATH"], "/usr/bin:/bin")
        self.assertEqual(child_env["CODEX_HOME"], "/tmp/codex")
        self.assertEqual(child_env["MARKETPLACE_TOKEN"], "fixture-token")
        self.assertNotIn("LANCERS_CDP_URL", child_env)
        self.assertNotIn("PLAYWRIGHT_WS_ENDPOINT", child_env)

    def test_normal_task_preserves_original_environment(self):
        child_env = provider_process_env("codex", {}, self.source)

        self.assertEqual(child_env, self.source)

    def test_application_intent_planner_config(self):
        config_path = ROOT / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(config["task_classes"]["application-intent-planner"], {
            "route": "luna-medium-isolated-application-intent",
            "token_reservation": 24576,
            "timeout_seconds": 180,
            "candidates": [
                {"provider": "codex", "model": "gpt-5.6-luna", "effort": "medium"},
                {"provider": "codex", "model": "gpt-5.6-terra", "effort": "medium"},
            ],
        })


if __name__ == "__main__":
    unittest.main()
