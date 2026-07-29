import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from job_search_loop.calendar_sync import event_key, prep_windows
from job_search_loop.inbox import (
    classify_message,
    mark_processed_threads,
    mark_threads_seen,
    select_new_recruiting_threads,
)
from job_search_loop.outbox import DeliveryUncertain, Outbox
from job_search_loop.summary import build_summary


class OperationsTests(unittest.TestCase):
    def test_inbox_classification(self):
        self.assertEqual(
            classify_message(
                "Verify your candidate account",
                "Click this link to confirm your email address.",
            ),
            "account_verification",
        )
        self.assertEqual(
            classify_message("Interview invitation", "Choose a time with our recruiter"),
            "interview",
        )
        self.assertEqual(
            classify_message("Application received", "Thank you for applying"),
            "confirmation",
        )
        self.assertEqual(
            classify_message("Update", "We will not be moving forward"), "rejection"
        )

    def test_inbox_poll_only_returns_unseen_recruiting_threads(self):
        threads = [
            {
                "id": "already-seen",
                "subject": "Interview invitation",
                "from": "recruiting@example.com",
            },
            {
                "id": "new-interview",
                "subject": "一次面接のご案内",
                "from": "採用担当 <jobs@example.jp>",
            },
            {
                "id": "newsletter",
                "subject": "Your weekly news",
                "from": "news@example.com",
            },
            {
                "id": "oauth-noise",
                "subject": "A third-party OAuth application was added",
                "from": "GitHub <noreply@github.com>",
            },
            {
                "id": "workday-verification",
                "subject": "Verify your candidate account",
                "from": "ASML People Services <asml@myworkday.com>",
            },
        ]
        selected = select_new_recruiting_threads(threads, {"already-seen"})
        self.assertEqual(
            [row["id"] for row in selected],
            ["new-interview", "workday-verification"],
        )

    def test_seen_thread_checkpoint_is_private_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "seen.json"
            mark_threads_seen(path, ["thread-1", "thread-1", "thread-2"])
            mark_threads_seen(path, ["thread-2"])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                __import__("json").loads(path.read_text(encoding="utf-8"))["thread_ids"],
                ["thread-1", "thread-2"],
            )

    def test_partial_result_acknowledges_only_processed_candidate_threads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = root / "candidates.json"
            result = root / "result.json"
            seen = root / "seen.json"
            candidates.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "new_count": 2,
                        "thread_ids": ["thread-1", "thread-2"],
                    }
                ),
                encoding="utf-8",
            )
            result.write_text(
                json.dumps(
                    {
                        "processed_threads": 1,
                        "processed_thread_ids": ["thread-1"],
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                mark_processed_threads(seen, candidates, result),
                ["thread-1"],
            )
            self.assertEqual(load_seen := json.loads(seen.read_text()), {
                "version": 1,
                "thread_ids": ["thread-1"],
            })
            self.assertNotIn("thread-2", load_seen["thread_ids"])
            self.assertEqual(seen.stat().st_mode & 0o777, 0o600)

    def test_partial_result_unknown_or_mismatched_ids_acknowledges_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = root / "candidates.json"
            seen = root / "seen.json"
            candidates.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "new_count": 2,
                        "thread_ids": ["thread-1", "thread-2"],
                    }
                ),
                encoding="utf-8",
            )
            for payload in (
                {
                    "processed_threads": 1,
                    "processed_thread_ids": ["unknown-thread"],
                },
                {
                    "processed_threads": 2,
                    "processed_thread_ids": ["thread-1"],
                },
                {
                    "processed_threads": 2,
                    "processed_thread_ids": ["thread-1", "thread-1"],
                },
            ):
                result = root / "result.json"
                result.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(payload=payload), self.assertRaises(ValueError):
                    mark_processed_threads(seen, candidates, result)
                self.assertFalse(seen.exists())

    def test_calendar_key_and_prep_windows_are_stable(self):
        start = datetime(2026, 8, 5, 1, 0, tzinfo=timezone.utc)
        self.assertEqual(event_key("thread-1", start), event_key("thread-1", start))
        now = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(prep_windows(now, start), ("three_day", "one_day"))

    def test_outbox_never_blind_retries_send_started(self):
        with tempfile.TemporaryDirectory() as directory:
            outbox = Outbox(Path(directory) / "outbox.sqlite3")
            row = outbox.enqueue("daily:2026-07-28", "hello")
            claim = outbox.claim(row)
            outbox.mark_send_started(row, claim)
            with self.assertRaises(DeliveryUncertain):
                outbox.claim(row)
            outbox.close()

    def test_summary_contains_counts_without_pii(self):
        value = build_summary(
            day="2026-07-28",
            states=["submitted", "submitted", "rejected"],
            model_route="terra-medium-bounded",
        )
        self.assertEqual(value["counts"]["submitted"], 2)
        self.assertNotIn("email", str(value).lower())


if __name__ == "__main__":
    unittest.main()
