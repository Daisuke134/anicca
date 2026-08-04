from __future__ import annotations

import datetime as dt
import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("publication_ledger.py")
SPEC = importlib.util.spec_from_file_location("publication_ledger", MODULE_PATH)
assert SPEC and SPEC.loader
ledger = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ledger
SPEC.loader.exec_module(ledger)


def post(identifier="p1", platform="instagram-standalone", state="PUBLISHED"):
    return {
        "id": identifier,
        "group": "g1",
        "state": state,
        "content": "  Full caption\ntext ",
        "publishDate": "2026-08-01T00:00:00Z",
        "releaseId": "native1" if state == "PUBLISHED" else None,
        "releaseURL": "https://www.instagram.com/reel/abc/" if state == "PUBLISHED" else None,
        "integration": {"id": "i1", "name": "account", "providerIdentifier": platform},
    }


class PublicationLedgerTest(unittest.TestCase):
    def test_direct_provider_receipt_resolves(self):
        row = ledger.make_row(post(), [], "2026-08-01T01:00:00Z")
        self.assertEqual(row["identity_status"], "resolved")
        self.assertEqual(row["native_post_id"], "native1")
        self.assertEqual(row["resolution_method"], "postiz_provider_native_receipt")

    def test_error_is_retained_without_native_identity(self):
        row = ledger.make_row(post(state="ERROR"), [], "2026-08-01T01:00:00Z")
        self.assertEqual(row["identity_status"], "error")
        self.assertIsNone(row["native_post_id"])
        ledger.validate_rows([row])

    def test_tiktok_publish_token_is_not_treated_as_native_id(self):
        value = post(platform="tiktok")
        value["releaseId"] = "v_pub_file~v2-1.123456789"
        value["releaseURL"] = "https://www.tiktok.com/@handle"
        row = ledger.make_row(value, [], "2026-08-01T01:00:00Z")
        self.assertEqual(row["identity_status"], "unresolved")
        self.assertIsNone(row["native_post_id"])

    def test_tiktok_requires_unique_full_caption_and_time_match(self):
        value = post(platform="tiktok")
        value["releaseURL"] = "https://www.tiktok.com/@handle"
        item = {
            "id": "video1", "webVideoUrl": "https://www.tiktok.com/@handle/video/video1",
            "text": "Full caption text", "createTimeISO": "2026-08-01T00:00:10Z",
            "authorMeta": {"name": "handle"},
        }
        row = ledger.make_row(value, [item], "2026-08-01T01:00:00Z")
        self.assertEqual(row["identity_status"], "resolved")
        self.assertEqual(row["native_post_id"], "video1")

    def test_duplicate_tiktok_candidates_remain_ambiguous(self):
        value = post(platform="tiktok")
        value["releaseURL"] = "https://www.tiktok.com/@handle"
        items = [{
            "id": f"video{number}", "webVideoUrl": f"https://x/{number}",
            "text": "Full caption text", "createTimeISO": f"2026-08-01T00:00:0{number}Z",
            "authorMeta": {"name": "handle"},
        } for number in (1, 2)]
        row = ledger.make_row(value, items, "2026-08-01T01:00:00Z")
        self.assertEqual(row["identity_status"], "ambiguous")
        self.assertIsNone(row["native_post_url"])
        self.assertEqual(row["candidate_count"], 2)

    def test_caption_hash_is_not_mislabeled_as_creative_hash(self):
        row = ledger.make_row(post(), [], "2026-08-01T01:00:00Z")
        self.assertIsNotNone(row["content_sha256"])
        self.assertIsNone(row["creative_sha256"])
        self.assertEqual(row["creative_sha256_null_reason"], "legacy_postiz_list_omits_asset_identity")

    def test_duplicate_native_identity_is_rejected(self):
        one = ledger.make_row(post("p1"), [], "2026-08-01T01:00:00Z")
        two = ledger.make_row(post("p2"), [], "2026-08-01T01:00:00Z")
        with self.assertRaisesRegex(ValueError, "duplicate native identity"):
            ledger.validate_rows([one, two])

    def test_merge_is_idempotent_by_postiz_id(self):
        one = ledger.make_row(post("p1"), [], "2026-08-01T01:00:00Z")
        newer = dict(one, observed_at="2026-08-01T02:00:00Z")
        rows = ledger.merge_rows([one], [newer])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["observed_at"], "2026-08-01T02:00:00Z")

    def test_report_uses_only_published_denominator(self):
        published = ledger.make_row(post("p1"), [], "2026-08-01T01:00:00Z")
        error = ledger.make_row(post("p2", state="ERROR"), [], "2026-08-01T01:00:00Z")
        start = dt.datetime(2026, 7, 31, tzinfo=dt.timezone.utc)
        end = dt.datetime(2026, 8, 2, tzinfo=dt.timezone.utc)
        report = ledger.reconciliation_report([published, error], start, end, "now")
        self.assertEqual(report["published_denominator"], 1)
        self.assertEqual(report["published_resolved"], 1)
        self.assertTrue(report["passes_95_percent_gate"])


if __name__ == "__main__":
    unittest.main()
