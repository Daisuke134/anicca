import tempfile
import unittest
from pathlib import Path

from runtime.loop.lm_loop_lifecycle import lifecycle, lifecycle_one


REGISTRY = {"schema_version": 2, "loops": {
    key: {"label": f"ai.anicca.{key}", "domain": "system", "entrypoint": f"bin/{key}.sh",
          "cadence": {"run_at_load": True}, "effect_class": "none",
          "state_root": f"~/.local/state/life-manager/{key}",
          "log_root": f"~/.local/state/life-manager/{key}/logs",
          "cleanup": {"max_runs": 10, "max_age_days": 7},
          "provider_route": "deterministic"}
    for key in ("a", "b", "c")
}}


class LmLoopLifecycleTest(unittest.TestCase):
    def test_all_collects_every_label_result_after_failure(self):
        calls = []
        def execute(action, loop_id, entry):
            calls.append(loop_id)
            return {"loop_id": loop_id, "label": entry["label"],
                    "action": action, "return_code": 7 if loop_id == "b" else 0}
        result = lifecycle(REGISTRY, "restart", "all", execute)
        self.assertEqual(calls, ["a", "b", "c"])
        self.assertEqual([row["return_code"] for row in result], [0, 7, 0])

    def test_start_bootstraps_unloaded_and_kickstarts_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            agents = Path(directory)
            (agents / "ai.anicca.a.plist").write_text("plist")
            calls = []
            def launchctl(args):
                calls.append(args)
                if args[0] == "print":
                    return (1, "") if len(calls) == 1 else (0, "loaded")
                return 0, ""
            result = lifecycle_one("start", "a", REGISTRY["loops"]["a"], agents, launchctl)
            self.assertEqual(result["return_code"], 0)
            self.assertEqual([call[0] for call in calls], ["print", "bootstrap", "print"])

    def test_restart_boots_out_then_bootstraps_and_reads_back(self):
        with tempfile.TemporaryDirectory() as directory:
            agents = Path(directory)
            (agents / "ai.anicca.a.plist").write_text("plist")
            calls = []
            def launchctl(args):
                calls.append(args)
                return 0, "loaded"
            result = lifecycle_one("restart", "a", REGISTRY["loops"]["a"], agents, launchctl)
            self.assertEqual(result["return_code"], 0)
            self.assertEqual([call[0] for call in calls], ["bootout", "bootstrap", "print"])

    def test_unknown_loop_is_rejected_without_execution(self):
        calls = []
        with self.assertRaisesRegex(ValueError, "unknown loop id"):
            lifecycle(REGISTRY, "start", "missing", lambda *args: calls.append(args))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
