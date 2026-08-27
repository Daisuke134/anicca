#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

import runner_report
import run_contract


class RunnerReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.evidence = self.root / "proof.json"
        self.evidence.write_text('{"observed":true}\n')

    def tearDown(self):
        self.tmp.cleanup()

    def payload(self):
        return {
            "runner_id": "score",
            "run_id": "1234567890abcdef1234567890abcdef",
            "environment": "production",
            "started_at": "2026-08-01T00:00:00Z",
            "finished_at": "2026-08-01T00:00:02Z",
            "status": "partial",
            "dry_run": False,
            "product_ids": [],
            "effects": [{
                "provider": "local",
                "action": "score",
                "status": "observed",
                "receipt": None,
                "evidence": str(self.evidence),
                "null_reason": "no_external_effect",
                "simulated": False,
            }],
            "metrics": [{
                "name": "judged_posts",
                "product_id": None,
                "value": None,
                "unit": "count",
                "observed_at": "2026-08-01T00:00:02Z",
                "source": "native_metrics",
                "evidence": str(self.evidence),
                "null_reason": "insufficient_verified_cohort",
                "simulated": False,
            }],
            "evidence_paths": [{"path": str(self.evidence), "kind": "result"}],
            "error": None,
        }

    def test_build_event_hashes_evidence_instead_of_trusting_caller_hash(self):
        event = runner_report.build_event(self.payload())
        self.assertEqual(event["schema_version"], "marketing.run.v1")
        self.assertEqual(event["evidence"][0]["bytes"], 18)
        run_contract.validate_event(event)

    def test_emit_without_send_records_once(self):
        payload_path = self.root / "payload.json"
        payload_path.write_text(json.dumps(self.payload()))
        first = runner_report.emit_payload(payload_path, self.root, send=False)
        second = runner_report.emit_payload(payload_path, self.root, send=False)
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(len((self.root / "run-reports.jsonl").read_text().splitlines()), 1)
        self.assertIsNone(first["delivery"])

    def test_missing_evidence_file_fails(self):
        payload = self.payload()
        payload["evidence_paths"][0]["path"] = str(self.root / "missing")
        with self.assertRaises(FileNotFoundError):
            runner_report.build_event(payload)


if __name__ == "__main__":
    unittest.main()
