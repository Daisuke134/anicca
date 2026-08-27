import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent_runner import provider_process_env, resolve_provider_profiles  # noqa: E402


class CodexProfileBoundaryTest(unittest.TestCase):
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
