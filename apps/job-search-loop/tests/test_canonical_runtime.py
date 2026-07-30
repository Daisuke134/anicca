import json
import os
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]


class CanonicalRuntimeTests(unittest.TestCase):
    @staticmethod
    def _valid_portable_profile(path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "candidate": {"name": "Scheduler Candidate"},
                    "facts": [
                        {
                            "id": "fact-1",
                            "claim": "Verified portable fact.",
                            "evidence": "Synthetic test source",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _fake_authenticated_codex(directory: Path) -> Path:
        executable = directory / "codex"
        executable.write_text(
            "#!/bin/sh\n"
            'test "$1" = "login" && test "$2" = "status" && exit 0\n'
            "exit 1\n",
            encoding="utf-8",
        )
        executable.chmod(0o700)
        return executable

    def _run_daily_with_fake_python(self, root: Path, slot_count: int, runner_rc: int):
        fake_python = root / "fake-python"
        calls = root / "python-calls.jsonl"
        fake_python.write_text(
            """#!/usr/bin/env python3
import json
import pathlib
import sys

calls = pathlib.Path(__file__).with_name("python-calls.jsonl")
with calls.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1:2] == ["-"]:
    print(%d)
    raise SystemExit(0)
if sys.argv[1:3] == ["-m", "job_search_loop.summary"]:
    from job_search_loop.summary import main
    raise SystemExit(main(sys.argv[3:]))
if sys.argv[1:2] and sys.argv[1].endswith("agent_runner.py"):
    evidence = pathlib.Path(sys.argv[sys.argv.index("--evidence-dir") + 1])
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "summary.json").write_text(
        json.dumps({"status": "budget_blocked"}) + "\\n",
        encoding="utf-8",
    )
    raise SystemExit(%d)
raise SystemExit(0)
"""
            % (slot_count, runner_rc),
            encoding="utf-8",
        )
        fake_python.chmod(0o700)
        env = {
            **os.environ,
            "HOME": str(root / "home"),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "JOB_SEARCH_STATE_ROOT": str(root / "state"),
            "JOB_SEARCH_PYTHON": str(fake_python),
            "JOB_SEARCH_TELEGRAM_MEDIA": str(root / "media"),
        }
        result = subprocess.run(
            ["/bin/zsh", str(APP_ROOT / "scripts" / "run-daily.sh")],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        recorded = [
            json.loads(line)
            for line in calls.read_text(encoding="utf-8").splitlines()
        ]
        return result, recorded

    def test_daily_full_quota_exits_without_browser_or_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, calls = self._run_daily_with_fake_python(root, 2, 99)

            self.assertEqual(result.returncode, 0, result.stderr)
            encoded = json.dumps(calls)
            self.assertNotIn("job_search_loop.browser_owner", encoded)
            self.assertNotIn("agent_runner.py", encoded)
            summaries = list((root / "state" / "evidence").glob("daily-*/summary.json"))
            self.assertEqual(len(summaries), 1)
            self.assertEqual(
                json.loads(summaries[0].read_text(encoding="utf-8"))["status"],
                "daily_quota_reached",
            )
            projection = root / "state" / "summary.v1.json"
            self.assertTrue(projection.is_file())
            self.assertEqual(projection.stat().st_mode & 0o777, 0o600)

    def test_daily_budget_block_is_an_honest_completed_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, calls = self._run_daily_with_fake_python(root, 0, 75)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("job_search_loop.browser_owner", json.dumps(calls))
            self.assertIn("agent_runner.py", json.dumps(calls))
            summaries = list((root / "state" / "evidence").glob("daily-*/summary.json"))
            self.assertEqual(len(summaries), 1)
            self.assertEqual(
                json.loads(summaries[0].read_text(encoding="utf-8"))["status"],
                "budget_blocked",
            )
            projection = root / "state" / "summary.v1.json"
            self.assertTrue(projection.is_file())
            self.assertEqual(projection.stat().st_mode & 0o777, 0o600)

    def test_daily_success_refreshes_durable_summary_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, calls = self._run_daily_with_fake_python(root, 0, 0)

            self.assertEqual(result.returncode, 0, result.stderr)
            projection = root / "state" / "summary.v1.json"
            self.assertTrue(projection.is_file())
            self.assertEqual(
                json.loads(projection.read_text(encoding="utf-8"))["day"],
                __import__("datetime").datetime.now(
                    __import__("zoneinfo").ZoneInfo("Asia/Tokyo")
                ).date().isoformat(),
            )
            self.assertIn("job_search_loop.summary", json.dumps(calls))

    def test_runner_config_is_job_scoped_and_contains_no_private_identity(self):
        config_path = REPO_ROOT / "runtime" / "agent-runner" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertTrue({"codex", "claude-direct"}.issubset(config["providers"]))
        self.assertTrue(
            {
                "composition-agent",
                "repeatable-agent",
                "browser-lane-agent",
                "high-value-agent",
            }.issubset(config["task_classes"])
        )
        encoded = json.dumps(config)
        self.assertNotIn("@", encoded)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("gig-", encoded)

    def test_private_env_loader_reads_only_the_requested_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            private_root = Path(tmp)
            env_file = private_root / ".env"
            marker = private_root / "must-not-exist"
            env_file.write_text(
                "\n".join(
                    [
                        "FIRECRAWL_API_KEY='agent key'",
                        f"UNRELATED=$(touch {marker})",
                    ]
                ),
                encoding="utf-8",
            )
            env = {
                **os.environ,
                "HOME": str(private_root / "home"),
                "JOB_SEARCH_PRIVATE_ENV": str(env_file),
            }
            env.pop("FIRECRAWL_API_KEY", None)
            result = subprocess.run(
                [
                    "/bin/zsh",
                    "-c",
                    (
                        f'source "{APP_ROOT / "scripts" / "runtime-paths.sh"}"; '
                        f'source "{APP_ROOT / "scripts" / "private-env.sh"}"; '
                        "job_search_load_private_env FIRECRAWL_API_KEY; "
                        "printf '%s' \"$FIRECRAWL_API_KEY\""
                    ),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "agent key")
            self.assertFalse(marker.exists())

    def test_runtime_paths_resolve_inside_life_manager_and_xdg(self):
        with tempfile.TemporaryDirectory() as tmp:
            private_root = Path(tmp)
            env = {
                **os.environ,
                "HOME": str(private_root / "home"),
                "XDG_CONFIG_HOME": str(private_root / "config"),
                "XDG_STATE_HOME": str(private_root / "state"),
                "XDG_DATA_HOME": str(private_root / "data"),
            }
            result = subprocess.run(
                [
                    "/bin/zsh",
                    "-c",
                    (
                        f'source "{APP_ROOT / "scripts" / "runtime-paths.sh"}"; '
                        "printf '%s\\n' "
                        '"$JOB_SEARCH_APP_ROOT" "$JOB_SEARCH_REPO_ROOT" '
                        '"$JOB_SEARCH_RUNNER" "$JOB_SEARCH_STATE_ROOT" '
                        '"$JOB_SEARCH_PROFILE" "$JOB_SEARCH_FRAMEWORK_ROOT"'
                    ),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            paths = result.stdout.splitlines()
            self.assertEqual(paths[0], str(APP_ROOT))
            self.assertEqual(paths[1], str(REPO_ROOT))
            self.assertEqual(
                paths[2], str(REPO_ROOT / "runtime" / "agent-runner" / "agent_runner.py")
            )
            self.assertEqual(
                paths[3], str(private_root / "state" / "anicca" / "job-search")
            )
            self.assertEqual(
                paths[4],
                str(private_root / "config" / "anicca" / "job-search" / "profile.json"),
            )
            self.assertEqual(
                paths[5],
                str(private_root / "data" / "anicca" / "job-search" / "framework"),
            )
            self.assertNotIn("anicca-job-search-loop", result.stdout)
            self.assertNotIn("profitable-claude", result.stdout)

    def test_installer_renders_canonical_plists_without_loading_launchd(self):
        with tempfile.TemporaryDirectory() as tmp:
            private_root = Path(tmp)
            agents = private_root / "LaunchAgents"
            env = {
                **os.environ,
                "HOME": str(private_root / "home"),
                "XDG_CONFIG_HOME": str(private_root / "config"),
                "XDG_STATE_HOME": str(private_root / "state"),
                "XDG_DATA_HOME": str(private_root / "data"),
                "JOB_SEARCH_LAUNCH_AGENT_DIR": str(agents),
                "JOB_SEARCH_SKIP_BOOTSTRAP": "1",
                "JOB_SEARCH_SKIP_LAUNCHCTL": "1",
            }
            fake_plutil = private_root / "plutil"
            fake_plutil.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_plutil.chmod(0o700)
            env["JOB_SEARCH_PLUTIL"] = str(fake_plutil)
            result = subprocess.run(
                ["/bin/zsh", str(APP_ROOT / "scripts" / "install-launchd.sh")],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            daily = plistlib.loads(
                (agents / "ai.anicca.job-search-daily.plist").read_bytes()
            )
            inbox = plistlib.loads(
                (agents / "ai.anicca.job-search-inbox.plist").read_bytes()
            )
            learning = plistlib.loads(
                (agents / "ai.anicca.job-search-learning.plist").read_bytes()
            )
            self.assertEqual(
                daily["ProgramArguments"][0],
                str(APP_ROOT / "scripts" / "run-daily.sh"),
            )
            self.assertEqual(
                inbox["ProgramArguments"][0],
                str(APP_ROOT / "scripts" / "run-inbox.sh"),
            )
            self.assertEqual(
                learning["ProgramArguments"][0],
                str(APP_ROOT / "scripts" / "run-learning.sh"),
            )
            self.assertEqual(daily["StartCalendarInterval"], {"Hour": 8, "Minute": 30})
            self.assertEqual(inbox["StartInterval"], 900)
            self.assertEqual(
                learning["StartCalendarInterval"],
                {"Weekday": 1, "Hour": 9, "Minute": 15},
            )
            self.assertTrue(
                daily["StandardOutPath"].startswith(
                    str(private_root / "state" / "anicca" / "job-search")
                )
            )
            self.assertNotIn("anicca-job-search-loop", result.stdout)
            self.assertNotIn("profitable-claude", result.stdout)

    def test_systemd_installer_renders_private_user_units_and_enables_timers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls = root / "systemctl-calls.jsonl"
            fake_systemctl = root / "systemctl"
            fake_systemctl.write_text(
                "#!/bin/sh\n"
                f"printf '%s\\n' \"$*\" >> {calls}\n",
                encoding="utf-8",
            )
            fake_systemctl.chmod(0o700)
            env = {
                **os.environ,
                "HOME": str(root / "home"),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_STATE_HOME": str(root / "state"),
                "XDG_DATA_HOME": str(root / "data"),
                "JOB_SEARCH_SYSTEMCTL": str(fake_systemctl),
                "JOB_SEARCH_SKIP_SYSTEMD_ANALYZE": "1",
            }

            result = subprocess.run(
                ["/bin/zsh", str(APP_ROOT / "scripts" / "install-systemd.sh")],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            unit_dir = root / "config" / "systemd" / "user"
            daily_service = (
                unit_dir / "ai.anicca.job-search-daily.service"
            ).read_text(encoding="utf-8")
            daily_timer = (
                unit_dir / "ai.anicca.job-search-daily.timer"
            ).read_text(encoding="utf-8")
            inbox_timer = (
                unit_dir / "ai.anicca.job-search-inbox.timer"
            ).read_text(encoding="utf-8")
            learning_service = (
                unit_dir / "ai.anicca.job-search-learning.service"
            ).read_text(encoding="utf-8")
            learning_timer = (
                unit_dir / "ai.anicca.job-search-learning.timer"
            ).read_text(encoding="utf-8")
            self.assertIn(
                str(APP_ROOT / "scripts" / "run-daily.sh"), daily_service
            )
            self.assertIn(str(REPO_ROOT), daily_service)
            self.assertIn("OnCalendar=*-*-* 08:30:00 Asia/Tokyo", daily_timer)
            self.assertIn("Persistent=true", daily_timer)
            self.assertIn("OnUnitActiveSec=15min", inbox_timer)
            self.assertIn(
                str(APP_ROOT / "scripts" / "run-learning.sh"), learning_service
            )
            self.assertIn("OnCalendar=Sun *-*-* 09:15:00 Asia/Tokyo", learning_timer)
            self.assertIn("Persistent=true", learning_timer)
            encoded = "\n".join(
                path.read_text(encoding="utf-8") for path in unit_dir.iterdir()
            )
            self.assertNotIn("__JOB_SEARCH_", encoded)
            self.assertNotIn("profitable-claude", encoded)
            self.assertNotIn("anicca-job-search-loop", encoded)
            recorded = calls.read_text(encoding="utf-8").splitlines()
            self.assertEqual(recorded[0], "--user daemon-reload")
            self.assertEqual(
                recorded[1],
                "--user enable --now ai.anicca.job-search-daily.timer "
                "ai.anicca.job-search-inbox.timer "
                "ai.anicca.job-search-learning.timer",
            )

    def test_portable_installer_dispatches_to_launchd_with_fake_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "profile.json"
            self._valid_portable_profile(source)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            self._fake_authenticated_codex(bin_dir)
            calls = root / "launchctl-calls.jsonl"
            launchctl = bin_dir / "launchctl"
            launchctl.write_text(
                "#!/bin/sh\n"
                f"printf '%s\\n' \"$*\" >> {calls}\n",
                encoding="utf-8",
            )
            launchctl.chmod(0o700)
            plutil = bin_dir / "plutil"
            plutil.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            plutil.chmod(0o700)
            env = {
                **os.environ,
                "HOME": str(root / "home"),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_STATE_HOME": str(root / "state"),
                "XDG_DATA_HOME": str(root / "data"),
                "PATH": f"{bin_dir}:/usr/bin:/bin",
                "PYTHONPATH": str(APP_ROOT),
                "JOB_SEARCH_PLATFORM": "Darwin",
                "JOB_SEARCH_SKIP_BOOTSTRAP": "1",
                "JOB_SEARCH_LAUNCHCTL": str(launchctl),
                "JOB_SEARCH_PLUTIL": str(plutil),
                "JOB_SEARCH_LAUNCH_AGENT_DIR": str(root / "LaunchAgents"),
            }

            result = subprocess.run(
                [
                    "/bin/zsh",
                    str(APP_ROOT / "scripts" / "install-local.sh"),
                    "--profile",
                    str(source),
                    "--provider",
                    "codex",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            recorded = calls.read_text(encoding="utf-8")
            self.assertIn("bootstrap gui/", recorded)
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt["scheduler"], "launchd")


if __name__ == "__main__":
    unittest.main()
