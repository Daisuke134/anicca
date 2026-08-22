import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.mercor_work_store import WorkStateStore
from job_search_loop.mercor_work_sync import sync_result


class MercorWorkSyncTests(unittest.TestCase):
    def test_syncs_optional_events_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = root / "result.json"
            result.write_text(
                json.dumps(
                    {
                        "mercor_work_events": [
                            {
                                "work_id": "application-1",
                                "event_id": "selected-1",
                                "next_state": "selected",
                                "evidence_ref": "gmail://message-1",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            first = sync_result(
                result_path=result,
                store_path=root / "work-events.jsonl",
                outbox_path=root / "telegram.sqlite3",
                sender=lambda **_: (_ for _ in ()).throw(RuntimeError("test transport")),
            )
            second = sync_result(
                result_path=result,
                store_path=root / "work-events.jsonl",
                outbox_path=root / "telegram.sqlite3",
                sender=lambda **_: (_ for _ in ()).throw(RuntimeError("test transport")),
            )

            self.assertEqual(first["synced_count"], 1)
            self.assertEqual(second["synced_count"], 1)
            self.assertEqual(WorkStateStore(root / "work-events.jsonl").current_state("application-1"), "selected")
            self.assertEqual(first["events"][0]["delivery"], "delivery_unknown")

    def test_missing_optional_events_is_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = root / "result.json"
            result.write_text("{}\n", encoding="utf-8")
            output = sync_result(
                result_path=result,
                store_path=root / "work-events.jsonl",
                outbox_path=root / "telegram.sqlite3",
            )
            self.assertEqual(output, {"synced_count": 0, "events": []})


if __name__ == "__main__":
    unittest.main()
