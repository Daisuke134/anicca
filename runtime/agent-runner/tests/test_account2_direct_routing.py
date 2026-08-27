#!/usr/bin/env python3
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "runtime" / "agent-runner" / "config.json"


class CodexAccountRoutingTest(unittest.TestCase):
    def test_codex_orders_account_one_then_account_two_without_proxy_override(self):
        provider = json.loads(CONFIG.read_text(encoding="utf-8"))["providers"]["codex"]

        self.assertEqual(
            [account["auth_file"] for account in provider["accounts"]],
            ["~/.codex/auth.json", "~/.codex-acct2/auth.json"],
        )
        self.assertNotIn("model_provider", provider)
        self.assertNotIn("model_providers", provider)


if __name__ == "__main__":
    unittest.main()
