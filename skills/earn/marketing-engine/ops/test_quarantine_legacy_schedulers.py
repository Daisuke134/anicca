from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("quarantine_legacy_schedulers.py")
SPEC = importlib.util.spec_from_file_location("quarantine_legacy_schedulers", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class FakeRunner:
    def __init__(self, launchctl: str = "PID\tStatus\tLabel\n", fail_at: int | None = None):
        self.launchctl = launchctl
        self.fail_at = fail_at
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if self.fail_at is not None and len(self.commands) == self.fail_at:
            raise subprocess.CalledProcessError(1, command)
        stdout = self.launchctl if command == ["launchctl", "list"] else ""
        return subprocess.CompletedProcess(command, 0, stdout, "")


class QuarantineTest(unittest.TestCase):
    def make_snapshot(self, root: Path, rows: list[dict]) -> dict:
        for row in rows:
            source = Path(row["source_path"])
            source.write_text(row.get("source_text", "source"))
            row["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
            row.pop("source_text", None)
        return {"host_uid": os.getuid(), "captured_at": "2026-08-01T00:00:00Z", "records": rows}

    def test_dry_run_does_not_mutate_and_skips_migrate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self.make_snapshot(root, [
                {"runtime": "launchd", "id": "ai.anicca.larry-one", "source_path": str(root / "one"), "enabled": True, "disposition": "retire"},
                {"runtime": "launchd", "id": "ai.anicca.marketing-metrics", "source_path": str(root / "two"), "enabled": True, "disposition": "migrate"},
            ])
            runner = FakeRunner()
            result = module.quarantine(snapshot, False, runner)
        self.assertEqual(result["target_count"], 1)
        self.assertEqual(runner.commands, [["launchctl", "list"]])

    def test_running_publisher_blocks_all_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self.make_snapshot(root, [{"runtime": "launchd", "id": "ai.anicca.reelclaw-one", "source_path": str(root / "one"), "enabled": True, "disposition": "retire"}])
            runner = FakeRunner("PID\tStatus\tLabel\n99\t0\tai.anicca.reelclaw-one\n")
            with self.assertRaisesRegex(module.QuarantineError, "refusing to interrupt"):
                module.quarantine(snapshot, True, runner)
        self.assertEqual(runner.commands, [["launchctl", "list"]])

    def test_changed_source_blocks_all_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self.make_snapshot(root, [{"runtime": "openclaw", "id": "11111111-1111-1111-1111-111111111111", "source_path": str(root / "jobs"), "enabled": True, "disposition": "retire"}])
            (root / "jobs").write_text("changed")
            runner = FakeRunner()
            with self.assertRaisesRegex(module.QuarantineError, "source changed"):
                module.quarantine(snapshot, True, runner)
        self.assertEqual(runner.commands, [["launchctl", "list"]])

    def test_apply_uses_reversible_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self.make_snapshot(root, [
                {"runtime": "launchd", "id": "ai.anicca.watercolor-one", "source_path": str(root / "one"), "enabled": True, "disposition": "retire"},
                {"runtime": "openclaw", "id": "11111111-1111-1111-1111-111111111111", "source_path": str(root / "jobs"), "enabled": True, "disposition": "retire"},
            ])
            runner = FakeRunner()
            result = module.quarantine(snapshot, True, runner)
        self.assertEqual(result["status"], "quarantined")
        self.assertIn(["launchctl", "disable", f"gui/{os.getuid()}/ai.anicca.watercolor-one"], runner.commands)
        self.assertIn(["launchctl", "bootout", f"gui/{os.getuid()}/ai.anicca.watercolor-one"], runner.commands)
        self.assertIn(["openclaw", "cron", "disable", "11111111-1111-1111-1111-111111111111"], runner.commands)

    def test_failure_rolls_back_changed_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = self.make_snapshot(root, [{"runtime": "launchd", "id": "ai.anicca.larry-one", "source_path": str(root / "one"), "enabled": True, "disposition": "retire"}])
            runner = FakeRunner(fail_at=3)
            with self.assertRaises(module.QuarantineError):
                module.quarantine(snapshot, True, runner)
        self.assertIn(["launchctl", "enable", f"gui/{os.getuid()}/ai.anicca.larry-one"], runner.commands)
        self.assertIn(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(root / "one")], runner.commands)

    def test_rejects_unreviewed_target_family(self):
        snapshot = {"host_uid": os.getuid(), "records": [{"runtime": "launchd", "id": "ai.anicca.life-manager", "enabled": True, "disposition": "retire"}]}
        with self.assertRaisesRegex(module.QuarantineError, "outside reviewed families"):
            module.quarantine(snapshot, True, FakeRunner())


if __name__ == "__main__":
    unittest.main()
