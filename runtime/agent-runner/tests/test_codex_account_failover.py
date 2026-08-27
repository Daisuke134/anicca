import sys
import tempfile
import unittest
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent_runner import provider_process_env, resolve_provider_profiles  # noqa: E402


class CodexProfileBoundaryTest(unittest.TestCase):
    def test_escalation_route_has_account_two_then_cross_provider_fallback(self):
        config = json.loads((ROOT / "config.json").read_text())
        candidates = config["task_classes"]["escalation-agent"]["candidates"]
        self.assertEqual(
            [(row["provider"], row["model"], row.get("profile_alias")) for row in candidates],
            [
                ("codex", "gpt-5.6-terra", "acct2"),
                ("claude", "claude-sonnet-5", None),
            ],
        )

    def test_codex_keeps_code_mode_host_for_tool_using_escalations(self):
        config = json.loads((ROOT / "config.json").read_text())
        disabled = config["providers"]["codex"]["disabled_features"]
        self.assertNotIn("code_mode_host", disabled)
        self.assertNotIn("unified_exec", disabled)

    def test_candidate_resolves_one_explicit_profile_without_expansion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); auth = root / "auth.json"; auth.write_text("{}\n")
            providers = {"codex": {"profiles": {"acct2": {
                "automation_home": str(root / "automation"), "auth_file": str(auth),
            }}}}
            candidates = resolve_provider_profiles(
                [{"provider": "codex", "model": "fixture", "profile_alias": "acct2"}], providers)
            self.assertEqual(len(candidates), 1)
            env = provider_process_env("codex", candidates[0], {"PATH": "/usr/bin:/bin"})
            self.assertEqual(env["CODEX_HOME"], str(root / "automation"))
            self.assertEqual((root / "automation/auth.json").resolve(), auth.resolve())

    def test_codex_candidate_without_profile_alias_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "profile_alias"):
            resolve_provider_profiles(
                [{"provider": "codex", "model": "fixture"}],
                {"codex": {"profiles": {"acct2": {}}}})

    def test_non_codex_candidate_keeps_order_without_expansion(self):
        candidates = resolve_provider_profiles([
            {"provider": "codex", "model": "fixture", "profile_alias": "acct2"},
            {"provider": "claude", "model": "fallback"},
        ], {"codex": {"profiles": {"acct2": {
            "automation_home": "/tmp/a", "auth_file": "/tmp/auth",
        }}}, "claude": {}})
        self.assertEqual([(x["provider"], x.get("profile_alias")) for x in candidates], [
            ("codex", "acct2"), ("claude", None)])


if __name__ == "__main__": unittest.main()
