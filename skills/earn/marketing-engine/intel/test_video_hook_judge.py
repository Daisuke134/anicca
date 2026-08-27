import json
import hashlib
import importlib.util
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

from video_hook_judge import HookJudgmentError, judge_pending_video_hooks


OBSERVED = "2026-08-01T15:20:00Z"
URL = "https://www.tiktok.com/@itsyangmun/video/7609309883912965390"


def hook(text="Your room can quietly teach your courage to shrink."):
    return {
        "schema_version": "marketing.hook.v1",
        "id": "hook.ebook-en.room-shrinks-courage.v1",
        "text": text,
        "language": "en",
        "product_ids": ["ebook-en"],
        "source_type": "video",
        "source_url": URL,
        "source_null_reason": None,
        "captured_at": OBSERVED,
        "provenance": "live_observed",
        "rubric": {"hook": 8, "emotional_peak": 6, "conflict": 5,
                   "quotability": 7, "practical_value": 8, "total": 34},
        "status": "active",
        "ewma_score": None,
        "observations": 0,
        "evidence_url": URL,
        "evidence_null_reason": None,
    }


def fixture(root: Path):
    intel = root / "intel"
    intel.mkdir()
    (intel / "hook-library.jsonl").write_text("", encoding="utf-8")
    evidence = root / "capture"
    evidence.mkdir()
    media = evidence / "source.mp4"
    media.write_bytes(b"video")
    transcript = evidence / "transcript.json"
    transcript.write_text(json.dumps({
        "language": "en",
        "text": "Staying at home too much is quietly ruining your life. It makes your world smaller.",
        "segments": [{"start": 0.0, "end": 3.8,
                      "text": "Staying at home too much is quietly ruining your life."}],
    }), encoding="utf-8")
    row = {
        "schema_version": "marketing.video-transcript.v1",
        "id": "transcript.tiktok.7609309883912965390.v1",
        "source_id": "video.tiktok.itsyangmun.en",
        "native_id": "7609309883912965390",
        "native_url": URL,
        "language": "en",
        "product_ids": ["ebook-en"],
        "observed_at": OBSERVED,
        "media_path": str(media), "media_bytes": 5,
        "media_sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
        "transcript_path": str(transcript),
        "transcript_sha256": hashlib.sha256(transcript.read_bytes()).hexdigest(),
        "segment_count": 1, "transcription_engine": "openai-whisper",
        "transcription_model": "base",
    }
    (intel / "video-transcripts.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    return intel


class VideoHookJudgeTest(unittest.TestCase):
    def test_lm_exposes_video_judge_command(self):
        lm_path = Path(__file__).resolve().parent.parent / "bin" / "lm"
        spec = importlib.util.spec_from_loader("marketing_lm_video_judge",
                                               SourceFileLoader("marketing_lm_video_judge", str(lm_path)))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp, \
                mock.patch.object(module.video_hook_judge, "judge_pending_video_hooks") as run:
            root = Path(temp)
            run.return_value = {"status": "success", "run_id": "fixture"}
            rc = module.main(["intel", "video-judge", "--intel-root", str(root / "intel"),
                              "--evidence-root", str(root / "evidence")])
            self.assertEqual(rc, 0)
            run.assert_called_once()

    def test_accepts_original_grounded_hook_and_writes_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intel = fixture(root)
            result = judge_pending_video_hooks(
                intel, root / "judge", judge=lambda manifest: {"hooks": [hook()]},
                run_id="judge-1", observed_at=OBSERVED)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["accepted_hooks"], 1)
            stored = json.loads((intel / "hook-library.jsonl").read_text())
            self.assertEqual(stored["text"], hook()["text"])
            provenance = json.loads((intel / "hook-evidence.jsonl").read_text())
            self.assertEqual(provenance["hook_id"], stored["id"])
            self.assertEqual(provenance["transcript_path"],
                             json.loads((intel / "video-transcripts.jsonl").read_text())["transcript_path"])
            judged = json.loads((intel / "video-hook-judgments.jsonl").read_text())
            self.assertEqual(judged["transcript_id"], "transcript.tiktok.7609309883912965390.v1")

    def test_rejects_verbatim_competitor_hook_and_keeps_pending(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intel = fixture(root)
            copied = hook("Staying at home too much is quietly ruining your life.")
            with self.assertRaisesRegex(HookJudgmentError, "verbatim"):
                judge_pending_video_hooks(
                    intel, root / "judge", judge=lambda manifest: {"hooks": [copied]},
                    run_id="judge-copy", observed_at=OBSERVED)
            self.assertEqual((intel / "hook-library.jsonl").read_text(), "")
            self.assertFalse((intel / "video-hook-judgments.jsonl").exists())

    def test_replay_has_no_pending_transcript(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intel = fixture(root)
            first = judge_pending_video_hooks(
                intel, root / "judge", judge=lambda manifest: {"hooks": [hook()]},
                run_id="judge-1", observed_at=OBSERVED)
            second = judge_pending_video_hooks(
                intel, root / "judge", judge=lambda manifest: self.fail("must not call judge"),
                run_id="judge-2", observed_at=OBSERVED)
            self.assertEqual(first["accepted_hooks"], 1)
            self.assertEqual(second["status"], "skipped")
            self.assertEqual(second["pending_transcripts"], 0)

    def test_rejects_rubric_total_that_does_not_sum(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            intel = fixture(root)
            bad = hook()
            bad["rubric"]["total"] = 99
            with self.assertRaisesRegex(HookJudgmentError, "rubric total"):
                judge_pending_video_hooks(
                    intel, root / "judge", judge=lambda manifest: {"hooks": [bad]},
                    run_id="judge-bad", observed_at=OBSERVED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
