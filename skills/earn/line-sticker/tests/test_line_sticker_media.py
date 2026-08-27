"""Contract tests for the bounded LINE sticker media pipeline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT))
import line_sticker_media as MODULE  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_executable(path: Path, source: str) -> Path:
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _write_plan_model(path: Path) -> Path:
    return _write_executable(
        path,
        """
        #!/usr/bin/env python3
        import json
        from pathlib import Path
        import sys
        request = json.load(sys.stdin)
        count = Path(__file__).with_suffix('.count')
        count.write_text(str(int(count.read_text() or '0') + 1) if count.exists() else '1')
        if request['mode'] == 'plan':
            motions = []
            for batch in range(1, 7):
                for position in range(1, 11):
                    number = (batch - 1) * 10 + position
                    motions.append({
                        'motion_id': f'motion-{number:02d}',
                        'batch': batch,
                        'position': position,
                        'intent': f'reaction {number}',
                        'action': f'performs clear motion {number}',
                        'provider_prompt': f'animate motion {number}',
                        'duration_ms': 500,
                    })
            print(json.dumps({
                'version': 1, 'mode': 'plan', 'set_id': request['set_id'],
                'character_id': request['character_id'],
                'character_anchors': ['round blue ears', 'white face', 'short tail'],
                'motions': motions,
            }))
        else:
            candidates = json.loads(Path(request['selection_input_path']).read_text())['candidates']
            valid = [item for item in candidates if not item['errors']]
            chosen = valid[:24]
            print(json.dumps({
                'version': 1, 'mode': 'select',
                'cover_motion_id': chosen[0]['motion_id'],
                'selections': [
                    {'position': index, 'motion_id': item['motion_id'], 'reason': 'observed clear motion'}
                    for index, item in enumerate(chosen, 1)
                ],
            }))
        """,
    )


def _write_provider(path: Path) -> Path:
    return _write_executable(
        path,
        """
        #!/usr/bin/env python3
        import hashlib
        import json
        from pathlib import Path
        import subprocess
        import sys
        request = json.load(sys.stdin)
        count = Path(__file__).with_suffix('.count')
        count.write_text(str(int(count.read_text() or '0') + 1) if count.exists() else '1')
        template = Path(sys.argv[1])
        batch = int(request['batch'])
        source = template.parent / f'source-{batch:02d}.mp4'
        subprocess.run([
            'ffmpeg', '-y', '-v', 'error', '-i', str(template),
            '-vf', f'drawbox=x={batch}:y=0:w=1:h=1:color=blue:t=fill',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-an', str(source),
        ], check=True)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        segments = [
            {'motion_id': motion['motion_id'], 'start_ms': (index - 1) * 500, 'end_ms': index * 500}
            for index, motion in enumerate(request['motions'], 1)
        ]
        print(json.dumps({
            'request_id': f'request-{batch}', 'batch': batch,
            'provider': 'fixture-provider', 'model': 'fixture-model',
            'quoted_cost_usd': '0.01', 'acknowledged': True,
            'video_path': str(source), 'video_sha256': digest, 'segments': segments,
        }))
        """,
    )


def _write_select_model(path: Path) -> Path:
    return _write_executable(
        path,
        """
        #!/usr/bin/env python3
        import json
        from pathlib import Path
        import sys
        request = json.load(sys.stdin)
        count = Path(__file__).with_suffix('.count')
        count.write_text(str(int(count.read_text() or '0') + 1) if count.exists() else '1')
        candidates = json.loads(Path(request['selection_input_path']).read_text())['candidates']
        valid = [item for item in candidates if not item['errors']]
        chosen = valid[:24]
        print(json.dumps({
            'version': 1, 'mode': 'select',
            'cover_motion_id': chosen[0]['motion_id'],
            'selections': [
                {'position': index, 'motion_id': item['motion_id'], 'reason': 'observed clear motion'}
                for index, item in enumerate(chosen, 1)
            ],
        }))
        """,
    )


def _make_character(root: Path) -> Path:
    path = root / "character.png"
    path.write_bytes(b"character-fixture")
    return path


def _make_video(root: Path) -> Path:
    path = root / "template.mp4"
    completed = subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
            "-i", "nullsrc=size=64x64:rate=10,geq=r='if(between(X,10+N,30+N)*between(Y,16,48),255,0)':g='if(between(X,10+N,30+N)*between(Y,16,48),0,255)':b=0",
            "-t", "5",
            "-pix_fmt", "yuv420p", "-an", str(path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode:
        raise AssertionError(completed.stderr.decode(errors="replace"))
    return path


class LineStickerMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="line-sticker-media-test-")
        self.root = Path(self.tempdir.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.character = _make_character(self.root)
        self.plan_model = _write_plan_model(self.root / "plan-model.py")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _plan(self) -> dict[str, object]:
        return MODULE.plan(self.character, [sys.executable, str(self.plan_model)], self.work, "set-1", "char-1")

    def test_module_exposes_the_four_cli_operations(self) -> None:
        self.assertTrue(callable(MODULE.plan))
        self.assertTrue(callable(MODULE.convert))
        self.assertTrue(callable(MODULE.select))
        self.assertTrue(callable(MODULE.package))

    def test_plan_writes_sixty_records_and_replays_without_model_call(self) -> None:
        first = self._plan()
        second = self._plan()
        self.assertEqual(first["status"], "ready")
        self.assertEqual(second["reason"], "replayed")
        payload = json.loads((self.work / "plan.json").read_text())
        self.assertEqual(len(payload["motions"]), 60)
        self.assertEqual((self.root / "plan-model.count").read_text(), "1")
        self.assertRegex(str(first["plan_sha256"]), r"^[0-9a-f]{64}$")

    def test_plan_rejects_extra_model_key(self) -> None:
        bad = _write_executable(
            self.root / "bad-model.py",
            """
            #!/usr/bin/env python3
            import json, sys
            value = json.loads(sys.stdin.read())
            value = {'version': 1, 'mode': 'plan', 'set_id': value['set_id'], 'character_id': value['character_id'], 'character_anchors': ['a'], 'motions': [], 'extra': True}
            print(json.dumps(value))
            """,
        )
        with self.assertRaises(MODULE.MediaError) as context:
            MODULE.plan(self.character, [sys.executable, str(bad)], self.work, "set-1", "char-1")
        self.assertEqual(context.exception.code, "model_schema_invalid")

    def test_plan_gate_rejects_count_duplicate_position_and_duration(self) -> None:
        self._plan()
        payload = json.loads((self.work / "plan.json").read_text())
        model = {key: payload[key] for key in ("version", "mode", "set_id", "character_id", "character_anchors", "motions")}
        for expected in ("motion_count_invalid", "motion_position_duplicate", "duration_invalid"):
            with self.subTest(expected=expected):
                candidate = json.loads(json.dumps(model))
                if expected == "motion_count_invalid":
                    candidate["motions"].pop()
                elif expected == "motion_position_duplicate":
                    candidate["motions"][1].update({"batch": 1, "position": 1})
                else:
                    candidate["motions"][0]["duration_ms"] = 499
                with self.assertRaises(MODULE.MediaError) as context:
                    MODULE._validate_plan_model(candidate, set_id="set-1", character_id="char-1")
                self.assertEqual(context.exception.code, expected)

    def test_command_argument_remains_literal(self) -> None:
        marker = self.root / "should-not-exist"
        script = _write_executable(
            self.root / "literal-model.py",
            """
            #!/usr/bin/env python3
            import json, sys
            value = json.loads(sys.stdin.read())
            motions = []
            for batch in range(1, 7):
                for position in range(1, 11):
                    number = (batch - 1) * 10 + position
                    motions.append({'motion_id': f'm-{number}', 'batch': batch, 'position': position, 'intent': 'intent', 'action': 'action', 'provider_prompt': 'prompt', 'duration_ms': 500})
            print(json.dumps({'version': 1, 'mode': 'plan', 'set_id': value['set_id'], 'character_id': value['character_id'], 'character_anchors': ['anchor'], 'motions': motions}))
            """,
        )
        result = MODULE.plan(self.character, [sys.executable, str(script), f"$(touch {marker})"], self.work, "set-1", "char-1")
        self.assertEqual(result["status"], "ready")
        self.assertFalse(marker.exists())

    def test_cli_parse_error_is_one_json_object_without_stderr(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(MODULE_ROOT / "line_sticker_media.py"), "--help"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(len(completed.stdout.splitlines()), 1)
        value = json.loads(completed.stdout)
        self.assertEqual(value["reason"], "configuration_error")
        self.assertNotIn("creative_prompt", completed.stdout)

    def test_command_timeout_and_output_overflow_are_bounded(self) -> None:
        timeout = _write_executable(
            self.root / "timeout-model.py",
            """
            #!/usr/bin/env python3
            import time
            time.sleep(1)
            """,
        )
        overflow = _write_executable(
            self.root / "overflow-model.py",
            """
            #!/usr/bin/env python3
            print('x' * 1048577)
            """,
        )
        with mock.patch.object(MODULE, "COMMAND_TIMEOUT_SECONDS", 0.01):
            with self.assertRaises(MODULE.MediaError) as context:
                MODULE.plan(self.character, [sys.executable, str(timeout)], self.work / "timeout", "set-1", "char-1")
            self.assertEqual(context.exception.code, "command_timeout")
        with self.assertRaises(MODULE.MediaError) as context:
            MODULE.plan(self.character, [sys.executable, str(overflow)], self.work / "overflow", "set-1", "char-1")
        self.assertEqual(context.exception.code, "command_output_overflow")

    def test_full_real_ffmpeg_pipeline_validates_package(self) -> None:
        self._plan()
        template = _make_video(self.root)
        provider = _write_provider(self.root / "provider.py")
        converted = MODULE.convert(
            self.work / "plan.json",
            [sys.executable, str(provider), str(template)],
            self.work,
            "1.00",
            "ffmpeg",
            "ffprobe",
        )
        self.assertEqual(converted["status"], "ready")
        self.assertEqual((self.root / "provider.count").read_text(), "6")
        selected = MODULE.select(
            self.work / "plan.json",
            self.work / "candidates",
            [sys.executable, str(self.plan_model)],
            self.work,
        )
        self.assertEqual(selected["status"], "ready")
        output = self.root / "official-package"
        packaged = MODULE.package(self.work / "selection.json", self.work, output, MODULE_ROOT / "official-policy.json", "ffmpeg")
        self.assertEqual(packaged["status"], "ready")
        self.assertEqual(len(list(output.glob("*.png"))), 26)
        self.assertEqual(json.loads((output / "provenance.json").read_text())["rights"], "original_ai_generated")

    def test_unknown_acknowledgement_is_durable_and_never_retried(self) -> None:
        self._plan()
        script = _write_executable(
            self.root / "unknown-provider.py",
            """
            #!/usr/bin/env python3
            import json
            from pathlib import Path
            import sys
            count = Path(__file__).with_suffix('.count')
            count.write_text(str(int(count.read_text() or '0') + 1) if count.exists() else '1')
            request = json.load(sys.stdin)
            print(json.dumps({'request_id': 'unknown', 'batch': request['batch'], 'provider': 'p', 'model': 'm', 'quoted_cost_usd': '0.01', 'acknowledged': 'unknown', 'video_path': 'missing', 'video_sha256': '0' * 64, 'segments': []}))
            """,
        )
        with self.assertRaises(MODULE.MediaError) as first:
            MODULE.convert(self.work / "plan.json", [sys.executable, str(script)], self.work, "1.00", "ffmpeg", "ffprobe")
        self.assertEqual(first.exception.code, "reconcile_unknown")
        with self.assertRaises(MODULE.MediaError) as second:
            MODULE.convert(self.work / "plan.json", [sys.executable, str(script)], self.work, "1.00", "ffmpeg", "ffprobe")
        self.assertEqual(second.exception.code, "reconcile_unknown")
        self.assertEqual((self.root / "unknown-provider.count").read_text(), "1")

    def test_cost_cap_is_fenced_after_quote_and_not_retried(self) -> None:
        self._plan()
        template = _make_video(self.root)
        provider = _write_provider(self.root / "cost-provider.py")
        with self.assertRaises(MODULE.MediaError) as first:
            MODULE.convert(self.work / "plan.json", [sys.executable, str(provider), str(template)], self.work, "0.005", "ffmpeg", "ffprobe")
        self.assertEqual(first.exception.code, "cost_exceeded")
        with self.assertRaises(MODULE.MediaError) as second:
            MODULE.convert(self.work / "plan.json", [sys.executable, str(provider), str(template)], self.work, "0.005", "ffmpeg", "ffprobe")
        self.assertEqual(second.exception.code, "cost_exceeded")
        self.assertEqual((self.root / "cost-provider.count").read_text(), "1")

    def test_selection_changed_candidate_requires_fresh_model(self) -> None:
        self._plan()
        candidates = self.work / "candidates"
        candidates.mkdir()
        for number in range(1, 61):
            path = candidates / f"motion-{number:02d}.png"
            path.write_bytes(f"candidate-{number}".encode())
            (candidates / f"motion-{number:02d}.json").write_text(json.dumps({
                "motion_id": f"motion-{number:02d}", "path": str(path), "candidate_sha256": _sha256(path),
                "validation_errors": [], "parsed": {}, "first_frame_path": str(path),
            }))
        model = _write_select_model(self.root / "select-model.py")
        first = MODULE.select(self.work / "plan.json", candidates, [sys.executable, str(model)], self.work)
        self.assertEqual(first["status"], "ready")
        (candidates / "motion-01.png").write_bytes(b"changed")
        second = MODULE.select(self.work / "plan.json", candidates, [sys.executable, str(model)], self.work)
        self.assertEqual(second["status"], "ready")
        self.assertEqual((self.root / "select-model.count").read_text(), "2")


if __name__ == "__main__":
    unittest.main()
