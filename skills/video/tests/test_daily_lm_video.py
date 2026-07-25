#!/usr/bin/env python3
import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / "daily-lm-video"
MODULE = SKILL / "generate.py"
BANK = SKILL / "creative-bank.jsonl"
EXPECTED_IDS = [f"A{i:02d}" for i in range(1, 7)] + [f"B{i:02d}" for i in range(1, 8)] + [f"C{i:02d}" for i in range(1, 4)]


def executable(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def sources(root: Path) -> dict[str, Path]:
    result = {}
    for name in ("call.mp3", "stock.mp4", "proof.png"):
        result[name] = root / name
        result[name].write_bytes(b"fixture")
    result["whisper.ass"] = root / "whisper.ass"
    result["whisper.ass"].write_text(
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname\n"
        "Style: Default,Arial\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,REAL CALL\n",
        encoding="utf-8",
    )
    return result


def fake_media_tools(root: Path, ffmpeg_rc: int = 0) -> tuple[Path, Path]:
    ffmpeg = executable(
        root / "ffmpeg",
        f"#!/usr/bin/env bash\nset -eu\n[ {ffmpeg_rc} -eq 0 ] || exit {ffmpeg_rc}\nout=${{@: -1}}\nprintf render >\"$out\"\n",
    )
    ffprobe = executable(
        root / "ffprobe",
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' '{\"streams\":[{\"codec_type\":\"video\",\"codec_name\":\"h264\",\"width\":1080,\"height\":1920},"
        "{\"codec_type\":\"audio\",\"codec_name\":\"aac\"}],\"format\":{\"duration\":\"34.656\"}}'\n",
    )
    return ffmpeg, ffprobe


def invoke(root: Path, state: Path, day: str, ffmpeg_rc: int = 0) -> subprocess.CompletedProcess:
    src = sources(root)
    ffmpeg, ffprobe = fake_media_tools(root, ffmpeg_rc)
    return subprocess.run(
        [
            sys.executable,
            str(MODULE),
            "--bank", str(BANK),
            "--state", str(state),
            "--output-dir", str(root / "renders"),
            "--call-audio", str(src["call.mp3"]),
            "--stock", str(src["stock.mp4"]),
            "--telegram-proof", str(src["proof.png"]),
            "--whisper-ass", str(src["whisper.ass"]),
            "--ffmpeg-bin", str(ffmpeg),
            "--ffprobe-bin", str(ffprobe),
            "--date", day,
        ],
        text=True,
        capture_output=True,
    )


class DailyLmVideoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("daily_lm_video", MODULE)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_canonical_bank_has_exactly_sixteen_rows(self):
        rows = self.module.load_bank(BANK)
        self.assertEqual([row["id"] for row in rows], EXPECTED_IDS)
        core = {"id", "pain", "moment", "punchline", "material_hint"}
        english = {"pain_en", "moment_en", "punchline_en"}
        # Every creative must carry both languages: English runs on TikTok, Japanese on Instagram.
        self.assertTrue(all(core.issubset(set(row)) and english.issubset(set(row)) for row in rows))

    def test_rotation_is_unused_first_then_starts_second_cycle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state.jsonl"
            start = date(2026, 7, 1)
            selected = []
            for offset in range(17):
                result = invoke(root, state, str(start + timedelta(days=offset)))
                self.assertEqual(result.returncode, 0, result.stderr)
                selected.append(json.loads(result.stdout)["selected_id"])
            self.assertEqual(selected[:16], EXPECTED_IDS)
            self.assertEqual(selected[16], "A01")
            self.assertEqual(json.loads(state.read_text(encoding="utf-8").splitlines()[-1])["cycle"], 2)

    def test_same_day_is_idempotent_and_render_failure_is_not_ledgered(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state.jsonl"
            first = invoke(root, state, "2026-08-01")
            self.assertEqual(first.returncode, 0, first.stderr)
            before = state.read_text(encoding="utf-8")
            retry = invoke(root, state, "2026-08-01")
            self.assertEqual(retry.returncode, 0, retry.stderr)
            self.assertEqual(state.read_text(encoding="utf-8"), before)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state.jsonl"
            failed = invoke(root, state, "2026-08-02", ffmpeg_rc=9)
            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse(state.exists())

    def test_whisper_derivative_excludes_old_creative_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.ass"
            destination = root / "speech.ass"
            source.write_text(
                "[Events]\n"
                "Dialogue: 0,0:00:00.00,0:00:05.00,Hero,,0,0,0,,OLD CREATIVE\n"
                "Dialogue: 0,0:00:05.00,0:00:07.00,Caption,,0,0,0,,REAL CALL\n",
                encoding="utf-8",
            )
            self.module.write_whisper_only_ass(source, destination, offset_seconds=5)
            derived = destination.read_text(encoding="utf-8")
            self.assertIn("REAL CALL", derived)
            self.assertNotIn("OLD CREATIVE", derived)
            self.assertIn("0:00:10.00,0:00:12.00", derived)

    def test_validation_rejects_video_longer_than_forty_seconds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "render.mp4"
            output.write_bytes(b"render")
            ffprobe = executable(
                root / "ffprobe",
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' '{\"streams\":[{\"codec_type\":\"video\",\"codec_name\":\"h264\",\"width\":1080,\"height\":1920},"
                "{\"codec_type\":\"audio\",\"codec_name\":\"aac\"}],\"format\":{\"duration\":\"45\"}}'\n",
            )
            with self.assertRaisesRegex(RuntimeError, "outside 20-40 seconds"):
                self.module.validate_render(output, str(ffprobe))


if __name__ == "__main__":
    unittest.main()
