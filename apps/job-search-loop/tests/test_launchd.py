import plistlib
import unittest
from pathlib import Path


class LaunchdTests(unittest.TestCase):
    def test_plists_have_separate_bounded_schedules(self):
        root = Path(__file__).parents[1] / "launchd"
        daily = plistlib.loads((root / "ai.anicca.job-search-daily.plist").read_bytes())
        inbox = plistlib.loads((root / "ai.anicca.job-search-inbox.plist").read_bytes())
        self.assertTrue(daily["RunAtLoad"])
        self.assertEqual(daily["StartCalendarInterval"]["Hour"], 8)
        self.assertEqual(daily["StartCalendarInterval"]["Minute"], 30)
        self.assertEqual(inbox["StartInterval"], 900)
        self.assertNotEqual(daily["Label"], inbox["Label"])
        self.assertNotEqual(daily["ProgramArguments"][0], inbox["ProgramArguments"][0])

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

    def test_daily_shell_skips_model_when_submission_quota_is_full(self):
        root = Path(__file__).parents[1]
        script = (root / "scripts" / "run-daily.sh").read_text(encoding="utf-8")
        self.assertIn("daily_slot_count", script)
        self.assertIn('if [[ "$SLOT_COUNT" -ge "2" ]]', script)
        self.assertIn("daily_quota_reached", script)

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
        self.assertNotIn("cat /Users/anicca/.openclaw/.env", script)


if __name__ == "__main__":
    unittest.main()
