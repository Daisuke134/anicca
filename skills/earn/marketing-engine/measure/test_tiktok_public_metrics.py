from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("tiktok_public_metrics.py")
SPEC = importlib.util.spec_from_file_location("tiktok_public_metrics", MODULE_PATH)
assert SPEC and SPEC.loader
tiktok = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tiktok
SPEC.loader.exec_module(tiktok)


class TikTokPublicMetricsTest(unittest.TestCase):
    def test_handle_is_taken_only_from_canonical_native_url(self):
        self.assertEqual(
            tiktok.handle_from_url(
                "https://www.tiktok.com/@honne_reveal/video/7667910852011412756"
            ),
            "honne_reveal",
        )
        self.assertIsNone(tiktok.handle_from_url("https://example.com/@honne/video/1"))

    def test_exact_native_id_and_account_are_required(self):
        payload = {
            "itemList": [
                {
                    "id": "111",
                    "author": {"uniqueId": "expected"},
                    "stats": {
                        "playCount": 0,
                        "diggCount": 0,
                        "commentCount": 0,
                        "shareCount": 0,
                        "collectCount": 0,
                    },
                },
                {
                    "id": "222",
                    "author": {"uniqueId": "wrong"},
                    "stats": {"playCount": 999},
                },
            ]
        }
        found = tiktok.extract_wanted_items(
            payload, wanted_ids={"111", "222"}, expected_handle="expected"
        )
        self.assertEqual(set(found), {"111"})
        self.assertEqual(found["111"]["stats"]["playCount"], 0)

    def test_sanitized_evidence_contains_no_caption_or_media_url(self):
        payload = {
            "itemList": [
                {
                    "id": "111",
                    "desc": "private-to-evidence caption",
                    "video": {"playAddr": "https://expiring.example/video"},
                    "author": {"uniqueId": "expected"},
                    "stats": {"playCount": 12, "diggCount": 1},
                }
            ]
        }
        found = tiktok.extract_wanted_items(
            payload, wanted_ids={"111"}, expected_handle="expected"
        )
        text = str(found)
        self.assertNotIn("private-to-evidence", text)
        self.assertNotIn("expiring.example", text)
        self.assertEqual(
            set(found["111"]),
            {"native_post_id", "handle", "native_url", "stats"},
        )

    def test_profile_identity_items_keep_only_deterministic_match_fields(self):
        payload = {
            "itemList": [
                {
                    "id": "7669159327655054613",
                    "desc": "Full caption text",
                    "createTime": 1785552010,
                    "author": {"uniqueId": "obou_anicca"},
                    "video": {"playAddr": "https://expiring.example/video"},
                    "stats": {"playCount": 99},
                },
                {
                    "id": "wrong-account",
                    "desc": "must be excluded",
                    "createTime": 1785552011,
                    "author": {"uniqueId": "someone_else"},
                },
            ]
        }
        items = tiktok.extract_profile_identity_items(
            payload, expected_handle="obou_anicca"
        )
        self.assertEqual(
            items,
            [
                {
                    "id": "7669159327655054613",
                    "webVideoUrl": "https://www.tiktok.com/@obou_anicca/video/7669159327655054613",
                    "text": "Full caption text",
                    "createTime": 1785552010,
                    "authorMeta": {"name": "obou_anicca"},
                }
            ],
        )
        self.assertNotIn("expiring.example", str(items))


if __name__ == "__main__":
    unittest.main()
