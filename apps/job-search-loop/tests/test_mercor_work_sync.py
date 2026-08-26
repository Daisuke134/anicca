import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.mercor_work_store import WorkStateStore
from job_search_loop.mercor_work_sync import sync_result


class MercorWorkSyncTests(unittest.TestCase):
    def test_unacknowledged_work_report_is_delivery_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = root / "result.json"
            result_path.write_text(
                json.dumps(
                    {"mercor_work_events": [{"work_id": "application-1", "event_id": "selected-unacknowledged", "next_state": "selected", "evidence_ref": "gmail://message-1"}]}
                ),
                encoding="utf-8",
            )
            result = sync_result(
                result_path=result_path,
                store_path=root / "work-events.jsonl",
                outbox_path=root / "telegram.sqlite3",
                sender=lambda **_: {"status": "send_started", "message_id": None},
            )

        self.assertEqual(result["events"][0]["delivery"], "delivery_unknown")

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

    def test_runtime_sync_accepts_explicit_authorization_and_acceptance_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            states = [
                ("selected", {}),
                ("contracted", {}),
                ("authorized_work", {"authorization_policy": "explicitly_allowed"}),
                ("work_submitted", {}),
                ("accepted", {"acceptance_status": "accepted"}),
            ]
            for index, (next_state, extra) in enumerate(states):
                result = root / f"result-{index}.json"
                result.write_text(
                    json.dumps(
                        {
                            "mercor_work_events": [
                                {
                                    "work_id": "application-1",
                                    "event_id": f"event-{index}",
                                    "next_state": next_state,
                                    "evidence_ref": f"evidence://{next_state}",
                                    **extra,
                                }
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                sync_result(
                    result_path=result,
                    store_path=root / "work-events.jsonl",
                    outbox_path=root / "telegram.sqlite3",
                    sender=lambda **_: {"status": "sent", "message_id": "telegram-chain"},
                )
            self.assertEqual(WorkStateStore(root / "work-events.jsonl").current_state("application-1"), "accepted")


if __name__ == "__main__":
    unittest.main()
