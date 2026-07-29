import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from job_search_loop.profile_setup import ProfileSetupError, collect_interactive


APP_ROOT = Path(__file__).resolve().parents[1]


class ProfileSetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.answers = self.root / "answers.json"
        self.output = self.root / "private" / "profile.json"

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def _answers() -> dict:
        return {
            "version": 1,
            "candidate": {
                "name": "Release Candidate",
                "application_email": "candidate@example.test",
            },
            "facts": [
                {
                    "id": "verified-ai",
                    "claim": "Built a verified AI product.",
                    "evidence": "User-entered portfolio evidence",
                }
            ],
        }

    def _run(self, *extra: str):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "job_search_loop.profile_setup",
                "--answers",
                str(self.answers),
                "--output",
                str(self.output),
                *extra,
            ],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(APP_ROOT)},
        )

    def test_answers_file_writes_exact_private_valid_profile(self):
        value = self._answers()
        self.answers.write_text(json.dumps(value), encoding="utf-8")

        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.output.read_text(encoding="utf-8")), value)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.output.parent.stat().st_mode & 0o777, 0o700)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["profile_path"], str(self.output))
        self.assertEqual(receipt["fact_count"], 1)
        self.assertNotIn("candidate@example.test", result.stdout)

    def test_placeholder_values_fail_closed_without_output(self):
        value = self._answers()
        value["facts"][0]["evidence"] = "REPLACE_ME"
        self.answers.write_text(json.dumps(value), encoding="utf-8")

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("placeholder", result.stderr)
        self.assertFalse(self.output.exists())

    def test_existing_profile_requires_explicit_replace(self):
        self.answers.write_text(json.dumps(self._answers()), encoding="utf-8")
        first = self._run()
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.output.read_bytes()
        value = self._answers()
        value["candidate"]["name"] = "Replacement Candidate"
        self.answers.write_text(json.dumps(value), encoding="utf-8")

        blocked = self._run()

        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("already exists", blocked.stderr)
        self.assertEqual(self.output.read_bytes(), before)

        replaced = self._run("--replace")
        self.assertEqual(replaced.returncode, 0, replaced.stderr)
        self.assertEqual(
            json.loads(self.output.read_text(encoding="utf-8"))["candidate"]["name"],
            "Replacement Candidate",
        )

    def test_answers_require_application_email_but_add_no_legal_facts(self):
        value = self._answers()
        del value["candidate"]["application_email"]
        self.answers.write_text(json.dumps(value), encoding="utf-8")

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("application_email", result.stderr)
        self.assertFalse(self.output.exists())

    def test_interactive_collection_preserves_only_explicit_answers(self):
        responses = iter(
            [
                "Interactive Candidate",
                "interactive@example.test",
                "Shipped an AI assistant.",
                "Public product page supplied by user",
                "",
            ]
        )
        with patch("builtins.input", side_effect=lambda _prompt: next(responses)):
            value = collect_interactive()

        self.assertEqual(value["candidate"]["name"], "Interactive Candidate")
        self.assertEqual(
            value["candidate"]["application_email"], "interactive@example.test"
        )
        self.assertEqual(value["facts"][0]["id"], "fact-001")
        self.assertEqual(len(value["facts"]), 1)
        encoded = json.dumps(value).lower()
        self.assertNotIn("nationality", encoded)
        self.assertNotIn("visa", encoded)
        self.assertNotIn("work_authorization", encoded)

    def test_interactive_collection_needs_at_least_one_verified_fact(self):
        responses = iter(["Candidate", "candidate@example.test", ""])
        with patch("builtins.input", side_effect=lambda _prompt: next(responses)):
            with self.assertRaisesRegex(ProfileSetupError, "fact"):
                collect_interactive()


if __name__ == "__main__":
    unittest.main()
