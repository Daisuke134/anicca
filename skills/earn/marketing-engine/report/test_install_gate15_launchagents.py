#!/usr/bin/env python3
"""Contract tests for the Gate 15 owner-report LaunchAgents."""

from __future__ import annotations

import json
import io
import pathlib
import plistlib
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

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

    def test_event_job_runs_serialized_truth_pipeline_hourly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            home = pathlib.Path(tmp) / "home"
            job = _plist(installer.build_plists(root, home)[LABELS["events"]])

        self.assertEqual(job["Label"], LABELS["events"])
        self.assertEqual(job["StartInterval"], 3600)
        self.assertNotIn("StartCalendarInterval", job)
        self.assertEqual(job["WorkingDirectory"], str(root))
        command = " ".join(job["ProgramArguments"])
        pipeline = root / "skills/earn/marketing-engine/report/truth_pipeline.py"
        self.assertEqual(job["ProgramArguments"][1], str(pipeline))
        self.assertIn(str(pipeline), command)
        self.assertNotIn("/bin/sh", command)
        self.assertNotIn("apify", command.lower())

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

            output = pathlib.Path(tmp) / "not-created" / "plan.json"
            captured = io.StringIO()
            with redirect_stdout(captured):
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
            self.assertFalse(output.exists())
            self.assertFalse(output.parent.exists())
            self.assertFalse((home / "Library").exists())
            self.assertEqual(
                sorted(path.name for path in launch_dir.iterdir()),
                sorted(
                    [
                        f"{LABELS['daily']}.plist",
                        f"{LABELS['events']}.plist",
                    ]
                ),
            )
            plan = json.loads(captured.getvalue())
            self.assertEqual(
                captured.getvalue(),
                json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            )
            self.assertEqual(plan["action"], "plan")
            self.assertEqual(
                {row["label"]: row["status"] for row in plan["rows"]},
                {
                    LABELS["events"]: "update",
                    LABELS["daily"]: "no-change",
                    LABELS["weekly"]: "create",
                },
            )


def _launchctl_success(stdout: str = "") -> subprocess.CompletedProcess[str]:
    """Build a successful mocked launchctl result without invoking launchctl."""

    return subprocess.CompletedProcess(
        args=["launchctl"], returncode=0, stdout=stdout, stderr=""
    )


def _matching_readback(root: pathlib.Path, home: pathlib.Path, label: str) -> str:
    """Literal launchctl-print-shaped output for an owned schedule."""

    payload = installer.build_plists(root, home)[label]
    job = plistlib.loads(payload)
    arguments = "\n".join(f"        {argument}" for argument in job["ProgramArguments"])
    common = f"""gui/501/{label} = {{
    label = {job['Label']}
    program = {job['ProgramArguments'][0]}
    program arguments = {{
{arguments}
    }}
    working directory = {job['WorkingDirectory']}
"""
    if "StartInterval" in job:
        return common + f"    run interval = {job['StartInterval']} seconds\n}}\n"

    calendar = job["StartCalendarInterval"]
    fields = [f'        "Minute" => {calendar["Minute"]};', f'        "Hour" => {calendar["Hour"]};']
    if "Weekday" in calendar:
        fields.append(f'        "Weekday" => {calendar["Weekday"]};')
    return common + """    event triggers = {
        descriptor = {
""" + "\n".join(fields) + """
        };
    };
}
"""


class ApplyTests(unittest.TestCase):
    def _mock_launchctl(self, root: pathlib.Path, home: pathlib.Path, calls: list[list[str]]):
        def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(list(arguments))
            if arguments[0] == "print":
                label = arguments[1].rsplit("/", 1)[-1]
                return _launchctl_success(_matching_readback(root, home, label))
            return _launchctl_success()

        return run

    def test_real_launchctl_print_shapes_match_each_owned_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            home = pathlib.Path(tmp) / "home"
            for label, payload in installer.build_plists(root, home).items():
                with self.subTest(label=label):
                    self.assertTrue(
                        installer._readback_matches(_matching_readback(root, home, label), payload, label)
                    )

    def test_apply_writes_atomically_and_controls_only_three_owner_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "repo"
            home = pathlib.Path(tmp) / "home"
            launch_dir = pathlib.Path(tmp) / "LaunchAgents"
            calls: list[list[str]] = []
            expected = installer.build_plists(root, home)
            with mock.patch.object(
                installer, "_run_launchctl", side_effect=self._mock_launchctl(root, home, calls)
            ), mock.patch.object(
                installer, "_atomic_write", wraps=installer._atomic_write
            ) as atomic_write:
                rows = installer.apply(root, home, launch_dir)

            self.assertEqual([row["label"] for row in rows], list(LABELS.values()))
            self.assertEqual(atomic_write.call_count, 3)
            self.assertEqual(
                {
                    path.name.removesuffix(".plist")
                    for path in launch_dir.iterdir()
                    if path.is_file()
                },
                set(LABELS.values()),
            )
            for label, payload in expected.items():
                self.assertEqual((launch_dir / f"{label}.plist").read_bytes(), payload)

            calls_text = [" ".join(arguments) for arguments in calls]
            for label in LABELS.values():
                self.assertTrue(any("bootstrap" in call and label in call for call in calls_text))
                self.assertTrue(any("kickstart" in call and label in call for call in calls_text))
                self.assertTrue(any("print" in call and label in call for call in calls_text))
            self.assertTrue(all("legacy" not in call and "marketing-mine" not in call for call in calls_text))
            self.assertTrue(all(row["loaded_readback"] for row in rows))

    def test_apply_fails_when_readback_is_empty_or_mismatched(self):
        for readback in ("", "Label = ai.anicca.legacy\nowner_report_cli.py\nStartInterval = 900"):
            with self.subTest(readback=readback), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp) / "repo"
                home = pathlib.Path(tmp) / "home"
                launch_dir = pathlib.Path(tmp) / "LaunchAgents"

                def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
                    if arguments[0] == "print":
                        return _launchctl_success(readback)
                    return _launchctl_success()

                with mock.patch.object(installer, "_run_launchctl", side_effect=run):
                    with self.assertRaisesRegex(RuntimeError, "readback mismatch"):
                        installer.apply(root, home, launch_dir)

    def _assert_schedule_readback_rejected(
        self,
        root: pathlib.Path,
        home: pathlib.Path,
        launch_dir: pathlib.Path,
        label: str,
        bad_readback: str,
    ) -> None:
        def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
            if arguments[0] == "print":
                printed_label = arguments[1].rsplit("/", 1)[-1]
                if printed_label == label:
                    return _launchctl_success(bad_readback)
                return _launchctl_success(_matching_readback(root, home, printed_label))
            return _launchctl_success()

        with mock.patch.object(installer, "_run_launchctl", side_effect=run):
            with self.assertRaisesRegex(RuntimeError, "readback mismatch"):
                installer.apply(root, home, launch_dir)

    def test_event_interval_wrong_value_is_rejected_even_if_3600_appears_elsewhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, home, launch_dir = (pathlib.Path(tmp) / name for name in ("repo", "home", "LaunchAgents"))
            label = LABELS["events"]
            readback = _matching_readback(root, home, label).replace(
                "run interval = 3600 seconds", "run interval = 120 seconds"
            ) + "\nUnrelated = 3600"
            self._assert_schedule_readback_rejected(root, home, launch_dir, label, readback)

    def test_daily_hour_wrong_value_is_rejected_even_if_22_appears_elsewhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, home, launch_dir = (pathlib.Path(tmp) / name for name in ("repo", "home", "LaunchAgents"))
            label = LABELS["daily"]
            readback = _matching_readback(root, home, label).replace(
                '"Hour" => 22', '"Hour" => 23'
            ) + "\nUnrelated = 22"
            self._assert_schedule_readback_rejected(root, home, launch_dir, label, readback)

    def test_daily_minute_wrong_value_is_rejected_even_if_zero_appears_elsewhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, home, launch_dir = (pathlib.Path(tmp) / name for name in ("repo", "home", "LaunchAgents"))
            label = LABELS["daily"]
            readback = _matching_readback(root, home, label).replace(
                '"Minute" => 0', '"Minute" => 1'
            ) + "\nUnrelated = 0"
            self._assert_schedule_readback_rejected(root, home, launch_dir, label, readback)

    def test_daily_schedule_cannot_borrow_values_from_another_descriptor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, home, launch_dir = (pathlib.Path(tmp) / name for name in ("repo", "home", "LaunchAgents"))
            label = LABELS["daily"]
            readback = _matching_readback(root, home, label).replace(
                '"Hour" => 22', '"Hour" => 23'
            ).replace(
                "    event triggers = {\n        descriptor = {",
                """    event triggers = {
        unrelated = {
            descriptor = {
                "Minute" => 0;
                "Hour" => 22;
            };
        };
        descriptor = {""",
            )
            self._assert_schedule_readback_rejected(root, home, launch_dir, label, readback)

    def test_weekly_weekday_wrong_value_is_rejected_even_if_zero_appears_elsewhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, home, launch_dir = (pathlib.Path(tmp) / name for name in ("repo", "home", "LaunchAgents"))
            label = LABELS["weekly"]
            readback = _matching_readback(root, home, label).replace(
                '"Weekday" => 0', '"Weekday" => 3'
            ) + "\nUnrelated = 0"
            self._assert_schedule_readback_rejected(root, home, launch_dir, label, readback)

    def test_weekly_hour_wrong_value_is_rejected_even_if_21_appears_elsewhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, home, launch_dir = (pathlib.Path(tmp) / name for name in ("repo", "home", "LaunchAgents"))
            label = LABELS["weekly"]
            readback = _matching_readback(root, home, label).replace(
                '"Hour" => 21', '"Hour" => 20'
            ) + "\nUnrelated = 21"
            self._assert_schedule_readback_rejected(root, home, launch_dir, label, readback)

    def test_weekly_minute_wrong_value_is_rejected_even_if_zero_appears_elsewhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, home, launch_dir = (pathlib.Path(tmp) / name for name in ("repo", "home", "LaunchAgents"))
            label = LABELS["weekly"]
            readback = _matching_readback(root, home, label).replace(
                '"Minute" => 0', '"Minute" => 1'
            ) + "\nUnrelated = 0"
            self._assert_schedule_readback_rejected(root, home, launch_dir, label, readback)


if __name__ == "__main__":
    unittest.main()
