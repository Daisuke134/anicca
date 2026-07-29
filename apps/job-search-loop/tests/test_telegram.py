import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop import telegram


class TelegramReportTests(unittest.TestCase):
    def test_daily_report_sends_one_content_addressed_correction(self):
        sender = getattr(telegram, "send_daily_report", None)
        self.assertIsNotNone(sender)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "fake-openclaw"
            executable.write_text(
                """#!/usr/bin/env python3
import json
import pathlib
import sys

messages = pathlib.Path(__file__).with_suffix(".messages")
prior = json.loads(messages.read_text()) if messages.exists() else []
prior.append(sys.argv[sys.argv.index("--message") + 1])
messages.write_text(json.dumps(prior))
print(json.dumps({"messageId": str(700 + len(prior))}))
""",
                encoding="utf-8",
            )
            executable.chmod(0o700)
            database = root / "outbox.sqlite3"

            first = sender(
                database=database,
                japan_day="2026-07-29",
                message="Discovery blocked; no applications.",
                executable=str(executable),
            )
            correction = sender(
                database=database,
                japan_day="2026-07-29",
                message="Discovery recovered; best-fit role blocked on legal answers.",
                executable=str(executable),
            )
            duplicate = sender(
                database=database,
                japan_day="2026-07-29",
                message="Discovery recovered; best-fit role blocked on legal answers.",
                executable=str(executable),
            )

            self.assertEqual(first["message_id"], "701")
            self.assertEqual(correction["message_id"], "702")
            self.assertEqual(duplicate, correction)
            messages = json.loads(executable.with_suffix(".messages").read_text())
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[1], "Discovery recovered; best-fit role blocked on legal answers.")
            self.assertIn(":correction:", correction["event_key"])


if __name__ == "__main__":
    unittest.main()
