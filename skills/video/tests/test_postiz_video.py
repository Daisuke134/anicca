#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "lm-distribution" / "postiz_video.py"
SPEC = importlib.util.spec_from_file_location("postiz_video", MODULE_PATH)
postiz_video = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(postiz_video)


class PostizVideoTests(unittest.TestCase):
    def test_payload_is_direct_public_video_with_exact_caption_and_media(self):
        payload = postiz_video.build_payload(
            integration="cmp9txjdp01c8oh0yb6dhlarr",
            caption="Exact caption\n#line",
            title="Life Manager",
            upload_id="upload-1",
            upload_path="https://uploads.example/video.mp4",
            now_iso="2026-07-24T00:00:00.000Z",
        )
        post = payload["posts"][0]
        self.assertEqual(post["integration"]["id"], "cmp9txjdp01c8oh0yb6dhlarr")
        self.assertEqual(post["value"][0]["content"], "Exact caption\n#line")
        self.assertEqual(post["value"][0]["image"], [{"id": "upload-1", "path": "https://uploads.example/video.mp4"}])
        self.assertEqual(post["settings"]["content_posting_method"], "DIRECT_POST")
        self.assertEqual(post["settings"]["privacy_level"], "PUBLIC_TO_EVERYONE")
        self.assertTrue(post["settings"]["video_made_with_ai"])

    def test_extract_post_id_accepts_the_real_postiz_array_shape_only(self):
        self.assertEqual(postiz_video.extract_post_id([{"postId": "post-1"}]), "post-1")
        with self.assertRaises(postiz_video.PostizError):
            postiz_video.extract_post_id({"id": "upload-id-is-not-post-id"})

    def test_find_published_requires_state_and_public_release_url(self):
        rows = {
            "posts": [
                {"id": "p1", "state": "QUEUE", "releaseURL": None},
                {"id": "p2", "state": "PUBLISHED", "releaseURL": "https://www.tiktok.com/@life/video/123"},
            ]
        }
        self.assertEqual(
            postiz_video.find_post(rows, "p2"),
            {"state": "PUBLISHED", "post_url": "https://www.tiktok.com/@life/video/123"},
        )
        self.assertEqual(postiz_video.find_post(rows, "p1"), {"state": "QUEUE", "post_url": None})

    def test_find_post_rejects_published_without_public_url(self):
        with self.assertRaises(postiz_video.PostizError):
            postiz_video.find_post([{"id": "p", "state": "PUBLISHED"}], "p")

    def test_find_post_derives_exact_video_url_from_profile_url_and_release_id(self):
        row = {
            "id": "post-1",
            "state": "PUBLISHED",
            "releaseURL": "https://www.tiktok.com/@life.manager",
            "releaseId": "v_pub_file~v2-1.7999999999999999999",
        }
        self.assertEqual(
            postiz_video.find_post([row], "post-1"),
            {
                "state": "PUBLISHED",
                "post_url": "https://www.tiktok.com/@life.manager/video/7999999999999999999",
            },
        )

    def test_exact_recent_provider_effect_reconciles_before_upload(self):
        rows = {
            "posts": [{
                "id": "post-1",
                "state": "PUBLISHED",
                "content": "Exact caption\n#line",
                "integration": {"id": "integration-1"},
                "releaseURL": "https://www.tiktok.com/@life",
                "releaseId": "v_pub_file~v2-1.7999999999999999999",
            }],
        }
        self.assertEqual(
            postiz_video.find_existing_post(
                rows,
                integration="integration-1",
                caption="Exact caption\n#line",
            ),
            {
                "post_id": "post-1",
                "state": "PUBLISHED",
                "post_url": "https://www.tiktok.com/@life/video/7999999999999999999",
                "reconciled": True,
            },
        )

    def test_profile_release_url_resolves_to_matching_recent_video(self):
        payload = {
            "entries": [
                {
                    "id": "111",
                    "url": "https://www.tiktok.com/@life/video/111",
                    "title": "unrelated old post",
                    "timestamp": 100,
                },
                {
                    "id": "222",
                    "url": "https://www.tiktok.com/@life/video/222",
                    "title": "Exact caption first line and more",
                    "timestamp": 205,
                },
            ]
        }

        def runner(*_args, **_kwargs):
            return subprocess.CompletedProcess([], 0, json.dumps(payload), "")

        url = postiz_video.resolve_profile_release_url(
            "https://www.tiktok.com/@life",
            "Exact caption first line\nand more",
            posted_after=200,
            runner=runner,
        )
        self.assertEqual(url, "https://www.tiktok.com/@life/video/222")

    def test_profile_resolution_rejects_old_or_caption_mismatched_entries(self):
        payload = {
            "entries": [
                {
                    "id": "111",
                    "url": "https://www.tiktok.com/@life/video/111",
                    "title": "Exact caption first line",
                    "timestamp": 100,
                },
                {
                    "id": "222",
                    "url": "https://www.tiktok.com/@life/video/222",
                    "title": "wrong current post",
                    "timestamp": 205,
                },
            ]
        }

        def runner(*_args, **_kwargs):
            return subprocess.CompletedProcess([], 0, json.dumps(payload), "")

        self.assertIsNone(
            postiz_video.resolve_profile_release_url(
                "https://www.tiktok.com/@life",
                "Exact caption first line",
                posted_after=200,
                runner=runner,
            )
        )


if __name__ == "__main__":
    unittest.main()
