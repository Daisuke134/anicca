import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "local_loop.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("affiliate_local_loop", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LocalLoopTest(unittest.TestCase):
    def test_wake_requires_authenticated_provider_and_receipts_transition(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            private = root / "affiliate-credentials.md"
            private.write_text(
                "## ElevenLabs\n"
                "- Default affiliate link: `https://try.elevenlabs.io/example`\n",
                encoding="utf-8",
            )
            private.chmod(0o600)
            args = Namespace(private_markdown=private, state=root / "state", cdp_port=9324)
            provider = {
                "state": "AUTHENTICATED", "changed": True,
                "transition_id": "transition-1",
            }
            output = io.StringIO()
            with (
                patch.object(MODULE, "browser_ready", return_value=True),
                patch.object(MODULE, "provider_poll", return_value=provider),
                patch.object(MODULE, "run_revenue_cycle", return_value={
                    "state": "NO_TRANSACTIONS", "source_rows": 0,
                    "appended_transitions": 0,
                }),
                contextlib.redirect_stdout(output),
            ):
                MODULE.wake(args)
            event = json.loads(output.getvalue())
            self.assertEqual(event["status"], "READY_FOR_PUBLICATION")
            self.assertEqual(event["provider_state"], "AUTHENTICATED")
            self.assertEqual(event["provider_transition_id"], "transition-1")
            self.assertEqual(event["revenue_state"], "NO_TRANSACTIONS")

    def test_telegram_outbox_precedes_send_and_deduplicates_message_id(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            event = {"event_uuid": "event-1", "kind": "REVENUE_RECONCILED", "body": "report", "created_at": 1}
            calls = []

            def runner(command, **kwargs):
                calls.append(command)
                self.assertTrue((state / "telegram-outbox.jsonl").is_file())
                return subprocess.CompletedProcess(command, 0, '{"result":{"messageId":"7640"}}', "")

            with patch.object(MODULE.shutil, "which", return_value="/opt/homebrew/bin/openclaw"):
                first = MODULE.flush_telegram(state, event, runner=runner)
                second = MODULE.flush_telegram(state, event, runner=runner)
            self.assertEqual(first, {"state": "SENT", "sent": 1, "message_id": "7640"})
            self.assertEqual(second["state"], "NO_PENDING")
            self.assertEqual(len(calls), 1)
            self.assertEqual(json.loads((state / "telegram-sent.jsonl").read_text())["message_id"], "7640")

    def test_revenue_cycle_cooldown_is_independent_of_wake(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            MODULE.atomic_json(state / "revenue-cycle.json", {"completed_at": 1000})
            self.assertFalse(MODULE.revenue_cycle_due(state, now=4599))
            self.assertTrue(MODULE.revenue_cycle_due(state, now=4600))

    def test_placement_receipt_is_exactly_once_and_hides_tracking_link(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            private = root / "affiliate-credentials.md"
            private.write_text(
                "# Affiliate Credentials (local only)\n\n"
                "## ElevenLabs\n"
                "- Default affiliate link: `https://try.elevenlabs.io/example`\n",
                encoding="utf-8",
            )
            private.chmod(0o600)
            args = Namespace(
                private_markdown=private, state=root / "state",
                placement="article-1", locale="en", print_url=False,
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                MODULE.placement(args)
                MODULE.placement(args)
            rows = (args.state / "placements.jsonl").read_text().splitlines()
            emitted = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual([row["deduplicated"] for row in emitted], [False, True])
            self.assertNotIn("try.elevenlabs.io", output.getvalue())


if __name__ == "__main__":
    unittest.main()
