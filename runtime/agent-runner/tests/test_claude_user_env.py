import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent_runner import provider_process_env  # noqa: E402


class ClaudeUserEnvTest(unittest.TestCase):
    """launchd omits USER; the claude CLI reads stored OAuth credentials only
    when USER is set, so a launchd-run claude call fails "Not logged in"
    without this (measured 2026-09-04)."""

    def test_claude_direct_gets_user_when_missing(self):
        launchd_environ = {"HOME": "/Users/anicca", "PATH": "/usr/bin:/bin"}
        env = provider_process_env("claude-direct", {}, environ=launchd_environ)
        self.assertTrue(env.get("USER"))

    def test_claude_direct_keeps_existing_user(self):
        environ = {"HOME": "/Users/anicca", "PATH": "/usr/bin:/bin", "USER": "someone"}
        env = provider_process_env("claude-direct", {}, environ=environ)
        self.assertEqual(env.get("USER"), "someone")


if __name__ == "__main__":
    unittest.main()
