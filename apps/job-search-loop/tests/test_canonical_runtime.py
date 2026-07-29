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
    def test_runner_config_is_job_scoped_and_contains_no_private_identity(self):
        config_path = REPO_ROOT / "runtime" / "agent-runner" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(set(config["providers"]), {"codex", "claude-direct"})
        self.assertEqual(
            set(config["task_classes"]),
            {
                "composition-agent",
                "repeatable-agent",
                "browser-lane-agent",
                "high-value-agent",
            },
        )
        self.assertNotIn("candidate_profiles", config)
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
            self.assertEqual(
                daily["ProgramArguments"][0],
                str(APP_ROOT / "scripts" / "run-daily.sh"),
            )
            self.assertEqual(
                inbox["ProgramArguments"][0],
                str(APP_ROOT / "scripts" / "run-inbox.sh"),
            )
            self.assertEqual(daily["StartCalendarInterval"], {"Hour": 8, "Minute": 30})
            self.assertEqual(inbox["StartInterval"], 900)
            self.assertTrue(
                daily["StandardOutPath"].startswith(
                    str(private_root / "state" / "anicca" / "job-search")
                )
            )
            self.assertNotIn("anicca-job-search-loop", result.stdout)
            self.assertNotIn("profitable-claude", result.stdout)


if __name__ == "__main__":
    unittest.main()
