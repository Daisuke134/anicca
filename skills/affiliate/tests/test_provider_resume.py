import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "provider_cli.py"
SPEC = importlib.util.spec_from_file_location("provider_cli", SCRIPT)
provider_cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(provider_cli)


class ProviderResumeTest(unittest.TestCase):
    def test_reads_plain_and_inconsistently_wrapped_private_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            private = Path(temporary) / "credentials.md"
            private.write_text(
                "## ElevenLabs\n- Login: person@example.com`\n"
                "- Password: `correct horse battery staple`\n",
                encoding="utf-8",
            )
            private.chmod(0o600)
            self.assertEqual(
                provider_cli.read_login_credentials(private, "ElevenLabs"),
                ("person@example.com", "correct horse battery staple"),
            )

    def test_submits_once_and_never_receipts_credentials(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = argparse.Namespace(
                provider="elevenlabs",
                cdp_host="127.0.0.1",
                cdp_port=9324,
                receipt=Path(temporary) / "receipt.json",
                private_markdown=Path(temporary) / "credentials.md",
            )
            states = [
                {"provider": "elevenlabs", "state": "SIGN_IN_REQUIRED"},
                {"provider": "elevenlabs", "state": "AUTHENTICATED"},
            ]
            with (
                patch.object(provider_cli, "observe", side_effect=states),
                patch.object(provider_cli, "read_json", return_value=[{
                    "type": "page", "url": "https://elevenlabs.io/app/sign-in",
                    "title": "Sign In | ElevenLabs", "id": "tab-1",
                }]),
                patch.object(provider_cli, "submit_login") as submit,
                patch.object(provider_cli.time, "sleep"),
            ):
                receipt = provider_cli.resume(args)

            self.assertEqual(submit.call_count, 1)
            self.assertTrue(receipt["submitted"])
            self.assertEqual(receipt["state"], "AUTHENTICATED")
            serialized = json.dumps(receipt)
            self.assertNotIn("password", serialized.lower())
            self.assertNotIn("credential", serialized.lower())


if __name__ == "__main__":
    unittest.main()
