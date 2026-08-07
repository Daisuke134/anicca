import plistlib
import unittest
from pathlib import Path


class LaunchdTests(unittest.TestCase):
    def test_plists_have_separate_bounded_schedules(self):
        root = Path(__file__).parents[1] / "launchd"
        daily = plistlib.loads((root / "ai.anicca.job-search-daily.plist").read_bytes())
        inbox = plistlib.loads((root / "ai.anicca.job-search-inbox.plist").read_bytes())
        learning = plistlib.loads(
            (root / "ai.anicca.job-search-learning.plist").read_bytes()
        )
        self.assertTrue(daily["RunAtLoad"])
        self.assertEqual(daily["StartInterval"], 3600)
        self.assertNotIn("StartCalendarInterval", daily)
        self.assertEqual(inbox["StartInterval"], 300)
        self.assertTrue(learning["RunAtLoad"])
        self.assertEqual(
            learning["StartCalendarInterval"],
            {"Weekday": 1, "Hour": 9, "Minute": 15},
        )
        self.assertNotEqual(daily["Label"], inbox["Label"])
        self.assertNotEqual(daily["ProgramArguments"][0], inbox["ProgramArguments"][0])
        self.assertNotEqual(
            learning["ProgramArguments"][0], daily["ProgramArguments"][0]
        )

    def test_browser_supervisor_uses_a_dedicated_dynamic_loopback_profile(self):
        root = Path(__file__).parents[1]
        browser = plistlib.loads(
            (root / "launchd" / "ai.anicca.job-search-browser.plist").read_bytes()
        )
        script = (root / "scripts" / "run-browser.sh").read_text(encoding="utf-8")
        self.assertEqual(browser["Label"], "ai.anicca.job-search-browser")
        self.assertTrue(browser["RunAtLoad"])
        self.assertTrue(browser["KeepAlive"])
        self.assertIn('--remote-debugging-port=0', script)
        self.assertIn('--remote-debugging-address=127.0.0.1', script)
        self.assertIn('job-search-daily', script)
        self.assertNotIn('daily-driver', script)
        self.assertNotIn('9222', script)

    def test_native_collector_has_isolated_launchagent_and_checksum_installer(self):
        root = Path(__file__).parents[1]
        service = plistlib.loads(
            (root / "launchd" / "ai.anicca.job-search-observability.plist").read_bytes()
        )
        installer = (root / "scripts" / "install-observability.sh").read_text()
        self.assertEqual(service["Label"], "ai.anicca.job-search-observability")
        self.assertTrue(service["RunAtLoad"])
        self.assertTrue(service["KeepAlive"])
        self.assertEqual(service["Umask"], 0o77)
        self.assertIn("__COLLECTOR_BINARY__", service["ProgramArguments"])
        self.assertTrue(
            any("__COLLECTOR_CONFIG__" in value for value in service["ProgramArguments"])
        )
        self.assertIn("JOB_HUNTER_TRACE_PATH", service["EnvironmentVariables"])
        self.assertIn("shasum -a 256", installer)
        self.assertIn("otelcol-contrib_0.158.0_darwin_arm64.tar.gz", installer)
        self.assertIn("opentelemetry-1.44.0-macos-arm64-py312.lock", installer)
        self.assertIn("--require-hashes", installer)
        self.assertIn('"$JOB_SEARCH_UV" pip install', installer)
        self.assertIn('chmod 600 "$TRACE_PATH"', installer)
        self.assertIn("for attempt in {1..20}", installer)
        self.assertIn("observability-health.json", installer)
        self.assertIn('DATA_ROOT="${JOB_SEARCH_DATA_ROOT:-', installer)
        self.assertIn("for attempt in {1..10}", installer)
        self.assertIn('"$JOB_SEARCH_LAUNCHCTL" print', installer)
        self.assertIn("ai.anicca.job-search-observability", installer)
        self.assertNotIn("ai.anicca.job-search-daily", installer)

    def test_inbox_shell_uses_deterministic_prefilter_before_model(self):
        root = Path(__file__).parents[1]
        script = (root / "scripts" / "run-inbox.sh").read_text(encoding="utf-8")
        self.assertIn("job_search_loop.inbox scan", script)
        self.assertIn(
            'if [[ "$NEW_COUNT" == "0" && "$PENDING_PREP_COUNT" == "0" ]]',
            script,
        )
        self.assertIn("job_search_loop.inbox mark", script)
        self.assertIn(".result_path", script)
        self.assertIn('--result "$RESULT_PATH"', script)

    def test_inbox_shell_processes_due_preps_without_new_email(self):
        root = Path(__file__).parents[1]
        script = (root / "scripts" / "run-inbox.sh").read_text(encoding="utf-8")
        self.assertIn("job_search_loop.interview_prep deliver", script)
        self.assertIn("job_search_loop.interview_prep append-prompt", script)
        self.assertIn("PENDING_PREP_COUNT", script)
        self.assertIn(
            'if [[ "$NEW_COUNT" == "0" && "$PENDING_PREP_COUNT" == "0" ]]',
            script,
        )
        self.assertLess(
            script.index("job_search_loop.interview_prep deliver"),
            script.index('if [[ "$NEW_COUNT"'),
        )

    def test_inbox_budget_exhaustion_is_clean_retry_before_ack(self):
        root = Path(__file__).parents[1]
        script = (root / "scripts" / "run-inbox.sh").read_text(encoding="utf-8")
        self.assertIn("set +e", script)
        self.assertIn("RUNNER_RC=$?", script)
        self.assertIn("set -e", script)
        self.assertIn('[[ "$RUNNER_RC" -eq 75 ]]', script)
        self.assertIn('.status == "budget_blocked"', script)
        self.assertIn('exit "$RUNNER_RC"', script)
        self.assertLess(
            script.index('.status == "budget_blocked"'),
            script.index("RESULT_PATH="),
        )
        self.assertLess(
            script.index('.status == "budget_blocked"'),
            script.index("job_search_loop.inbox mark"),
        )

    def test_daily_shell_skips_model_when_submission_quota_is_full(self):
        root = Path(__file__).parents[1]
        script = (root / "scripts" / "run-daily.sh").read_text(encoding="utf-8")
        self.assertIn("confirmed_daily_count", script)
        self.assertNotIn("daily_slot_count", script)
        self.assertIn('if [[ "$CONFIRMED_COUNT" -ge "10" ]]', script)
        self.assertIn("daily_quota_reached", script)
        self.assertIn("job_search_loop.quota", script)
        self.assertIn('--identity "job-search:dais"', script)

    def test_daily_shell_leases_browser_and_registers_release_before_runner(self):
        root = Path(__file__).parents[1]
        script = (root / "scripts" / "run-daily.sh").read_text(encoding="utf-8")
        acquire = "job_search_loop.browser_owner acquire"
        release = "job_search_loop.browser_owner release"
        beat = "job_search_loop.browser_owner hold"
        runner = "--task-class application-lane-agent"
        self.assertIn(acquire, script)
        self.assertIn(release, script)
        self.assertIn(beat, script)
        self.assertIn("TRAPEXIT", script)
        self.assertLess(script.index(acquire), script.index(runner))
        self.assertLess(script.index("TRAPEXIT"), script.index(runner))

    def test_healthcheck_covers_scheduler_ledger_and_private_state(self):
        root = Path(__file__).parents[1]
        script = (root / "scripts" / "healthcheck.sh").read_text(encoding="utf-8")
        self.assertIn('"$JOB_SEARCH_PLUTIL" -lint', script)
        self.assertIn("PRAGMA integrity_check", script)
        self.assertIn('if (candidate / "summary.json").is_file()', script)
        self.assertIn("interview-prep.sqlite3", script)
        self.assertIn("interview_preps", script)
        self.assertIn("ai.anicca.job-search-daily", script)
        self.assertIn("ai.anicca.job-search-inbox", script)
        self.assertIn("ai.anicca.job-search-learning", script)
        self.assertIn('"learning-": 8 * 24 * 3600', script)
        self.assertNotIn("cat /Users/anicca/.openclaw/.env", script)


if __name__ == "__main__":
    unittest.main()
