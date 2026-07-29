import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gig_healer.py"


def load():
    spec = importlib.util.spec_from_file_location("gig_healer_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load gig_healer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Result:
    def __init__(self, returncode=0, stderr="", stdout=""):
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout


class GigHealerTest(unittest.TestCase):
    def setUp(self):
        self.healer = load()

    def test_scheduler_restart_never_kills_an_active_revenue_pass(self):
        command = self.healer.repair_command("scheduler_restart", uid=501)
        self.assertEqual(command[-1], "gui/501/ai.anicca.hf-gig-pass")
        self.assertNotIn("-k", command)

    def test_lane_probe_uses_the_same_non_killing_kickstart(self):
        command = self.healer.repair_command("lane_probe", uid=501)
        self.assertEqual(command[-1], "gui/501/ai.anicca.hf-gig-pass")
        self.assertNotIn("-k", command)

    def test_browser_restart_is_isolated_to_the_gig_browser(self):
        command = self.healer.repair_command("browser_restart", uid=501)
        self.assertEqual(command[-1], "gui/501/ai.anicca.hf-gig-browser")
        self.assertIn("-k", command)

    def test_disk_recovery_kick_does_not_kill_an_active_cleanup(self):
        command = self.healer.repair_command("disk_recover", uid=501)
        self.assertEqual(
            command[-1],
            "gui/501/com.anicca.emergency-disk-guard",
        )
        self.assertNotIn("-k", command)

    def test_application_expansion_uses_non_killing_pass_kick(self):
        command = self.healer.repair_command("application_expand", uid=501)
        self.assertEqual(command[-1], "gui/501/ai.anicca.hf-gig-pass")
        self.assertNotIn("-k", command)

    def test_sandbox_recovery_uses_existing_non_killing_healthcheck(self):
        command = self.healer.repair_command("sandbox_recover", uid=501)
        self.assertEqual(
            command[-1],
            "gui/501/ai.anicca.hf-gig-core-healthcheck",
        )
        self.assertNotIn("-k", command)

    def test_telegram_repair_uses_receipt_reconcile_and_fenced_flush(self):
        for repair_class in ("telegram_reconcile", "telegram_probe"):
            command = self.healer.repair_command(repair_class, uid=501)
            self.assertIn("telegram_report.py", " ".join(command))
            self.assertIn("flush", command)
            self.assertNotIn("send", command)

    def test_unknown_and_unreconcilable_classes_are_not_dispatched(self):
        self.assertIsNone(self.healer.repair_command("lane_diagnose", uid=501))

    def test_schema_diagnosis_is_read_only_and_checks_all_runtime_schemas(self):
        result = self.healer.dispatch(
            "schema_diagnose",
            uid=501,
            incident={"evidence": {"failed_step": "B2"}},
            runner=lambda *args, **kwargs: self.fail("must not spawn a repair command"),
        )
        self.assertEqual(result["status"], "diagnosed")
        self.assertTrue(result["canary_passed"])
        self.assertGreaterEqual(result["schemas_checked"], 3)

    def test_provider_diagnosis_checks_executable_without_calling_provider(self):
        result = self.healer.dispatch(
            "provider_diagnose",
            uid=501,
            incident={"evidence": {
                "diagnosis_class": "provider_timeout",
                "diagnosis_evidence": {"attempt_executable": "/bin/sh"},
            }},
            runner=lambda *args, **kwargs: self.fail("must not call the provider"),
        )
        self.assertEqual(result["status"], "diagnosed")
        self.assertTrue(result["canary_passed"])
        self.assertEqual(result["diagnosis_class"], "provider_timeout")

    def test_unclassified_task_handoffs_to_life_manager_self_fix_with_tdd_rollback(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return Result(stdout="self-fix spawned")

        result = self.healer.dispatch(
            "task_diagnose",
            uid=501,
            incident={
                "incident_id": 42,
                "fingerprint": "task:unclassified:B2",
                "evidence": {
                    "failed_step": "B2",
                    "diagnosis_class": "task_failure_unclassified",
                },
            },
            runner=runner,
        )
        self.assertEqual(result["patch_handoff"], "spawned")
        command_text = " ".join(calls[0][0])
        self.assertIn("self-fix.sh", command_text)
        self.assertIn("failing regression test", command_text)
        self.assertIn("revert", command_text)
        self.assertIn("natural", command_text)
        self.assertFalse(calls[0][1]["shell"])

    def test_ledger_reconcile_calls_only_canonical_readback_healer(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "gig-pass-pass-2"
            agent = evidence / "agent-B2"
            agent.mkdir(parents=True)
            intent = agent / "gig-B2-5183000-submitted.intent.json"
            intent.write_text(json.dumps({"request_id": "5183000"}))
            calls = []

            def runner(command, **kwargs):
                calls.append((command, kwargs))
                return Result(stdout=json.dumps({
                    "status": "reconciled",
                    "recovered": 1,
                    "request_ids": ["5183000"],
                }))

            result = self.healer.dispatch(
                "ledger_reconcile",
                uid=501,
                incident={"evidence": {
                    "pass_id": "pass-2",
                    "evidence_dir": str(evidence),
                }},
                runner=runner,
            )
            self.assertEqual(result["status"], "dispatched")
            self.assertEqual(result["recovered"], 1)
            self.assertIn("application_ledger_heal.py", " ".join(calls[0][0]))
            self.assertNotIn("submit", " ".join(calls[0][0]).lower())
            self.assertFalse(calls[0][1]["shell"])


    def test_dispatch_passes_an_argument_vector_without_a_shell(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return Result()

        result = self.healer.dispatch("scheduler_restart", uid=501, runner=runner)
        self.assertEqual(result["status"], "dispatched")
        self.assertEqual(calls[0][1]["shell"], False)
        self.assertEqual(calls[0][1]["timeout"], 20)

    def test_nonzero_dispatch_is_not_called_recovered(self):
        result = self.healer.dispatch(
            "browser_restart",
            uid=501,
            runner=lambda *args, **kwargs: Result(returncode=3, stderr="launch failed"),
        )
        self.assertEqual(result["status"], "dispatch_failed")
        self.assertEqual(result["returncode"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
