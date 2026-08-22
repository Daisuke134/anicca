#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "canonical-renderer" / "render.py"


class CanonicalRendererTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("canonical_renderer", MODULE)
        cls.renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.renderer)

    def test_rejects_secret_like_listing_text(self):
        with self.assertRaisesRegex(ValueError, "secret or PII"):
            self.renderer.validate_public_text("Try sk-live-1234567890abcdefghijklmnop")

    def test_probe_contract_requires_vertical_bt709_audio(self):
        valid = {
            "streams": [
                {
                    "codec_type": "video", "codec_name": "h264", "width": 1080,
                    "height": 1920, "pix_fmt": "yuv420p", "color_space": "bt709",
                    "color_transfer": "bt709", "color_primaries": "bt709",
                },
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
            ],
            "format": {"duration": "8.0"},
        }
        self.assertEqual(self.renderer.validate_probe(valid), 8.0)
        invalid = json.loads(json.dumps(valid))
        invalid["streams"][0]["pix_fmt"] = "yuv444p"
        with self.assertRaisesRegex(RuntimeError, "yuv420p"):
            self.renderer.validate_probe(invalid)

    def test_ass_captions_stay_inside_vertical_safe_area(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "captions.ass"
            self.renderer.write_ass(
                path,
                "Instant interview themes",
                "Turn calls into evidence",
                "INPUT: Friday chasing missing receipts",
                "OUTPUT: Missing receipts are the repeated pain",
                8,
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn("PlayResX: 1080", text)
            self.assertIn("PlayResY: 1920", text)
            self.assertIn("MarginL, MarginR, MarginV", text)
            self.assertIn(",96,96,260,", text)
            self.assertIn("INPUT", text)
            self.assertIn("VERIFIED OUTPUT", text)

    def test_demonstration_rejects_generic_or_unverifiable_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "case.md"
            source.write_text("verified case", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "distinct input and output"):
                self.renderer.validate_demonstration(source, "generic money b-roll", "generic money b-roll")
            with self.assertRaisesRegex(FileNotFoundError, "demonstration source"):
                self.renderer.validate_demonstration(source.with_name("missing.md"), "input notes", "ranked memo")

    def test_demonstration_records_source_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "case.md"
            source.write_text("verified case", encoding="utf-8")
            evidence = self.renderer.validate_demonstration(source, "input notes", "ranked memo")
            self.assertEqual(evidence["mode"], "input_output")
            self.assertTrue(evidence["source_sha256"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
