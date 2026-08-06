import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.trace_index import TraceIndex


class TraceIndexTests(unittest.TestCase):
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
