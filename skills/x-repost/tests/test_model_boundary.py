import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "model_boundary.py"
CLI = Path(__file__).parents[1] / "x-repost-cli.sh"


class ModelBoundaryTest(unittest.TestCase):
    def run_boundary(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], check=False, text=True,
            capture_output=True,
        )

    def test_prepare_creates_isolated_home_bound_to_requested_auth(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            auth = root_path / "account-2" / "auth.json"
            auth.parent.mkdir()
            auth.write_text(json.dumps({"tokens": {"access_token": "secret"}}))
            automation_home = root_path / "automation"
            result = self.run_boundary(
                "prepare", "--home", str(automation_home), "--auth", str(auth)
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()), automation_home.resolve())
            self.assertEqual((automation_home / "auth.json").resolve(), auth.resolve())
            self.assertEqual(os.stat(automation_home).st_mode & 0o777, 0o700)

    def test_prepare_rejects_an_existing_different_auth_target(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            expected, wrong = root_path / "account-2.json", root_path / "account-1.json"
            expected.write_text("{}")
            wrong.write_text("{}")
            automation_home = root_path / "automation"
            automation_home.mkdir()
            (automation_home / "auth.json").symlink_to(wrong)
            result = self.run_boundary(
                "prepare", "--home", str(automation_home), "--auth", str(expected)
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("auth target mismatch", result.stderr)
            self.assertEqual((automation_home / "auth.json").resolve(), wrong.resolve())

    def test_classify_reads_usage_limit_from_codex_event_stream(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            stdout = Path(root) / "model.stdout"
            stdout.write_text(json.dumps({
                "type": "error", "message": "You've hit your usage limit. Try again later."
            }))
            result = self.run_boundary("classify", str(stdout))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "quota")

    def test_classify_preserves_network_failure_even_when_outer_timeout_fires(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            stdout = Path(root) / "model.stdout"
            stdout.write_text(json.dumps({
                "type": "error",
                "message": "failed to lookup address information: nodename nor servname provided",
            }))
            result = self.run_boundary(
                "classify", str(stdout), "--returncode", "124"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "network")

    def test_cli_uses_prepared_home_and_classifies_all_model_calls(self) -> None:
        normalized = " ".join(CLI.read_text().split())
        self.assertIn('"$PY" "$MODEL_BOUNDARY" prepare', normalized)
        self.assertIn('CODEX_HOME="$CODEX_AUTOMATION_HOME"', normalized)
        self.assertIn('"$PY" "$MODEL_BOUNDARY" classify', normalized)
        self.assertIn('"$EV/model.stdout" "$EV/model.err" "$out_file"', normalized)
        self.assertEqual(normalized.count("handle_model_failure"), 5)


if __name__ == "__main__":
    unittest.main()
