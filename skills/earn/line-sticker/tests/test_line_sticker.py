"""Contract tests for the deterministic LINE animated-sticker package validator."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT))
import line_sticker as MODULE  # noqa: E402  # RED: module is created by the implementation step


POLICY = MODULE_ROOT / "official-policy.json"
PNG_NAMES = ["main.png", "tab.png"] + [f"{n:02d}.png" for n in range(1, 25)]


def _chunk(kind: str, payload: bytes) -> bytes:
    raw_kind = kind.encode("ascii")
    body = raw_kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def _png(
    width: int,
    height: int,
    *,
    animated: bool,
    frames: int = 5,
    plays: int = 1,
    color_type: int = 6,
    delay_num: int = 20,
    delay_den: int = 100,
    marker: str = "",
) -> bytes:
    chunks = [b"\x89PNG\r\n\x1a\n"]
    chunks.append(_chunk("IHDR", struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)))
    if animated:
        chunks.append(_chunk("acTL", struct.pack(">II", frames, plays)))
        sequence = 0
        for frame in range(frames):
            chunks.append(
                _chunk(
                    "fcTL",
                    struct.pack(">IIIIIHHBB", sequence, width, height, 0, 0, delay_num, delay_den, 0, 0),
                )
            )
            sequence += 1
            if frame == 0:
                chunks.append(_chunk("IDAT", zlib.compress(b"\x00\x00\x00\x00")))
            else:
                chunks.append(_chunk("fdAT", struct.pack(">I", sequence) + zlib.compress(b"\x00\x00\x00\x00")))
                sequence += 1
    else:
        chunks.append(_chunk("IDAT", zlib.compress(b"\x00\x00\x00\x00")))
    if marker:
        chunks.append(_chunk("tEXt", b"asset=" + marker.encode("ascii")))
    chunks.append(_chunk("IEND", b""))
    return b"".join(chunks)


def _write_fake_ffmpeg(path: Path, *, enclosed_hole: bool = False) -> Path:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import struct, sys\n"
        "input_path = Path(sys.argv[sys.argv.index('-i') + 1])\n"
        "data = input_path.read_bytes()\n"
        "width, height = struct.unpack('>II', data[16:24])\n"
        "pixels = bytearray(b'\\xff' * (width * height * 4))\n"
        + (
            "if input_path.name == '01.png':\n"
            "    pixels[((height // 2) * width + (width // 2)) * 4 + 3] = 0\n"
            if enclosed_hole
            else ""
        )
        + "sys.stdout.buffer.write(pixels)\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_zip(root: Path, names: list[str] | None = None) -> None:
    names = names or PNG_NAMES
    with zipfile.ZipFile(root / "submission.zip", "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(names):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, (root / name).read_bytes())


def _write_provenance(root: Path) -> None:
    assets = {}
    prompt_hashes = {}
    for name in PNG_NAMES:
        contents = (root / name).read_bytes()
        assets[name] = {
            "sha256": _sha256(contents),
            "intentional_alpha_holes": [],
        }
        prompt_hashes[name] = _sha256(("prompt:" + name).encode("ascii"))
    (root / "provenance.json").write_text(
        json.dumps(
            {
                "set_id": "set-20260828-001",
                "character_id": "char-001",
                "rights": "original_ai_generated",
                "providers": {"image": "openai", "animation": "runway"},
                "prompt_hashes": prompt_hashes,
                "assets": assets,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _refresh_package(root: Path) -> None:
    _write_provenance(root)
    _write_zip(root)


def _make_package(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.png").write_bytes(_png(240, 240, animated=True, marker="main"))
    (root / "tab.png").write_bytes(_png(96, 74, animated=False, marker="tab"))
    for number in range(1, 25):
        name = f"{number:02d}.png"
        (root / name).write_bytes(_png(270, 270, animated=True, marker=name))
    _refresh_package(root)
    return root


def _copy_policy(root: Path, *, observed_at: str) -> Path:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    policy["observed_at"] = observed_at
    path = root.parent / "policy.json"
    path.write_text(json.dumps(policy, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _replace_asset(root: Path, name: str, contents: bytes, *, refresh: bool = True) -> None:
    (root / name).write_bytes(contents)
    if refresh:
        _refresh_package(root)


def _corrupt_crc(contents: bytes) -> bytes:
    data = bytearray(contents)
    offset = 8
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = bytes(data[offset + 4 : offset + 8])
        crc_offset = offset + 8 + length
        if kind == b"IDAT":
            data[crc_offset + 3] ^= 0x01
            return bytes(data)
        offset = crc_offset + 4
    raise AssertionError("fixture has no IDAT chunk")


def _with_zip_entries(root: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(root / "submission.zip", "w", compression=zipfile.ZIP_STORED) as archive:
        for name, contents in entries.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, contents)


class LineStickerValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = _make_package(Path(self.tempdir.name) / "package")
        self.ffmpeg = _write_fake_ffmpeg(Path(self.tempdir.name) / "ffmpeg")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _validate(self, *, policy: Path = POLICY, ffmpeg: Path | None = None) -> dict[str, object]:
        return MODULE.validate_package(self.root, policy, ffmpeg=str(ffmpeg or self.ffmpeg))

    def test_official_policy_is_exact_snapshot(self) -> None:
        self.assertEqual(
            json.loads(POLICY.read_text(encoding="utf-8")),
            {
                "version": 1,
                "source_url": "https://creator.line.me/en/guideline/animationsticker/",
                "observed_at": "2026-08-28",
                "max_policy_age_days": 30,
                "sticker_count": 24,
                "main": {"width": 240, "height": 240, "animated": True},
                "tab": {"width": 96, "height": 74, "animated": False},
                "sticker": {"max_width": 320, "max_height": 270, "required_side": 270},
                "apng": {
                    "min_frames": 5,
                    "max_frames": 20,
                    "min_plays": 1,
                    "max_plays": 4,
                    "max_duration_ms": 4000,
                },
                "max_file_bytes": 1000000,
                "max_zip_bytes": 60000000,
                "required_color_types": [4, 6],
            },
        )

    def test_valid_package_is_ready_and_identity_is_stable(self) -> None:
        first = self._validate()
        second = self._validate()
        self.assertEqual(first["status"], "ready")
        self.assertEqual(first["effect"], 0)
        self.assertEqual(first["readback"], 0)
        self.assertEqual(len(first["files"]), 26)
        self.assertRegex(first["package_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(first, second)
        self.assertEqual([entry["name"] for entry in first["files"]], sorted(PNG_NAMES))

    def test_parse_png_reports_apng_fields_and_chunk_hashes(self) -> None:
        parsed = MODULE.parse_png(self.root / "01.png")
        self.assertEqual(parsed["width"], 270)
        self.assertEqual(parsed["height"], 270)
        self.assertEqual(parsed["color_type"], 6)
        self.assertTrue(parsed["animated"])
        self.assertEqual(parsed["frames"], 5)
        self.assertEqual(parsed["plays"], 1)
        self.assertEqual(parsed["duration_ms"], 1000)
        self.assertTrue(parsed["chunk_hashes"])

    def test_cli_prints_one_json_object_and_returns_ready_exit_code(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(MODULE_ROOT / "line_sticker.py"),
                "validate",
                "--package",
                str(self.root),
                "--policy",
                str(POLICY),
                "--ffmpeg",
                str(self.ffmpeg),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(len(completed.stdout.splitlines()), 1)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(set(("status", "effect", "readback", "package_sha256", "files", "errors")), set(payload))
        self.assertNotIn("prompt:", completed.stdout)

    def test_fail_closed_mutations(self) -> None:
        mutations = {
            "policy_stale": lambda: self._validate(policy=_copy_policy(self.root, observed_at="2026-01-01")),
            "package_membership_mismatch": lambda: self._add_extra_file(),
            "zip_membership_mismatch": lambda: self._add_zip_extra(),
            "zip_content_mismatch:01.png": lambda: self._add_zip_content_mismatch(),
            "provenance_missing": lambda: self._remove_provenance(),
            "provenance_hash_mismatch:01.png": lambda: self._change_provenance_hash(),
            "duplicate_asset:01.png:02.png": lambda: self._duplicate_asset(),
            "png_crc_invalid:01.png": lambda: self._corrupt_asset_crc(),
            "animation_required:01.png": lambda: self._make_static_asset(),
            "frame_count_invalid:01.png": lambda: self._make_short_animation(),
            "play_count_invalid:01.png": lambda: self._make_excessive_play_count(),
            "duration_invalid:01.png": lambda: self._make_long_animation(),
            "dimensions_invalid:01.png": lambda: self._make_bad_dimensions(),
            "color_type_invalid:01.png": lambda: self._make_bad_color_type(),
            "alpha_hole_unexpected:01.png": lambda: self._validate(ffmpeg=_write_fake_ffmpeg(Path(self.tempdir.name) / "hole-ffmpeg", enclosed_hole=True)),
            "file_too_large:01.png": lambda: self._make_large_asset(),
            "zip_too_large": lambda: self._make_large_zip(),
        }
        for expected, mutate in mutations.items():
            with self.subTest(expected=expected):
                result = mutate()
                if result is None:
                    result = self._validate()
                self.assertNotEqual(result["status"], "ready")
                self.assertIn(expected, result["errors"])
                self.tearDown()
                self.setUp()

    def test_declared_alpha_hole_is_allowed(self) -> None:
        provenance_path = self.root / "provenance.json"
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        provenance["assets"]["01.png"]["intentional_alpha_holes"] = [{"x": 135, "y": 135}]
        provenance_path.write_text(json.dumps(provenance, sort_keys=True) + "\n", encoding="utf-8")
        self.assertEqual(self._validate(ffmpeg=_write_fake_ffmpeg(Path(self.tempdir.name) / "hole-ffmpeg", enclosed_hole=True))["status"], "ready")

    def _add_extra_file(self) -> None:
        (self.root / "extra.txt").write_text("unexpected", encoding="utf-8")

    def _add_zip_extra(self) -> None:
        entries = {name: (self.root / name).read_bytes() for name in PNG_NAMES}
        entries["extra.txt"] = b"unexpected"
        _with_zip_entries(self.root, entries)

    def _add_zip_content_mismatch(self) -> None:
        entries = {name: (self.root / name).read_bytes() for name in PNG_NAMES}
        entries["01.png"] = b"different zip bytes"
        _with_zip_entries(self.root, entries)

    def _remove_provenance(self) -> None:
        (self.root / "provenance.json").unlink()

    def _change_provenance_hash(self) -> None:
        path = self.root / "provenance.json"
        provenance = json.loads(path.read_text(encoding="utf-8"))
        provenance["assets"]["01.png"]["sha256"] = "0" * 64
        path.write_text(json.dumps(provenance, sort_keys=True) + "\n", encoding="utf-8")

    def _duplicate_asset(self) -> None:
        _replace_asset(self.root, "02.png", (self.root / "01.png").read_bytes())

    def _corrupt_asset_crc(self) -> None:
        _replace_asset(self.root, "01.png", _corrupt_crc((self.root / "01.png").read_bytes()))

    def _make_static_asset(self) -> None:
        _replace_asset(self.root, "01.png", _png(270, 270, animated=False, marker="01-static"))

    def _make_short_animation(self) -> None:
        _replace_asset(self.root, "01.png", _png(270, 270, animated=True, frames=4, marker="01-short"))

    def _make_excessive_play_count(self) -> None:
        _replace_asset(self.root, "01.png", _png(270, 270, animated=True, plays=5, marker="01-plays"))

    def _make_long_animation(self) -> None:
        _replace_asset(self.root, "01.png", _png(270, 270, animated=True, delay_num=1000, delay_den=1000, marker="01-long"))

    def _make_bad_dimensions(self) -> None:
        _replace_asset(self.root, "01.png", _png(321, 270, animated=True, marker="01-wide"))

    def _make_bad_color_type(self) -> None:
        _replace_asset(self.root, "01.png", _png(270, 270, animated=True, color_type=2, marker="01-rgb"))

    def _make_large_asset(self) -> None:
        contents = bytearray((self.root / "01.png").read_bytes())
        iend = contents.rfind(b"IEND") - 4
        contents[iend:iend] = _chunk("tEXt", b"x" * 1_000_001)
        _replace_asset(self.root, "01.png", bytes(contents))

    def _make_large_zip(self) -> None:
        with (self.root / "submission.zip").open("r+b") as stream:
            stream.seek(60_000_000)
            stream.write(b"x")


if __name__ == "__main__":
    unittest.main()
