import json
import unittest
from pathlib import Path


class ApprovedRouteDefaultTest(unittest.TestCase):
    def test_every_executable_agent_class_uses_its_approved_single_route(self):
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
                        {"provider": "codex", "model": "gpt-5.6-luna", "effort": "high"},
                        {"provider": "codex", "model": "gpt-5.6-terra", "effort": "medium"},
                    ]
                if name == "browser-lane-agent":
                    expected = [
                        {"provider": "codex", "model": "gpt-5.6-luna", "effort": "xhigh"},
                    ]
                self.assertEqual(candidates, expected)

    def test_browser_lane_is_one_bounded_explicit_route_and_all_callers_explain_it(self):
        runner_root = Path(__file__).resolve().parents[1]
        repo_root = runner_root.parents[1]
        config = json.loads((runner_root / "config.json").read_text(encoding="utf-8"))
        route = config["task_classes"]["browser-lane-agent"]

        self.assertEqual(route["route"], "luna-xhigh-browser-loop")
        self.assertEqual(route["timeout_seconds"], 900)
        self.assertTrue(route["requires_explicit_escalation"])
        self.assertEqual(len(route["candidates"]), 1)
        for caller in (
            repo_root / "apps" / "job-search-loop" / "scripts" / "run-daily.sh",
            repo_root / "apps" / "job-search-loop" / "job_search_loop" / "agent_runner.py",
        ):
            with self.subTest(caller=caller):
                source = caller.read_text(encoding="utf-8")
                self.assertIn("--escalation-reason", source)
                self.assertIn("mandatory-model-browser-loop", source)

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
