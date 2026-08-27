import json
import plistlib
import tempfile
import unittest
from pathlib import Path

from runtime.loop.lm_loop_apply import apply_registry, build_apply_plan, install_one


SHA = "a" * 40


def registry(entrypoint="bin/example.sh"):
    return {"schema_version": 2, "loops": {"example": {
        "label": "ai.anicca.example", "domain": "system", "entrypoint": entrypoint,
        "cadence": {"start_interval_seconds": 60}, "effect_class": "none",
        "state_root": "~/.local/state/life-manager/example",
        "log_root": "~/.local/state/life-manager/example/logs",
        "cleanup": {"max_runs": 10, "max_age_days": 7},
        "provider_route": "deterministic",
    }}}


class LmLoopApplyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "bin").mkdir()
        (self.root / "bin/example.sh").write_text("#!/bin/sh\nexit 0\n")
        (self.root / "bin/example.sh").chmod(0o755)
        (self.root / "bin/lm-loop-run").write_text("#!/bin/sh\nexit 0\n")
        (self.root / "bin/lm-loop-run").chmod(0o755)
        (self.root / "RELEASE.json").write_text(json.dumps({"sha": SHA}))

    def tearDown(self):
        self.temp.cleanup()

    def test_rendered_plist_is_deterministic_and_release_exact(self):
        first = build_apply_plan(registry(), self.root, SHA)
        second = build_apply_plan(registry(), self.root, SHA)
        self.assertEqual(first[0]["plist_bytes"], second[0]["plist_bytes"])
        value = plistlib.loads(first[0]["plist_bytes"])
        self.assertEqual(value["ProgramArguments"], [
            str(self.root.resolve() / "bin/lm-loop-run"), "example", str(self.root.resolve())])
        self.assertEqual(value["StartInterval"], 60)
        self.assertEqual(value["EnvironmentVariables"]["LIFE_MANAGER_RELEASE_SHA"], SHA)

    def test_invalid_generation_causes_zero_installer_calls(self):
        calls = []
        with self.assertRaisesRegex(ValueError, "missing entrypoint"):
            apply_registry(registry("bin/missing.sh"), self.root, SHA, calls.append)
        self.assertEqual(calls, [])

    def test_non_executable_entrypoint_is_rejected_before_install(self):
        (self.root / "bin/example.sh").chmod(0o644)
        calls = []
        with self.assertRaisesRegex(ValueError, "not executable"):
            apply_registry(registry(), self.root, SHA, calls.append)
        self.assertEqual(calls, [])

    def test_valid_generation_installs_after_complete_preflight(self):
        calls = []
        result = apply_registry(registry(), self.root, SHA, lambda item: calls.append(item) or {
            "label": item["label"], "loaded_arguments": item["expected_arguments"], "ok": True,
        })
        self.assertEqual(len(calls), 1)
        self.assertEqual(result[0]["loaded_arguments"], calls[0]["expected_arguments"])

    def test_failed_swap_restores_previous_plist_and_loaded_job(self):
        target = self.root / "installed.plist"
        old = plistlib.dumps({"Label": "ai.anicca.example", "ProgramArguments": ["/old/run.sh"]})
        target.write_bytes(old)
        rendered = build_apply_plan(registry(), self.root, SHA)[0]
        calls = []

        def launchctl(args):
            calls.append(args)
            if args[0] == "print" and len(calls) == 1:
                return 0, "arguments = {\n/old/run.sh\n}\n"
            if args[0] == "bootstrap" and target.read_bytes() != old:
                return 5, "new bootstrap failed"
            if args[0] == "print":
                return 0, "arguments = {\n/old/run.sh\n}\n"
            return 0, ""

        with self.assertRaisesRegex(RuntimeError, "restored previous job"):
            install_one(rendered, target, launchctl, attempts=1)
        self.assertEqual(target.read_bytes(), old)
        self.assertGreaterEqual(sum(call[0] == "bootstrap" for call in calls), 2)


if __name__ == "__main__":
    unittest.main()
