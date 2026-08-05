import plistlib
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from job_search_loop.guardian import schedule_health


class GuardianScheduleTests(unittest.TestCase):
    def setup_runtime(self, root):
        plists = root / "plists"
        launchers = root / "launchers"
        evidence = root / "evidence"
        plists.mkdir(); launchers.mkdir(); evidence.mkdir()
        schedules = {
            "daily": {"StartInterval": 3600},
            "inbox": {"StartInterval": 300},
            "learning": {"StartCalendarInterval": {"Weekday": 1, "Hour": 9, "Minute": 15}},
        }
        for lane, schedule in schedules.items():
            launcher = launchers / lane
            launcher.write_text("#!/bin/zsh\nexit 0\n")
            launcher.chmod(0o555)
            value = {
                "Label": f"ai.anicca.job-search-{lane}",
                "ProgramArguments": [str(launcher)],
                "RunAtLoad": True,
                **schedule,
            }
            with (plists / f"ai.anicca.job-search-{lane}.plist").open("wb") as handle:
                plistlib.dump(value, handle)
            run = evidence / f"{lane}-20260805-120000"
            run.mkdir()
            timestamp = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc).timestamp()
            os.utime(run, (timestamp, timestamp))
        return plists, launchers, evidence

    def reader(self, label):
        lane = label.rsplit("-", 1)[-1]
        if lane == "daily":
            return None
        interval = "run interval = 300 seconds\n" if lane == "inbox" else ""
        return f"state = not running\nruns = 2\nlast exit code = 0\n{interval}"

    def test_expected_schedules_and_intentional_daily_disable_are_healthy(self):
        with tempfile.TemporaryDirectory() as directory:
            plists, launchers, evidence = self.setup_runtime(Path(directory))
            report = schedule_health(
                plist_root=plists,
                launcher_root=launchers,
                evidence_root=evidence,
                launchctl_reader=self.reader,
                intentionally_disabled={"daily"},
                now=datetime(2026, 8, 5, 12, 5, tzinfo=timezone.utc),
            )
            self.assertEqual(report["status"], "healthy")
            self.assertEqual(report["lanes"]["daily"]["state"], "intentionally_disabled")
            self.assertEqual(report["lanes"]["inbox"]["interval_seconds"], 300)

    def test_interval_drift_and_nonzero_exit_are_reported_unhealthy(self):
        with tempfile.TemporaryDirectory() as directory:
            plists, launchers, evidence = self.setup_runtime(Path(directory))
            path = plists / "ai.anicca.job-search-inbox.plist"
            value = plistlib.loads(path.read_bytes())
            value["StartInterval"] = 900
            path.write_bytes(plistlib.dumps(value))

            def reader(label):
                if label.endswith("daily"):
                    return None
                exit_code = 78 if label.endswith("learning") else 0
                return f"state = not running\nruns = 1\nlast exit code = {exit_code}\n"

            report = schedule_health(
                plist_root=plists,
                launcher_root=launchers,
                evidence_root=evidence,
                launchctl_reader=reader,
                intentionally_disabled={"daily"},
                now=datetime(2026, 8, 5, 12, 5, tzinfo=timezone.utc),
            )
            self.assertEqual(report["status"], "unhealthy")
            self.assertIn("interval_mismatch", report["lanes"]["inbox"]["reasons"])
            self.assertIn("last_exit_nonzero", report["lanes"]["learning"]["reasons"])


if __name__ == "__main__":
    unittest.main()
