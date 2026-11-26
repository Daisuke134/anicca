#!/usr/bin/env python3
"""PCM duplication regressions, using synthetic signals only; no voice trials."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import wave

from audit_voice_wav_evidence import audit, pcm_metrics

CONFIG = {
    "model_version": "SYNTHETIC", "skill_blob_sha": "fixture-skill",
    "script_blob_sha": "fixture-script", "voice_mode": "fixture",
    "mic_setup_id": "fixture-mic", "speaker_output_id": "fixture-output",
}


class PCMReusedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def wav(self, name, samples, rate=8000):
        p = self.root / name
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(struct.pack("<" + "h" * len(samples), *samples))
        return p

    def with_list_chunk(self, source, name):
        """Different valid RIFF container, identical decoded 16-bit PCM."""
        data = source.read_bytes()
        self.assertEqual(data[36:40], b"data")
        chunk = b"LIST" + struct.pack("<I", 4) + b"INFO"
        new_size = struct.unpack("<I", data[4:8])[0] + len(chunk)
        dest = self.root / name
        dest.write_bytes(data[:4] + struct.pack("<I", new_size) + data[8:36] + chunk + data[36:])
        return dest

    def row(self, p, tid):
        return {
            "trial_id": tid, "wav_path": p.name,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "source_kind": "synthetic_fixture", **CONFIG,
        }

    def run_audit(self, rows):
        manifest = self.root / "manifest.jsonl"
        manifest.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        return audit(manifest)

    def test_same_samples_different_valid_headers_flagged(self):
        a = self.wav("a.wav", [7, -9, 11, -13] * 250)
        b = self.with_list_chunk(a, "b.wav")
        self.assertNotEqual(hashlib.sha256(a.read_bytes()).hexdigest(), hashlib.sha256(b.read_bytes()).hexdigest())
        result = self.run_audit([self.row(a, "one"), self.row(b, "two")])
        self.assertEqual(result["wav_byte_integrity"], "FAIL")
        self.assertIn("duplicate_decoded_pcm", result["items"][1]["issues"])
        self.assertNotIn("duplicate_audio_bytes", result["items"][1]["issues"])

    def test_pcm_fingerprint_same_despite_header_metadata(self):
        a = self.wav("a.wav", [7, 10] * 120)
        b = self.with_list_chunk(a, "b.wav")
        self.assertEqual(pcm_metrics(a)["pcm_sha256"], pcm_metrics(b)["pcm_sha256"])

    def test_pcm_fingerprint_changes_with_samples(self):
        a = self.wav("a.wav", [7, 10] * 120)
        b = self.wav("b.wav", [8, 10] * 120)
        self.assertNotEqual(pcm_metrics(a)["pcm_sha256"], pcm_metrics(b)["pcm_sha256"])
        result = self.run_audit([self.row(a, "one"), self.row(b, "two")])
        self.assertEqual(result["wav_byte_integrity"], "PASS")

    def test_same_pcm_different_declared_rate_still_flagged(self):
        a = self.wav("a.wav", [7, 10] * 120, 8000)
        b = self.wav("b.wav", [7, 10] * 120, 16000)
        result = self.run_audit([self.row(a, "one"), self.row(b, "two")])
        self.assertIn("duplicate_decoded_pcm", result["items"][1]["issues"])
        self.assertEqual(result["repeated_config_consistency"], "DIFFERENT_CONFIGS")

    def test_distinct_synthetic_wavs_never_claim_real_voice_success(self):
        a = self.wav("a.wav", [1, 2] * 100)
        result = self.run_audit([self.row(a, "one")])
        self.assertEqual(result["wav_byte_integrity"], "PASS")
        self.assertEqual(result["audio_origin_authenticity"], "NOT_VERIFIED")
        self.assertEqual(result["voice_reproducibility"], "NOT_MEASURED")
        self.assertEqual(result["audience_laughter"], "NOT_MEASURED")


if __name__ == "__main__":
    unittest.main()
