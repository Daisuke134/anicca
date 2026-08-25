#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
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

    def test_instagram_carousel_payload_preserves_order_and_native_post_settings(self):
        payload = postiz_video.build_payload(
            integration="cmq3sq7mc000eqp0y7azfm8yk",
            caption="メンタルが勝手に安定する\n口癖５選",
            title="Life Manager",
            upload_ids=["upload-1", "upload-2", "upload-3"],
            upload_paths=["https://uploads.example/1.jpg", "https://uploads.example/2.jpg", "https://uploads.example/3.jpg"],
            now_iso="2026-08-26T07:30:00.000Z",
            platform="instagram",
        )
        post = payload["posts"][0]
        self.assertEqual(post["integration"]["id"], "cmq3sq7mc000eqp0y7azfm8yk")
        self.assertEqual(post["settings"], {
            "__type": "instagram-standalone",
            "post_type": "post",
            "is_trial_reel": False,
            "collaborators": [],
        })
        self.assertEqual([item["id"] for item in post["value"][0]["image"]], ["upload-1", "upload-2", "upload-3"])
        self.assertEqual([item["path"] for item in post["value"][0]["image"]], [
            "https://uploads.example/1.jpg", "https://uploads.example/2.jpg", "https://uploads.example/3.jpg",
        ])

    def test_carousel_payload_rejects_short_or_video_image_mix(self):
        with self.assertRaises(postiz_video.PostizError):
            postiz_video.build_payload(
                integration="i", caption="caption", title="title",
                upload_ids=["upload-1"], upload_paths=["https://uploads.example/1.jpg"],
                now_iso="2026-08-26T07:30:00.000Z", platform="instagram",
            )
        with self.assertRaises(postiz_video.PostizError):
            postiz_video.build_payload(
                integration="i", caption="caption", title="title",
                upload_ids=["upload-1", "upload-2"], upload_paths=["1.jpg", "2.jpg"],
                now_iso="2026-08-26T07:30:00.000Z", platform="tiktok",
            )

    def test_image_upload_rejects_empty_and_non_jpeg_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            empty = Path(directory) / "empty.jpg"
            empty.write_bytes(b"")
            with self.assertRaises(postiz_video.PostizError):
                postiz_video.upload_image(empty, "token")
            png = Path(directory) / "image.png"
            png.write_bytes(b"\x89PNG\r\n")
            with self.assertRaises(postiz_video.PostizError):
                postiz_video.upload_image(png, "token")

    def test_carousel_caption_reader_preserves_raw_utf8_while_video_reader_trims(self):
        with tempfile.TemporaryDirectory() as directory:
            caption_file = Path(directory) / "caption.txt"
            raw_caption = " \nExact caption\n  \n"
            caption_file.write_text(raw_caption, encoding="utf-8")
            self.assertEqual(postiz_video.read_caption(caption_file, carousel=True), raw_caption)
            self.assertEqual(postiz_video.read_caption(caption_file, carousel=False), raw_caption.strip())

    def test_direct_carousel_url_only_accepts_instagram_post(self):
        self.assertTrue(postiz_video._valid_instagram_carousel_url("https://www.instagram.com/p/ABC_123/"))
        self.assertFalse(postiz_video._valid_instagram_carousel_url("https://www.instagram.com/reel/ABC_123/"))
        self.assertFalse(postiz_video._valid_instagram_carousel_url("https://www.instagram.com/@ani.cca1234"))
        self.assertFalse(postiz_video._valid_instagram_carousel_url("https://www.instagram.com/p/12345678901234567890/"))
        self.assertTrue(postiz_video._valid_public_url("instagram", "https://www.instagram.com/reel/ABC_123/"))

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

    def test_published_exact_video_state_is_provider_reconciled(self):
        self.assertTrue(postiz_video.is_reconciled_state({
            "state": "PUBLISHED",
            "post_url": "https://www.tiktok.com/@life/video/123",
        }))
        self.assertFalse(postiz_video.is_reconciled_state({
            "state": "PUBLISHED",
            "post_url": "https://www.tiktok.com/@life",
        }))

    def test_find_post_rejects_published_without_public_url(self):
        with self.assertRaises(postiz_video.PostizError):
            postiz_video.find_post([{"id": "p", "state": "PUBLISHED"}], "p")

    def test_find_post_does_not_derive_tiktok_url_from_internal_release_id(self):
        row = {
            "id": "post-1",
            "state": "PUBLISHED",
            "releaseURL": "https://www.tiktok.com/@life.manager",
            "releaseId": "v_pub_file~v2-1.7999999999999999999",
        }
        self.assertEqual(
            postiz_video.find_post([row], "post-1"),
            {"state": "PUBLISHED", "post_url": "https://www.tiktok.com/@life.manager"},
        )

    def test_caption_only_provider_effect_never_reconciles_a_different_video(self):
        rows = {
            "posts": [{
                "id": "post-1",
                "state": "PUBLISHED",
                "content": "Exact caption\n#line",
                "integration": {"id": "integration-1"},
                "releaseURL": "https://www.tiktok.com/@life/video/222",
                "releaseId": "internal-provider-id",
            }],
        }
        self.assertIsNone(
            postiz_video.find_existing_post(
                rows,
                integration="integration-1",
                caption="Exact caption\n#line",
                video_sha256="b" * 64,
            ),
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
                browser_resolver=lambda *_args, **_kwargs: None,
            )
        )

    def test_profile_only_post_falls_back_to_browser_caption_join(self):
        calls = []

        def browser(profile_url, caption, *, posted_after, caption_prefix):
            calls.append((profile_url, caption, posted_after, caption_prefix))
            return "https://www.tiktok.com/@honne_reveal/video/7676388327427149077"

        result = postiz_video.resolve_profile_release_url(
            "https://www.tiktok.com/@honne_reveal",
            "someone tell me\nthis is illegal",
            posted_after=1_777_000_000,
            runner=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", ""),
            browser_resolver=browser,
        )
        self.assertEqual(result, "https://www.tiktok.com/@honne_reveal/video/7676388327427149077")
        self.assertEqual(calls[0][0], "https://www.tiktok.com/@honne_reveal")
        self.assertEqual(calls[0][3], "someone tell me this is")

    def test_profile_caption_join_rejects_an_old_duplicate(self):
        rows = [
            {"href": "https://www.tiktok.com/@life/video/7676852644698262791", "alt": "Exact caption #tag"},
            {"href": "https://www.tiktok.com/@life/video/7676422253638176020", "alt": "Exact caption #tag"},
        ]
        self.assertEqual(
            postiz_video._matching_profile_url(rows, "exact caption", 1_787_406_536),
            "https://www.tiktok.com/@life/video/7676852644698262791",
        )
        self.assertIsNone(postiz_video._matching_profile_url(rows[1:], "exact caption", 1_787_406_536))


if __name__ == "__main__":
    unittest.main()
