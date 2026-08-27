import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_runner import (
    codex_effect_started,
    expand_codex_candidates,
    provider_process_env,
    should_retry_next_codex_account,
)


CONFIG = ROOT / "config.json"


class CodexAccountFailoverTest(unittest.TestCase):
    def test_canonical_config_orders_account_one_before_account_two(self):
        provider = json.loads(CONFIG.read_text(encoding="utf-8"))["providers"]["codex"]
        self.assertEqual(
            [account["alias"] for account in provider["accounts"]],
            ["account-1", "account-2"],
        )
        self.assertEqual(
            [account["auth_file"] for account in provider["accounts"]],
            ["~/.codex/auth.json", "~/.codex-acct2/auth.json"],
        )

    def test_each_effective_candidate_resolves_its_own_home_and_auth_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            auth_one = root / "account-one-auth.json"
            auth_two = root / "account-two-auth.json"
            auth_one.write_text('{"fixture":"one"}\n', encoding="utf-8")
            auth_two.write_text('{"fixture":"two"}\n', encoding="utf-8")
            provider = {
                "accounts": [
                    {
                        "alias": "account-1",
                        "automation_home": str(root / "home-one"),
                        "auth_file": str(auth_one),
                    },
                    {
                        "alias": "account-2",
                        "automation_home": str(root / "home-two"),
                        "auth_file": str(auth_two),
                    },
                ],
            }

            candidates = expand_codex_candidates(
                [{"provider": "codex", "model": "fixture-model"}],
                {"codex": provider},
            )

            self.assertEqual([candidate["account"] for candidate in candidates], [
                "account-1", "account-2",
            ])
            self.assertEqual(
                [(candidate["account_index"], candidate["account_count"]) for candidate in candidates],
                [(0, 2), (1, 2)],
            )
            for candidate, auth_source, home in zip(
                candidates,
                (auth_one, auth_two),
                (root / "home-one", root / "home-two"),
            ):
                self.assertEqual(candidate["automation_home"], str(home))
                self.assertEqual(candidate["auth_file"], str(auth_source))
                child_env = provider_process_env(
                    "codex",
                    {
                        "automation_home": candidate["automation_home"],
                        "auth_file": candidate["auth_file"],
                    },
                    {"PATH": "/usr/bin:/bin"},
                )
                self.assertEqual(child_env["CODEX_HOME"], str(home))
                self.assertEqual(
                    (home / "auth.json").resolve(), auth_source.resolve()
                )
                self.assertNotEqual(
                    child_env["CODEX_HOME"],
                    str(root / ("home-two" if home.name == "home-one" else "home-one")),
                )

    def test_only_pre_effect_quota_or_auth_retries_next_account(self):
        self.assertTrue(should_retry_next_codex_account("transient_quota", False))
        self.assertTrue(should_retry_next_codex_account("transient_auth", False))
        for error_class in (
            "transient_timeout", "transient_unavailable", "validation_or_task_failure",
        ):
            self.assertFalse(should_retry_next_codex_account(error_class, False))
        self.assertFalse(should_retry_next_codex_account("transient_quota", True))

    def test_codex_effect_detection_reads_json_events_not_free_text(self):
        self.assertFalse(codex_effect_started(json.dumps({
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "run a command later"},
        })))
        self.assertTrue(codex_effect_started(json.dumps({
            "type": "item.started",
            "item": {"type": "command_execution", "command": "true"},
        })))

    def test_account_expansion_preserves_next_provider_order(self):
        candidates = expand_codex_candidates(
            [
                {"provider": "codex", "model": "fixture"},
                {"provider": "claude", "model": "fallback"},
            ],
            {
                "codex": {"accounts": [
                    {"alias": "account-1", "automation_home": "/tmp/a1", "auth_file": "/tmp/auth1"},
                    {"alias": "account-2", "automation_home": "/tmp/a2", "auth_file": "/tmp/auth2"},
                ]},
                "claude": {},
            },
        )
        self.assertEqual(
            [(candidate["provider"], candidate.get("account")) for candidate in candidates],
            [("codex", "account-1"), ("codex", "account-2"), ("claude", None)],
        )


if __name__ == "__main__":
    unittest.main()
