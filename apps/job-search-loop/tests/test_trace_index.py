import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.trace_index import TraceIndex


class TraceIndexTests(unittest.TestCase):
    def test_timeline_joins_resource_and_span_identity_without_private_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "traces.jsonl"
            source.write_text(json.dumps({"resourceSpans": [{
                "resource": {"attributes": [
                    {"key": "service.version", "value": {"stringValue": "release-123"}},
                    {"key": "job_hunter.lane", "value": {"stringValue": "daily"}},
                    {"key": "job_hunter.resident_actor", "value": {"stringValue": "pid-456"}},
                    {"key": "email", "value": {"stringValue": "private@example.com"}},
                ]},
                "scopeSpans": [{"spans": [{
                    "traceId": "a" * 32, "spanId": "b" * 16,
                    "name": "application.confirmation",
                    "startTimeUnixNano": "1000000000",
                    "endTimeUnixNano": "2000000000",
                    "attributes": [
                        {"key": "application.id", "value": {"stringValue": "app-1"}},
                        {"key": "route.id", "value": {"stringValue": "route-1"}},
                        {"key": "failure.code", "value": {"stringValue": "none"}},
                        {"key": "evidence.sha256", "value": {"stringValue": "c" * 64}},
                        {"key": "confirmation.observed", "value": {"boolValue": True}},
                        {"key": "email", "value": {"stringValue": "private@example.com"}},
                    ],
                }]}],
            }]}) + "\n")
            index = TraceIndex(root / "trace-index.sqlite3")

            index.ingest(source)
            timeline = index.timeline(application_id="app-1")

            self.assertEqual(timeline, [{
                "trace_id": "a" * 32,
                "span_id": "b" * 16,
                "name": "application.confirmation",
                "start_time_unix_nano": 1_000_000_000,
                "end_time_unix_nano": 2_000_000_000,
                "release_sha": "release-123",
                "lane": "daily",
                "resident_actor": "pid-456",
                "application_id": "app-1",
                "route_id": "route-1",
                "failure_code": "none",
                "evidence_sha256": "c" * 64,
                "confirmation_observed": True,
            }])
            self.assertNotIn("private@example.com", json.dumps(timeline))
            index.close()

    def test_ingest_indexes_allowlisted_attributes_and_prunes_old_spans(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "traces.jsonl"
            source.write_text(json.dumps({"resourceSpans": [{"scopeSpans": [{"spans": [{
                "traceId": "a" * 32, "spanId": "b" * 16, "name": "submit.intent",
                "startTimeUnixNano": "1000000000", "endTimeUnixNano": "2000000000",
                "attributes": [
                    {"key": "application.id", "value": {"stringValue": "app-1"}},
                    {"key": "failure.code", "value": {"stringValue": "blocked"}},
                    {"key": "email", "value": {"stringValue": "private@example.com"}},
                ],
            }]}]}]}) + "\n")
            index = TraceIndex(root / "trace-index.sqlite3")
            self.assertEqual(index.ingest(source), 1)
            self.assertEqual(index.ingest(source), 0)
            rows = index.query(failure_code="blocked")
            self.assertEqual(rows[0]["application_id"], "app-1")
            self.assertNotIn("private@example.com", json.dumps(rows))
            self.assertEqual(index.prune_before(3_000_000_000), 1)
            index.close()
            self.assertEqual((root / "trace-index.sqlite3").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
