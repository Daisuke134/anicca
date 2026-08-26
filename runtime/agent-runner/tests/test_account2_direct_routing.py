#!/usr/bin/env python3
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "runtime" / "agent-runner" / "config.json"


class Account2DirectRoutingTest(unittest.TestCase):
    def test_codex_uses_account2_without_proxy_override(self):
        provider = json.loads(CONFIG.read_text(encoding="utf-8"))["providers"]["codex"]

        self.assertEqual(provider["auth_file"], "~/.codex-acct2/auth.json")
        self.assertNotIn("model_provider", provider)
        self.assertNotIn("model_providers", provider)


if __name__ == "__main__":
    unittest.main()
