import argparse
import json
import tempfile
import unittest
from pathlib import Path

from agent_runner import command_for


class CodexSchemaCompatibilityTest(unittest.TestCase):
    def test_codex_receives_supported_schema_copy_while_local_schema_stays_strict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original_path = root / "inbox.schema.json"
            original = {
                "type": "object",
                "additionalProperties": False,
                "required": ["processed_message_ids"],
                "properties": {
                    "processed_message_ids": {
                        "type": "array",
                        "uniqueItems": True,
                        "items": {"type": "string"},
                    }
                },
            }
            original_path.write_text(json.dumps(original), encoding="utf-8")
            result_path = root / "attempt-01.result.json"
            args = argparse.Namespace(
                schema=original_path,
                task_class="composition-agent",
                workdir=root,
            )

            command = command_for(
                "codex",
                "/opt/homebrew/bin/codex",
                {},
                {"model": "gpt-5.6-terra", "effort": "medium"},
                args,
                "Process the bounded inbox candidates.",
                original,
                result_path,
                60,
                None,
                prompt_via_stdin=True,
            )

            provider_schema_path = Path(
                command[command.index("--output-schema") + 1]
            )
            provider_schema = json.loads(
                provider_schema_path.read_text(encoding="utf-8")
            )
            self.assertNotEqual(provider_schema_path, original_path)
            self.assertNotIn(
                "uniqueItems",
                provider_schema["properties"]["processed_message_ids"],
            )
            self.assertTrue(
                json.loads(original_path.read_text(encoding="utf-8"))["properties"][
                    "processed_message_ids"
                ]["uniqueItems"]
            )
            self.assertEqual(provider_schema_path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
