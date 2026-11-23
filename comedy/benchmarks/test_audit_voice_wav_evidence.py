#!/usr/bin/env python3
"""Synthetic-only regression tests. No real stage recording is supplied."""

import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import wave

from audit_voice_wav_evidence import audit, pcm_metrics

CONFIG = dict(model_version="SYNTHETIC", skill_blob_sha="skill",
              script_blob_sha="script", voice_mode="test",
              mic_setup_id="test-mic", speaker_output_id="test-speaker")


class VoiceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def wav(self, name, samples, rate=8000):
        path = self.root / name
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(struct.pack("<" + "h" * len(samples), *samples))
        return path

    def row(self, path, tid, **other):
        return dict(trial_id=tid, wav_path=path.name,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    source_kind="synthetic_fixture", **CONFIG) | other

    def audit_rows(self, rows):
        path = self.root / "manifest.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        return audit(path)

    def test_empty_manifest_is_unmeasured(self):
        r = self.audit_rows([])
        self.assertEqual(r["wav_byte_integrity"], "NOT_MEASURED")
        self.assertEqual(r["voice_reproducibility"], "NOT_MEASURED")

    def test_synthetic_file_digest_and_pcm_metrics(self):
        p = self.wav("tone.wav", [1000, -1000] * 4000)
        r = self.audit_rows([self.row(p, "synthetic-1")])
        self.assertEqual(r["verified_wav_count"], 1)
        self.assertEqual(r["wav_byte_integrity"], "PASS")
        self.assertEqual(r["voice_reproducibility"], "NOT_MEASURED")
        self.assertEqual(r["items"][0]["sample_domain_metrics"]["duration_s"], 1.0)

    def test_sha_mismatch_detected(self):
        p = self.wav("tone.wav", [1000] * 80)
        row = self.row(p, "one")
        row["sha256"] = "a" * 64
        r = self.audit_rows([row])
        self.assertIn("sha256_mismatch", r["items"][0]["issues"])

    def test_duplicate_recording_never_counts_as_independent(self):
        a = self.wav("a.wav", [1500] * 80)
        b = self.wav("b.wav", [1500] * 80)
        r = self.audit_rows([self.row(a, "one"), self.row(b, "two")])
        self.assertIn("duplicate_audio_bytes", r["items"][1]["issues"])

    def test_digital_silence_is_observed_not_performance_success(self):
        p = self.wav("silence.wav", [0] * 80)
        r = self.audit_rows([self.row(p, "one")])
        self.assertTrue(r["items"][0]["sample_domain_metrics"]["digital_silence"])
        self.assertIsNone(r["items"][0]["sample_domain_metrics"]["rms_dbfs"])
        self.assertEqual(r["back_row_intelligibility"], "NOT_MEASURED")

    def test_sample_clipping_detected(self):
        p = self.wav("clip.wav", [32767, -32768] * 80)
        self.assertEqual(pcm_metrics(p)["sample_clip_fraction"], 1.0)

    def test_mismatched_voice_configs_are_not_comparable(self):
        a = self.wav("a.wav", [1] * 80)
        b = self.wav("b.wav", [2] * 80)
        row = self.row(b, "two")
        row["mic_setup_id"] = "different"
        r = self.audit_rows([self.row(a, "one"), row])
        self.assertEqual(r["repeated_config_consistency"], "DIFFERENT_CONFIGS")

    def test_different_actual_sample_rates_are_not_same_conditions(self):
        a = self.wav("a.wav", [1] * 80, rate=8000)
        b = self.wav("b.wav", [2] * 80, rate=16000)
        result = self.audit_rows([self.row(a, "one"), self.row(b, "two")])
        self.assertEqual(result["wav_byte_integrity"], "PASS")
        self.assertEqual(result["repeated_config_consistency"], "DIFFERENT_CONFIGS")

    def test_path_traversal_rejected(self):
        p = self.wav("tone.wav", [400] * 80)
        row = self.row(p, "one")
        row["wav_path"] = "../tone.wav"
        r = self.audit_rows([row])
        self.assertIn("path_outside_manifest_dir", r["items"][0]["issues"])

    def test_missing_config_rejected(self):
        p = self.wav("tone.wav", [400] * 80)
        row = self.row(p, "one")
        row.pop("model_version")
        r = self.audit_rows([row])
        self.assertIn("missing_config:model_version", r["items"][0]["issues"])

    def test_invalid_pcm_rejected(self):
        p = self.root / "bad.wav"
        p.write_bytes(b"not a wav")
        r = self.audit_rows([self.row(p, "one")])
        self.assertTrue(any(s.startswith("invalid_wav:") for s in r["items"][0]["issues"]))

    def test_real_source_field_is_not_proof_of_authenticity(self):
        p = self.wav("tone.wav", [1000] * 80)
        row = self.row(p, "one")
        row["source_kind"] = "claimed_real_rehearsal"
        r = self.audit_rows([row])
        self.assertEqual(r["audio_origin_authenticity"], "NOT_VERIFIED")
        self.assertEqual(r["audience_laughter"], "NOT_MEASURED")


if __name__ == "__main__":
    unittest.main()
