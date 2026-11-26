#!/usr/bin/env python3
"""Synthetic-only regressions for audio evidence vs WAV container integrity."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

from audit_voice_wav_evidence import audit, pcm_metrics

SETTINGS = dict(model_version="UNVERIFIED-FIXTURE", skill_blob_sha="fixture",
                script_blob_sha="fixture", voice_mode="test",
                mic_setup_id="test-mic", speaker_output_id="test-output")


class SilentDialogueEvidenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def make_wav(self, name, samples):
        path = self.root / name
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(struct.pack("<" + "h" * len(samples), *samples))
        return path

    def record(self, file, trial, source_kind):
        return dict(trial_id=trial, wav_path=file.name,
                    sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                    source_kind=source_kind, **SETTINGS)

    def check(self, records):
        manifest = self.root / "manifest.jsonl"
        manifest.write_text("".join(json.dumps(x) + "\n" for x in records),
                            encoding="utf-8")
        return audit(manifest), manifest

    def test_real_silence_rejected_as_dialogue_evidence_but_valid_wav(self):
        p = self.make_wav("silent.wav", [0] * 8000)
        out, _ = self.check([self.record(p, "r1", "claimed_real_rehearsal")])
        self.assertEqual(out["wav_byte_integrity"], "PASS")
        self.assertEqual(out["claimed_rehearsal_audio_evidence"], "FAIL")
        self.assertEqual(out["items"][0]["dialogue_evidence"], "DIGITAL_SILENCE_INVALID")
        self.assertEqual(out["audio_origin_authenticity"], "NOT_VERIFIED")
        self.assertEqual(out["voice_reproducibility"], "NOT_MEASURED")

    def test_nonsilent_real_never_claims_speech_verified(self):
        p = self.make_wav("nonzero.wav", [100, -100] * 4000)
        out, _ = self.check([self.record(p, "r1", "claimed_real_rehearsal")])
        self.assertEqual(out["claimed_rehearsal_audio_evidence"],
                         "NEEDS_SPEECH_VERIFICATION")
        self.assertEqual(out["items"][0]["dialogue_evidence"], "UNVERIFIED_SPEECH")
        self.assertEqual(out["phone_ai_role_understanding"], "NOT_MEASURED")

    def test_synthetic_silence_is_fixture_not_real_rehearsal(self):
        p = self.make_wav("synthetic.wav", [0] * 100)
        out, _ = self.check([self.record(p, "s1", "synthetic_fixture")])
        self.assertEqual(out["claimed_rehearsal_audio_evidence"], "NOT_MEASURED")
        self.assertEqual(out["items"][0]["dialogue_evidence"], "NOT_APPLICABLE")
        self.assertTrue(out["items"][0]["sample_domain_metrics"]["digital_silence"])

    def test_mixed_real_set_fails_evidence_when_one_is_silent(self):
        a = self.make_wav("a.wav", [100, 200] * 4000)
        b = self.make_wav("b.wav", [0] * 8000)
        out, _ = self.check([self.record(a, "r1", "claimed_real_rehearsal"),
                             self.record(b, "r2", "claimed_real_rehearsal")])
        self.assertEqual(out["wav_byte_integrity"], "PASS")
        self.assertEqual(out["claimed_rehearsal_audio_evidence"], "FAIL")
        self.assertEqual(out["verified_wav_count"], 2)

    def test_no_claimed_real_audio_is_unmeasured(self):
        out, _ = self.check([])
        self.assertEqual(out["claimed_rehearsal_audio_evidence"], "NOT_MEASURED")

    def test_pcm_nonzero_fraction_remains_diagnostic_not_speech_detector(self):
        p = self.make_wav("click.wav", [0] * 7999 + [1])
        value = pcm_metrics(p)
        self.assertEqual(value["nonzero_sample_fraction"], 0.000125)
        out, _ = self.check([self.record(p, "r1", "claimed_real_rehearsal")])
        self.assertEqual(out["claimed_rehearsal_audio_evidence"],
                         "NEEDS_SPEECH_VERIFICATION")

    def test_cli_silent_real_exits_nonzero_without_mislabeling_wav_bytes(self):
        p = self.make_wav("silent.wav", [0] * 8000)
        _, manifest = self.check([self.record(p, "r1", "claimed_real_rehearsal")])
        report = self.root / "out.json"
        code = subprocess.run([sys.executable,
                               str(Path(__file__).with_name("audit_voice_wav_evidence.py")),
                               "--manifest", str(manifest), "--output", str(report)],
                              capture_output=True, text=True).returncode
        self.assertEqual(code, 1)
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(data["wav_byte_integrity"], "PASS")
        self.assertEqual(data["claimed_rehearsal_audio_evidence"], "FAIL")


if __name__ == "__main__":
    unittest.main()
