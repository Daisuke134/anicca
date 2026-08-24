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
        resume = path.with_name("resume.pdf")
        resume.write_bytes(b"%PDF-1.4\nportable resume\n")
        path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "candidate": {"name": "Scheduler Candidate"},
                    "materials": {
                        "resumes": {"engineering": str(resume)}
                    },
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
        fake_openclaw = root / "fake-openclaw"
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
    program = sys.stdin.read()
    sys.argv = sys.argv[1:]
    exec(compile(program, "<stdin>", "exec"), {"__name__": "__main__"})
    raise SystemExit(0)
if sys.argv[1:3] == ["-m", "job_search_loop.summary"]:
    from job_search_loop.summary import main
    raise SystemExit(main(sys.argv[3:]))
if sys.argv[1:3] and sys.argv[1] == "-m" and "--output" in sys.argv:
    module = sys.argv[2]
    output = pathlib.Path(sys.argv[sys.argv.index("--output") + 1])
    output.parent.mkdir(parents=True, exist_ok=True)
    value = {}
    if module == "job_search_loop.ashby_fast_path":
        value = {"status": "no_work", "processed": [], "excluded": []}
    elif module == "job_search_loop.ashby_discovery":
        value = {"status": "completed", "discovered": []}
    elif module == "job_search_loop.browser_owner":
        value = {"status": "ready", "endpoint": "http://127.0.0.1:9222"}
    output.write_text(json.dumps(value) + "\\n", encoding="utf-8")
    raise SystemExit(0)
if sys.argv[1:3] == ["-m", "job_search_loop.browser_agent.orchestrator"]:
    raise SystemExit(%d)
if sys.argv[1:2] and sys.argv[1].endswith("agent_runner.py"):
    evidence = pathlib.Path(sys.argv[sys.argv.index("--evidence-dir") + 1])
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "summary.json").write_text(
        json.dumps({"status": "failed"}) + "\\n",
        encoding="utf-8",
    )
    raise SystemExit(%d)
raise SystemExit(0)
"""
            % (runner_rc, runner_rc),
            encoding="utf-8",
        )
        fake_python.chmod(0o700)
        fake_openclaw.write_text(
            "#!/bin/sh\nprintf '%s\\n' '{\"messageId\":\"test-message\"}'\n",
            encoding="utf-8",
        )
        fake_openclaw.chmod(0o700)
        fake_disk_guard = root / "disk-guard.py"
        fake_disk_guard.write_text("raise SystemExit(0)\n", encoding="utf-8")
        fake_disk_guard.chmod(0o600)
        env = {
            **os.environ,
            "HOME": str(root / "home"),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "JOB_SEARCH_STATE_ROOT": str(root / "state"),
            "JOB_SEARCH_PYTHON": str(fake_python),
            "JOB_SEARCH_OPENCLAW": str(fake_openclaw),
            "JOB_SEARCH_TELEGRAM_MEDIA": str(root / "media"),
            "JOB_SEARCH_DISK_GUARD": str(fake_disk_guard),
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

    def test_daily_runs_even_when_prior_slots_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, calls = self._run_daily_with_fake_python(root, 2, 99)

            self.assertEqual(result.returncode, 99, result.stderr)
            encoded = json.dumps(calls)
            self.assertIn("job_search_loop.browser_owner", encoded)
            self.assertIn("job_search_loop.browser_agent.orchestrator", encoded)
            self.assertNotIn("job_search_loop.workday_fast_path", encoded)
            self.assertNotIn("job_search_loop.ashby_fast_path", encoded)
            self.assertEqual(
                1,
                sum(
                    call[:2] == ["-m", "job_search_loop.browser_agent.orchestrator"]
                    for call in calls
                ),
            )

    def test_daily_emits_one_direct_final_wake_report_on_runner_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, calls = self._run_daily_with_fake_python(root, 0, 99)

            self.assertEqual(result.returncode, 99, result.stderr)
            wake_reports = [
                call
                for call in calls
                if call[:3]
                == ["-m", "job_search_loop.application_reporting", "wake"]
            ]
            self.assertEqual(len(wake_reports), 1)

    def test_daily_has_no_openclaw_telegram_transport(self):
        source = (APP_ROOT / "scripts" / "run-daily.sh").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("$JOB_SEARCH_OPENCLAW\" message send", source)
        self.assertNotIn("pre-model-report.json", source)

    def test_daily_success_refreshes_durable_summary_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, calls = self._run_daily_with_fake_python(root, 0, 0)

            self.assertEqual(result.returncode, 0, result.stderr)
            projection = root / "state" / "summary.v2.json"
            compatibility = root / "state" / "summary.v1.json"
            self.assertTrue(projection.is_file())
            self.assertTrue(compatibility.is_file())
            self.assertEqual(
                json.loads(projection.read_text(encoding="utf-8"))["version"],
                2,
            )
            self.assertEqual(
                json.loads(compatibility.read_text(encoding="utf-8"))["version"],
                1,
            )
            self.assertEqual(
                json.loads(projection.read_text(encoding="utf-8"))["day"],
                __import__("datetime").datetime.now(
                    __import__("zoneinfo").ZoneInfo("Asia/Tokyo")
                ).date().isoformat(),
            )
            self.assertIn("job_search_loop.summary", json.dumps(calls))
            self.assertIn("--compat-output", json.dumps(calls))

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

    def test_runner_codex_home_is_job_search_owned(self):
        config_path = REPO_ROOT / "runtime" / "agent-runner" / "config.json"
        provider = json.loads(config_path.read_text(encoding="utf-8"))["providers"][
            "codex"
        ]

        self.assertEqual(
            provider["automation_home"],
            "~/.local/state/anicca/job-search/codex-runner",
        )
        self.assertEqual(
            provider["auth_file"],
            "~/.config/anicca/job-search/codex-auth.json",
        )

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
            self.assertEqual(daily["StartInterval"], 1800)
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
            self.assertIn("OnBootSec=30min", daily_timer)
            self.assertIn("OnUnitActiveSec=30min", daily_timer)
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
