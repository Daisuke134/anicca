import pathlib
import plistlib
import sys
import tempfile
import unittest


HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import install_gate8_schedules as installer  # noqa: E402


class ScheduleInstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.repo = self.repo.resolve()
        self.home = self.home.resolve()
        self.launch_agents = self.home / "Library" / "LaunchAgents"
        self.launch_agents.mkdir(parents=True)
        (self.repo / "skills/earn/marketing-engine/bin").mkdir(parents=True)
        (self.repo / "skills/earn/marketing-engine/bin/lm").write_text("#!/bin/sh\n")
        (self.repo / "skills/earn/marketing-engine/report").mkdir(parents=True)
        (self.repo / "skills/earn/marketing-engine/report/scheduled_runner.py").write_text("")
        self.daily = self.launch_agents / "ai.anicca.marketing-mine-daily.plist"
        self.weekly = self.launch_agents / "ai.anicca.marketing-weekly-review.plist"
        self._write(self.daily, {
            "Label": "ai.anicca.marketing-mine-daily",
            "ProgramArguments": ["python3", str(self.repo / "skills/earn/marketing-engine/report/scheduled_runner.py"), "mine"],
            "WorkingDirectory": str(self.repo),
            "StartCalendarInterval": {"Hour": 5, "Minute": 30},
        })
        self._write(self.weekly, {
            "Label": "ai.anicca.marketing-weekly-review",
            "ProgramArguments": ["python3", "/old/weekly_review.py"],
            "WorkingDirectory": str(self.repo),
            "StartCalendarInterval": {"Weekday": 0, "Hour": 21, "Minute": 0},
            "StandardOutPath": "/old/out.log", "StandardErrorPath": "/old/err.log",
        })

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _write(path, value):
        with path.open("wb") as handle:
            plistlib.dump(value, handle)

    def test_apply_is_reversible_idempotent_and_preserves_cadence(self):
        backup = self.root / "backups"
        first = installer.install(
            repo=self.repo, home=self.home, backup_root=backup, apply=True,
            launchctl=lambda args: 0,
        )
        weekly = plistlib.loads(self.weekly.read_bytes())
        daily = plistlib.loads(self.daily.read_bytes())
        self.assertTrue(first["weekly"]["changed"])
        self.assertFalse(first["daily"]["changed"])
        self.assertEqual({"Weekday": 0, "Hour": 21, "Minute": 0}, weekly["StartCalendarInterval"])
        self.assertEqual([str(self.repo / "skills/earn/marketing-engine/bin/lm"), "intel", "gap", "--telegram"], weekly["ProgramArguments"])
        self.assertEqual("mine", daily["ProgramArguments"][-1])
        self.assertTrue((backup / self.weekly.name).is_file())
        second = installer.install(
            repo=self.repo, home=self.home, backup_root=backup, apply=False,
            launchctl=lambda args: self.fail("launchctl must not run in plan mode"),
        )
        self.assertFalse(second["weekly"]["would_change"])
        self.assertFalse(second["daily"]["would_change"])

    def test_refuses_daily_schedule_that_no_longer_owns_mine_lane(self):
        value = plistlib.loads(self.daily.read_bytes())
        value["ProgramArguments"][-1] = "score"
        self._write(self.daily, value)
        with self.assertRaisesRegex(ValueError, "daily mine"):
            installer.install(repo=self.repo, home=self.home, backup_root=self.root / "b", apply=False)


if __name__ == "__main__":
    unittest.main()
