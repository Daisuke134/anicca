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
                    {"provider": "codex", "model": "gpt-5.6-terra", "effort": "medium"},
                ]
                if name == "application-intent-planner":
                    expected = [
                        {"provider": "codex", "model": "gpt-5.6-luna", "effort": "medium"},
                        {"provider": "codex", "model": "gpt-5.6-terra", "effort": "medium"},
                    ]
                self.assertEqual(candidates, expected)


if __name__ == "__main__":
    unittest.main()
