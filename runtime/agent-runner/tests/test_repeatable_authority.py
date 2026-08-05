import argparse
import tempfile
import unittest
from pathlib import Path

from agent_runner import command_for, provider_process_env


class RepeatableAuthorityTests(unittest.TestCase):
    def test_codex_repeatable_is_read_only_not_sandbox_bypass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(task_class="repeatable-agent", workdir=root)
            command = command_for(
                "codex", "codex", {},
                {"model": "gpt-5.6-luna", "effort": "medium"},
                args, "Extract and normalize public job postings only.",
                {"type": "object"}, root / "result.json", 60, None,
            )
            self.assertIn("read-only", command)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_claude_repeatable_has_no_tools(self):
        args = argparse.Namespace(task_class="repeatable-agent", workdir=Path("/tmp"))
        command = command_for(
            "claude-direct", "claude", {}, {"model": "sonnet"}, args,
            "Extract and normalize public job postings only.", {"type": "object"},
            Path("/tmp/result.json"), 60, None,
        )
        self.assertEqual(command[command.index("--tools") + 1], "")

    def test_repeatable_child_env_drops_outbound_and_private_credentials(self):
        source = {
            "PATH": "/usr/bin",
            "TELEGRAM_BOT_TOKEN": "secret",
            "GMAIL_TOKEN": "secret",
            "GOOGLE_APPLICATION_CREDENTIALS": "/secret.json",
            "GOG_KEYRING_PASSWORD": "secret",
            "JOB_SEARCH_PROFILE": "/private/profile.json",
            "FIRECRAWL_API_KEY": "public-search-key",
        }
        child = provider_process_env("codex", {}, source, task_class="repeatable-agent")
        self.assertEqual(child["PATH"], "/usr/bin")
        self.assertEqual(child["FIRECRAWL_API_KEY"], "public-search-key")
        for name in ("TELEGRAM_BOT_TOKEN", "GMAIL_TOKEN", "GOOGLE_APPLICATION_CREDENTIALS", "GOG_KEYRING_PASSWORD", "JOB_SEARCH_PROFILE"):
            self.assertNotIn(name, child)

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
                {"PATH": "/usr/bin", "JOB_SEARCH_PROFILE": "/private/profile.json", "TELEGRAM_BOT_TOKEN": "secret"},
                task_class="job-search-terra-high",
            )
            self.assertEqual(child["JOB_SEARCH_PROFILE"], "/private/profile.json")
            self.assertNotIn("TELEGRAM_BOT_TOKEN", child)


if __name__ == "__main__":
    unittest.main()
