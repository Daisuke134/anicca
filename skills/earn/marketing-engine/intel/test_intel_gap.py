import json
import pathlib
import sys
import tempfile
import unittest


HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import intel_gap  # noqa: E402


class GapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_report_groups_open_testable_tactics_and_exposes_source_failure(self):
        rows = [
            {
                "id": "tactic.open.v1", "claim": "Test this", "mechanism": "Because",
                "applies_to": ["app", "content"], "testable": True, "status": "new",
                "source_url": "https://x.com/a/status/1", "evidence_url": "https://x.com/a/status/1",
            },
            {
                "id": "tactic.done.v1", "claim": "Already done", "mechanism": "Done",
                "applies_to": ["app"], "testable": True, "status": "done",
                "source_url": "https://example.com/done", "evidence_url": "https://example.com/done",
            },
        ]
        run = {
            "run_id": "a" * 32,
            "observed_at": "2026-08-01T00:00:00Z",
            "sources": [
                {"source_id": "x.a", "status": "success", "reason": None},
                {"source_id": "meta.ads", "status": "unavailable", "reason": "meta_ad_library_access_token_not_configured"},
            ],
        }

        report = intel_gap.build_gap_report(rows, run)

        self.assertIn("APP", report)
        self.assertIn("CONTENT", report)
        self.assertIn("tactic.open.v1", report)
        self.assertNotIn("tactic.done.v1", report)
        self.assertIn("https://x.com/a/status/1", report)
        self.assertIn("meta.ads: unavailable", report)
        self.assertIn("meta_ad_library_access_token_not_configured", report)

    def test_report_never_turns_missing_url_into_evidence(self):
        rows = [{
            "id": "tactic.open.v1", "claim": "Test this", "mechanism": "Because",
            "applies_to": ["ebook"], "testable": True, "status": "queued",
            "source_url": None, "source_null_reason": "exact_url_missing", "evidence_url": None,
            "evidence_null_reason": "exact_url_missing",
        }]
        report = intel_gap.build_gap_report(rows, {"run_id": "b" * 32, "observed_at": "2026-08-01T00:00:00Z", "sources": []})
        self.assertIn("evidence unavailable: exact_url_missing", report)
        self.assertNotIn("https://", report)

    def test_append_only_enrichment_supplies_recovered_exact_source(self):
        rows = [{
            "id": "tactic.open.v1", "claim": "Test this", "mechanism": "Because",
            "applies_to": ["app"], "testable": True, "status": "new",
            "source_url": None, "source_null_reason": "exact_url_missing",
            "evidence_url": None, "evidence_null_reason": "exact_url_missing",
        }]
        enrichments = [{"tactic_id": "tactic.open.v1", "source_url": "https://x.com/a/status/1"}]
        report = intel_gap.build_gap_report(
            rows, {"run_id": "c" * 32, "observed_at": "2026-08-01T00:00:00Z", "sources": []},
            enrichments=enrichments,
        )
        self.assertIn("https://x.com/a/status/1", report)
        self.assertNotIn("evidence unavailable", report)


if __name__ == "__main__":
    unittest.main()
