import tempfile
import fcntl
import sqlite3
from unittest.mock import patch
import unittest
from pathlib import Path

from runtime.loop.lm_loop_lifecycle import lifecycle, lifecycle_one
from runtime.host.resource_admission import owner_deploy_lock
from runtime.host import resource_admission as admission


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
    def setUp(self):
        self.state_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.state_directory.cleanup)
        environment = patch.dict("os.environ", {
            "LIFE_MANAGER_RESOURCE_ADMISSION_ROOT": self.state_directory.name,
        })
        environment.start()
        self.addCleanup(environment.stop)

    def test_start_does_not_run_while_same_owner_is_locked(self):
        with tempfile.TemporaryDirectory() as directory:
            agents = Path(directory)
            (agents / "ai.anicca.a.plist").write_text("plist")
            calls = []
            with owner_deploy_lock("a") as acquired:
                self.assertTrue(acquired)
                result = lifecycle_one(
                    "start", "a", REGISTRY["loops"]["a"], agents,
                    lambda args: (calls.append(args) or (0, "loaded")),
                )
            self.assertNotEqual(result["return_code"], 0)
            self.assertEqual(calls, [])

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

    def test_stop_suspends_durable_admission_after_bootout(self):
        with tempfile.TemporaryDirectory() as directory:
            actions = []

            def launchctl(args):
                self.assertEqual(args[0], "bootout")
                return 0, ""

            result = lifecycle_one(
                "stop", "a", REGISTRY["loops"]["a"], Path(directory), launchctl,
                admission=actions.append,
            )

            self.assertEqual(result["return_code"], 0)
            self.assertEqual(actions, ["suspend"])

    def test_start_resumes_durable_admission_after_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            agents = Path(directory)
            (agents / "ai.anicca.a.plist").write_text("plist")
            actions = []

            def launchctl(args):
                if args[0] == "print":
                    return (1, "") if len(actions) == 0 else (0, "loaded")
                actions.append(args[0])
                return 0, ""

            result = lifecycle_one(
                "start", "a", REGISTRY["loops"]["a"], agents, launchctl,
                admission=lambda action: actions.append(action),
            )

            self.assertEqual(result["return_code"], 0)
            self.assertEqual(actions, ["bootstrap", "resume"])

    def test_stop_does_not_assume_unloaded_on_preflight_error(self):
        actions = []
        result = lifecycle_one(
            "stop", "a", REGISTRY["loops"]["a"], Path(self.state_directory.name),
            lambda args: (77, "preflight failed"), admission=actions.append,
        )
        self.assertNotEqual(result["return_code"], 0)
        self.assertEqual(actions, [])

    def test_stop_retries_suspend_after_control_busy_and_unloaded_readback(self):
        root = Path(self.state_directory.name)
        admission.activate_durable_v2()
        admission.enqueue_durable("deterministic", "a", admission_class="revenue",
                                  occurrence_id="a:wake")
        loaded = True
        def launchctl(args):
            nonlocal loaded
            if args[0] == "bootout" and loaded:
                loaded = False
                return 0, ""
            return 113, "Could not find service"
        callback = lambda action: admission.suspend_durable("a")
        with (root / "control.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            first = lifecycle_one("stop", "a", REGISTRY["loops"]["a"], root,
                                  launchctl, admission=callback)
        self.assertNotEqual(first["return_code"], 0)
        second = lifecycle_one("stop", "a", REGISTRY["loops"]["a"], root,
                               launchctl, admission=callback)
        self.assertEqual(second["return_code"], 0)
        with sqlite3.connect(root / "admission-v2.sqlite3") as db:
            eligible = db.execute("SELECT next_eligible_at FROM priorities WHERE owner_id='a'").fetchone()[0]
        self.assertEqual(eligible, float("inf"))

    def test_stop_reports_a_failed_admission_suspend(self):
        with tempfile.TemporaryDirectory() as directory:
            result = lifecycle_one(
                "stop", "a", REGISTRY["loops"]["a"], Path(directory),
                lambda args: (0, ""), admission=lambda action: False,
            )
            self.assertNotEqual(result["return_code"], 0)
            self.assertIn("admission", result["detail"])

    def test_start_reports_a_failed_admission_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            agents = Path(directory)
            (agents / "ai.anicca.a.plist").write_text("plist")
            def launchctl(args):
                return 0, "loaded"
            result = lifecycle_one(
                "start", "a", REGISTRY["loops"]["a"], agents, launchctl,
                admission=lambda action: False,
            )
            self.assertNotEqual(result["return_code"], 0)
            self.assertIn("admission", result["detail"])

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
