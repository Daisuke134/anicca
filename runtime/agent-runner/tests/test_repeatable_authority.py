import argparse
import tempfile
import unittest
from pathlib import Path

from agent_runner import command_for, provider_process_env


class RepeatableAuthorityTests(unittest.TestCase):
    def test_locked_main_connector_and_marketing_gig_repeatable_authority_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(task_class="repeatable-agent", workdir=root)
            command = command_for(
                "codex", "codex", {},
                {"model": "gpt-5.6-luna", "effort": "medium"},
                args, "Extract and normalize public job postings only.",
                {"type": "object"}, root / "result.json", 60, None,
            )
            self.assertIn("--dangerously-bypass-approvals-and-sandbox", command)
            self.assertNotIn("--sandbox", command)

            source = {
                "PATH": "/usr/bin",
                "TELEGRAM_BOT_TOKEN": "secret",
                "GMAIL_TOKEN": "secret",
                "GOOGLE_APPLICATION_CREDENTIALS": "/secret.json",
                "GOG_KEYRING_PASSWORD": "secret",
                "CLOAK_SESSION": "session",
                "JOB_SEARCH_PROFILE": "/private/profile.json",
                "FIRECRAWL_API_KEY": "public-search-key",
            }
            child = provider_process_env("codex", {}, source, task_class="repeatable-agent")
            self.assertEqual(child, source)

    def test_locked_main_marketing_gig_repeatable_claude_keeps_tools(self):
        args = argparse.Namespace(task_class="repeatable-agent", workdir=Path("/tmp"))
        command = command_for(
            "claude-direct", "claude", {}, {"model": "sonnet"}, args,
            "Extract and normalize public job postings only.", {"type": "object"},
            Path("/tmp/result.json"), 60, None,
        )
        self.assertNotIn("--tools", command)

    def test_job_search_terra_high_is_read_only_and_keeps_profile_without_outbound_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(task_class="job-search-terra-high", workdir=root)
            command = command_for(
                "codex", "codex", {},
                {"model": "gpt-5.6-terra", "effort": "high"}, args,
                "Analyze one explicitly escalated dream application.",
                {"type": "object"}, root / "result.json", 60, None,
            )
            self.assertIn("read-only", command)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
            child = provider_process_env(
                "codex", {},
                {
                    "PATH": "/usr/bin",
                    "JOB_SEARCH_PROFILE": "/private/profile.json",
                    "TELEGRAM_BOT_TOKEN": "secret",
                    "GMAIL_TOKEN": "secret",
                    "JOB_SEARCH_BROWSER": "http://127.0.0.1:9222",
                },
                task_class="job-search-terra-high",
            )
            self.assertEqual(child["JOB_SEARCH_PROFILE"], "/private/profile.json")
            self.assertNotIn("TELEGRAM_BOT_TOKEN", child)
            self.assertNotIn("GMAIL_TOKEN", child)
            self.assertNotIn("JOB_SEARCH_BROWSER", child)


if __name__ == "__main__":
    unittest.main()
