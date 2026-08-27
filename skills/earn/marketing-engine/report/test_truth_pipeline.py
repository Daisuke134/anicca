from __future__ import annotations

import fcntl
import importlib.util
import pathlib
import sys
import tempfile
import unittest


MODULE_PATH = pathlib.Path(__file__).with_name("truth_pipeline.py")
SPEC = importlib.util.spec_from_file_location("truth_pipeline", MODULE_PATH)
assert SPEC and SPEC.loader
truth_pipeline = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = truth_pipeline
SPEC.loader.exec_module(truth_pipeline)


class TruthPipelineTest(unittest.TestCase):
    def test_commands_are_serialized_reconcile_collect_report_without_paid_tools(self):
        root = pathlib.Path("/repo")
        home = pathlib.Path("/home/owner")
        commands = truth_pipeline.build_commands(root, home, python="/python")
        rendered = [" ".join(command) for command in commands]
        self.assertIn("publication_ledger.py", rendered[0])
        self.assertIn("native_metrics.py", rendered[1])
        self.assertEqual(
            [command[command.index("--kind") + 1] for command in commands[2:]],
            ["action", "checkpoint", "incident", "experiment"],
        )
        self.assertNotIn("apify", " ".join(rendered).lower())

    def test_nonblocking_lock_prevents_overlapping_external_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = pathlib.Path(tmp) / "truth.lock"
            lock_path.touch()
            calls = []
            with lock_path.open("r+") as held:
                fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = truth_pipeline.run_pipeline(
                    [["one"], ["two"]],
                    lock_path=lock_path,
                    run_command=lambda command: calls.append(command) or 0,
                )
        self.assertEqual(result["status"], "locked")
        self.assertEqual(calls, [])

    def test_failure_does_not_suppress_health_reporting(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def runner(command: list[str]) -> int:
                calls.append(command[0])
                return 1 if command[0] == "collect" else 0

            result = truth_pipeline.run_pipeline(
                [["reconcile"], ["collect"], ["report"]],
                lock_path=pathlib.Path(tmp) / "truth.lock",
                run_command=runner,
            )
        self.assertEqual(calls, ["reconcile", "collect", "report"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_stages"], ["collect"])


if __name__ == "__main__":
    unittest.main()
