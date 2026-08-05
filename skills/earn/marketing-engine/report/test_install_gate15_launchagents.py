#!/usr/bin/env python3
"""Contract tests for the Gate 15 owner-report LaunchAgents."""

from __future__ import annotations

import json
import pathlib
import plistlib
import tempfile
import unittest

import install_gate15_launchagents as installer


LABELS = {
    "events": "ai.anicca.marketing-owner-events",
    "daily": "ai.anicca.marketing-owner-daily",
    "weekly": "ai.anicca.marketing-owner-weekly",
}
FORBIDDEN = ("openclaw", "daily_report.py", "weekly_review.py", "notify_posts.py")


def _plist(payload: bytes) -> dict:
    return plistlib.loads(payload)


class BuildPlistsTests(unittest.TestCase):
    def test_returns_exactly_three_owner_report_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            home = pathlib.Path(tmp) / "home"
            plists = installer.build_plists(root, home)

        self.assertEqual(set(plists), set(LABELS.values()))
        self.assertEqual(len(plists), 3)
        self.assertEqual(
            {plistlib.loads(payload)["Label"] for payload in plists.values()},
            set(LABELS.values()),
        )

    def test_event_job_runs_all_four_sweeps_every_900_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            home = pathlib.Path(tmp) / "home"
            job = _plist(installer.build_plists(root, home)[LABELS["events"]])

        self.assertEqual(job["Label"], LABELS["events"])
        self.assertEqual(job["StartInterval"], 900)
        self.assertNotIn("StartCalendarInterval", job)
        self.assertEqual(job["WorkingDirectory"], str(root))
        command = " ".join(job["ProgramArguments"])
        cli = root / "skills/earn/marketing-engine/report/owner_report_cli.py"
        state = root / "skills/earn/marketing-engine/state"
        self.assertIn(str(cli), command)
        self.assertIn(str(state), command)
        for kind in ("action", "checkpoint", "incident", "experiment"):
            self.assertIn(f"--kind {kind}", command)

    def test_daily_and_weekly_calendar_intervals_and_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            home = pathlib.Path(tmp) / "home"
            plists = installer.build_plists(root, home)
            daily = _plist(plists[LABELS["daily"]])
            weekly = _plist(plists[LABELS["weekly"]])

        self.assertEqual(
            daily["StartCalendarInterval"], {"Hour": 22, "Minute": 0}
        )
        self.assertEqual(
            weekly["StartCalendarInterval"], {"Weekday": 0, "Hour": 21, "Minute": 0}
        )
        self.assertNotIn("StartInterval", daily)
        self.assertNotIn("StartInterval", weekly)
        daily_args = daily["ProgramArguments"]
        weekly_args = weekly["ProgramArguments"]
        self.assertEqual(daily_args[2:5], ["sweep", "--kind", "product_daily"])
        self.assertEqual(weekly_args[2:5], ["sweep", "--kind", "portfolio_weekly"])
        self.assertIn("--state-root", daily_args)
        self.assertIn("--state-root", weekly_args)

    def test_commands_use_canonical_paths_and_writable_non_openclaw_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            home = pathlib.Path(tmp) / "home"
            home.mkdir()
            plists = installer.build_plists(root, home)

        for payload in plists.values():
            job = _plist(payload)
            self.assertEqual(job["WorkingDirectory"], str(root))
            self.assertTrue(pathlib.Path(job["StandardOutPath"]).is_absolute())
            self.assertTrue(pathlib.Path(job["StandardErrorPath"]).is_absolute())
            logs = (job["StandardOutPath"] + "\n" + job["StandardErrorPath"]).lower()
            for forbidden in FORBIDDEN:
                self.assertNotIn(forbidden, logs)

    def test_generated_plists_never_reference_legacy_reporters_or_openclaw(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            home = pathlib.Path(tmp) / "home"
            payloads = installer.build_plists(root, home)

        for payload in payloads.values():
            rendered = payload.decode("utf-8").lower()
            for forbidden in FORBIDDEN:
                self.assertNotIn(forbidden, rendered)


class PlanTests(unittest.TestCase):
    def test_plan_reports_create_update_no_change_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            home = pathlib.Path(tmp) / "home"
            launch_dir = pathlib.Path(tmp) / "LaunchAgents"
            launch_dir.mkdir()
            targets = installer.build_plists(root, home)

            no_change = launch_dir / f"{LABELS['daily']}.plist"
            no_change.write_bytes(targets[LABELS["daily"]])
            update = launch_dir / f"{LABELS['events']}.plist"
            old = b"legacy bytes that must remain untouched"
            update.write_bytes(old)

            output = pathlib.Path(tmp) / "plan.json"
            rc = installer.main(
                [
                    "--plan",
                    "--repo-root",
                    str(root),
                    "--home",
                    str(home),
                    "--launch-dir",
                    str(launch_dir),
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertEqual(update.read_bytes(), old)
            self.assertEqual(
                sorted(path.name for path in launch_dir.iterdir()),
                sorted(
                    [
                        f"{LABELS['daily']}.plist",
                        f"{LABELS['events']}.plist",
                    ]
                ),
            )
            plan = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(plan["action"], "plan")
            self.assertEqual(
                {row["label"]: row["status"] for row in plan["rows"]},
                {
                    LABELS["events"]: "update",
                    LABELS["daily"]: "no-change",
                    LABELS["weekly"]: "create",
                },
            )


if __name__ == "__main__":
    unittest.main()
