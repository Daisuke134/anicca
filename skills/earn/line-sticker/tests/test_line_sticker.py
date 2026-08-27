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
from unittest import mock
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
    extra_chunks: list[tuple[str, bytes]] | None = None,
    after_idat_chunks: list[tuple[str, bytes]] | None = None,
    frame_dimensions: list[tuple[int, int]] | None = None,
    actl_after_idat: bool = False,
) -> bytes:
    chunks = [b"\x89PNG\r\n\x1a\n"]
    chunks.append(_chunk("IHDR", struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)))
    for kind, payload in extra_chunks or []:
        chunks.append(_chunk(kind, payload))
    if animated and not actl_after_idat:
        chunks.append(_chunk("acTL", struct.pack(">II", frames, plays)))
        sequence = 0
        for frame in range(frames):
            frame_width, frame_height = (
                frame_dimensions[frame] if frame_dimensions is not None else (width, height)
            )
            chunks.append(
                _chunk(
                    "fcTL",
                    struct.pack(">IIIIIHHBB", sequence, frame_width, frame_height, 0, 0, delay_num, delay_den, 0, 0),
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
    if animated and actl_after_idat:
        chunks.append(_chunk("acTL", struct.pack(">II", frames, plays)))
    for kind, payload in after_idat_chunks or []:
        chunks.append(_chunk(kind, payload))
    if marker:
        chunks.append(_chunk("tEXt", b"asset=" + marker.encode("ascii")))
    chunks.append(_chunk("IEND", b""))
    return b"".join(chunks)


def _write_fake_ffmpeg(
    path: Path,
    *,
    enclosed_hole: bool = False,
    opaque_background: bool = False,
    opaque_background_name: str | None = None,
    later_hole: bool = False,
    identical_frames: bool = False,
    identical_frames_name: str | None = None,
    extra_frame: bool = False,
) -> Path:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import struct, sys\n"
        "input_path = Path(sys.argv[sys.argv.index('-i') + 1])\n"
        "data = input_path.read_bytes()\n"
        "width, height = struct.unpack('>II', data[16:24])\n"
        "frame_count = int(sys.argv[sys.argv.index('-frames:v') + 1])\n"
        "output_path = Path(sys.argv[-1])\n"
        "frames = []\n"
        "for frame in range(frame_count):\n"
        "    pixels = bytearray(b'\\xff' * (width * height * 4))\n"
        + (
            "    if not (" + repr(opaque_background) + " or input_path.name == " + repr(opaque_background_name) + "):\n"
            "        for x in range(width):\n"
            "            pixels[(x * 4) + 3] = 0\n"
            "            pixels[((height - 1) * width + x) * 4 + 3] = 0\n"
            "        for y in range(height):\n"
            "            pixels[(y * width) * 4 + 3] = 0\n"
            "            pixels[(y * width + width - 1) * 4 + 3] = 0\n"
            if True
            else ""
        )
        + (
            "    if not (" + repr(identical_frames) + " or input_path.name == " + repr(identical_frames_name) + "):\n"
            "        center = ((height // 2) * width + (width // 2)) * 4\n"
            "        pixels[center] = frame % 255\n"
            if True
            else ""
        )
        + (
            "    if input_path.name == '01.png' and " + repr(enclosed_hole) + " and frame == 0:\n"
            "        pixels[((height // 2) * width + (width // 2)) * 4 + 3] = 0\n"
            if enclosed_hole
            else ""
        )
        + (
            "    if input_path.name == '01.png' and " + repr(later_hole) + " and frame == 1:\n"
            "        pixels[((height // 2) * width + (width // 2)) * 4 + 3] = 0\n"
            if later_hole
            else ""
        )
        + "    frames.append(bytes(pixels))\n"
        + "output = b''.join(frames)\n"
        + ("output += frames[-1]\n" if extra_frame else "")
        + "(sys.stdout.buffer.write(output) if str(output_path) == '-' else output_path.write_bytes(output))\n",
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


def _generate_real_apng(path: Path, width: int, height: int, seed: int = 1) -> None:
    generated = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"nullsrc=size={width}x{height}:rate=5,format=rgba,geq=r='mod(X+Y+{seed}+N*17,256)':g='mod(X*2+Y+{seed}+N*29,256)':b='mod(X+Y*2+{seed}+N*43,256)':a='if(eq(X,0)+eq(X,W-1)+eq(Y,0)+eq(Y,H-1),0,255)'",
            "-frames:v",
            "5",
            "-plays",
            "1",
            "-f",
            "apng",
            str(path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if generated.returncode:
        raise AssertionError(generated.stderr.decode(errors="replace"))


def _generate_real_png(path: Path, width: int, height: int) -> None:
    generated = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black@0.0:s={width}x{height},format=rgba",
            "-frames:v",
            "1",
            "-f",
            "image2",
            str(path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if generated.returncode:
        raise AssertionError(generated.stderr.decode(errors="replace"))


def _corrupt_fdat_payload(contents: bytes) -> bytes:
    data = bytearray(contents)
    offset = 8
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = bytes(data[offset + 4 : offset + 8])
        if kind == b"fdAT" and length > 5:
            payload_start = offset + 8
            data[payload_start + 4 : payload_start + length] = b"\x00" * (length - 4)
            crc_body = bytes(data[offset + 4 : payload_start + length])
            data[payload_start + length : payload_start + length + 4] = struct.pack(
                ">I", zlib.crc32(crc_body) & 0xFFFFFFFF
            )
            return bytes(data)
        offset += length + 12
    raise AssertionError("fixture has no fdAT chunk")


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

    def test_policy_schema_values_and_dates_are_fail_closed(self) -> None:
        variants = {
            "wrong value": lambda policy: policy["main"].update({"width": 1}),
            "wrong type": lambda policy: policy.update({"max_file_bytes": "1000000"}),
            "extra key": lambda policy: policy.update({"untrusted": True}),
            "missing key": lambda policy: policy.pop("required_color_types"),
        }
        for label, mutate in variants.items():
            with self.subTest(label=label):
                policy_path = self.root.parent / f"policy-{label.replace(' ', '-')}.json"
                policy = json.loads(POLICY.read_text(encoding="utf-8"))
                mutate(policy)
                policy_path.write_text(json.dumps(policy) + "\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "^policy_hash_mismatch$"):
                    MODULE.validate_package(self.root, policy_path, ffmpeg=str(self.ffmpeg))
        self.assertTrue(MODULE._policy_is_stale({"observed_at": "2999-01-01", "max_policy_age_days": 30}))

    def test_policy_uses_versioned_file_hash_trust_anchor(self) -> None:
        self.assertFalse(hasattr(MODULE, "OFFICIAL_POLICY"))
        self.assertEqual(MODULE.POLICY_SHA256_V1, _sha256(POLICY.read_bytes()))
        tampered = self.root.parent / "tampered-policy.json"
        tampered.write_bytes(POLICY.read_bytes().replace(b'"version": 1', b'"version": 2'))
        with self.assertRaisesRegex(ValueError, "^policy_hash_mismatch$"):
            MODULE.validate_package(self.root, tampered, ffmpeg=str(self.ffmpeg))

    def test_invalid_png_type_or_size_is_rejected_before_parse_and_ffmpeg(self) -> None:
        target = self.root / "01.png"
        target.unlink()
        target.symlink_to(self.root / "02.png")
        original_parse = MODULE.parse_png
        original_run = MODULE.subprocess.run

        def parse(path: Path) -> dict[str, object]:
            if Path(path).name == "01.png":
                raise AssertionError("non-regular PNG was parsed")
            return original_parse(path)

        def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "-i" in command and Path(command[command.index("-i") + 1]).name == "01.png":
                raise AssertionError("non-regular PNG reached ffmpeg")
            return original_run(command, **kwargs)

        with mock.patch.object(MODULE, "parse_png", side_effect=parse), mock.patch.object(MODULE.subprocess, "run", side_effect=run):
            self.assertEqual(self._validate()["errors"], ["file_not_regular:01.png"])

    def test_oversized_png_skips_parse_and_ffmpeg(self) -> None:
        self._make_large_asset()
        original_parse = MODULE.parse_png
        original_run = MODULE.subprocess.run

        def parse(path: Path) -> dict[str, object]:
            if Path(path).name == "01.png":
                raise AssertionError("oversized PNG was parsed")
            return original_parse(path)

        def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "-i" in command and Path(command[command.index("-i") + 1]).name == "01.png":
                raise AssertionError("oversized PNG reached ffmpeg")
            return original_run(command, **kwargs)

        with mock.patch.object(MODULE, "parse_png", side_effect=parse), mock.patch.object(MODULE.subprocess, "run", side_effect=run):
            self.assertEqual(self._validate()["errors"], ["file_too_large:01.png"])

    def test_invalid_dimensions_skip_ffmpeg(self) -> None:
        self._make_bad_dimensions()
        original_run = MODULE.subprocess.run

        def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "-i" in command and Path(command[command.index("-i") + 1]).name == "01.png":
                raise AssertionError("invalid-dimension PNG reached ffmpeg")
            return original_run(command, **kwargs)

        with mock.patch.object(MODULE.subprocess, "run", side_effect=run):
            self.assertEqual(self._validate()["errors"], ["dimensions_invalid:01.png"])

    def test_acTL_must_precede_IDAT(self) -> None:
        _replace_asset(self.root, "01.png", _png(270, 270, animated=True, actl_after_idat=True, marker="01-actl-after"))
        self.assertEqual(self._validate()["errors"], ["png_apng_order_invalid:01.png"])

    def test_opaque_background_is_rejected(self) -> None:
        ffmpeg = _write_fake_ffmpeg(Path(self.tempdir.name) / "opaque-ffmpeg", opaque_background_name="01.png")
        self.assertEqual(self._validate(ffmpeg=ffmpeg)["errors"], ["alpha_background_missing:01.png"])

    def test_later_frame_unexpected_hole_is_rejected(self) -> None:
        ffmpeg = _write_fake_ffmpeg(Path(self.tempdir.name) / "later-hole-ffmpeg", later_hole=True)
        self.assertEqual(self._validate(ffmpeg=ffmpeg)["errors"], ["alpha_hole_unexpected:01.png"])

    def test_identical_decoded_frames_are_rejected(self) -> None:
        ffmpeg = _write_fake_ffmpeg(Path(self.tempdir.name) / "identical-ffmpeg", identical_frames_name="01.png")
        self.assertEqual(self._validate(ffmpeg=ffmpeg)["errors"], ["animation_static:01.png"])

    def test_later_frame_corrupt_payload_fails_real_decode(self) -> None:
        real_apng = Path(self.tempdir.name) / "corrupt-source.png"
        corrupt_apng = Path(self.tempdir.name) / "corrupt-later-frame.png"
        _generate_real_apng(real_apng, 270, 270, seed=81)
        corrupt_apng.write_bytes(_corrupt_fdat_payload(real_apng.read_bytes()))
        parsed = MODULE.parse_png(corrupt_apng)
        self.assertEqual(MODULE._decode_and_check_alpha(corrupt_apng, parsed, "ffmpeg", set()), "decode_failed")

    def test_complete_real_ffmpeg_package_is_ready(self) -> None:
        package = Path(self.tempdir.name) / "real-package"
        package.mkdir()
        _generate_real_apng(package / "main.png", 240, 240, seed=100)
        _generate_real_png(package / "tab.png", 96, 74)
        for number in range(1, 25):
            _generate_real_apng(package / f"{number:02d}.png", 270, 270, seed=100 + number * 3)
        _refresh_package(package)
        result = MODULE.validate_package(package, POLICY, ffmpeg="ffmpeg")
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["errors"], [])

    def test_exact_file_limit_is_rejected(self) -> None:
        self._make_asset_at_limit()
        self.assertEqual(self._validate()["errors"], ["file_too_large:01.png"])

    def test_exact_zip_limit_is_rejected(self) -> None:
        with (self.root / "submission.zip").open("r+b") as stream:
            stream.seek(60_000_000 - 1)
            stream.write(b"x")
        self.assertEqual(self._validate()["errors"], ["zip_too_large"])

    def test_provenance_schema_and_hole_declarations_are_exact(self) -> None:
        variants = {
            "top-level unknown": lambda provenance: provenance.update({"unknown": True}),
            "asset unknown": lambda provenance: provenance["assets"]["01.png"].update({"unknown": True}),
            "hole missing": lambda provenance: provenance["assets"]["01.png"].pop("intentional_alpha_holes"),
            "hole malformed": lambda provenance: provenance["assets"]["01.png"].update({"intentional_alpha_holes": [{"x": "135", "y": 135}]}),
            "hole out of range": lambda provenance: provenance["assets"]["01.png"].update({"intentional_alpha_holes": [{"x": 270, "y": 135}]}),
            "hole unknown field": lambda provenance: provenance["assets"]["01.png"].update({"intentional_alpha_holes": [{"x": 135, "y": 135, "extra": 1}]}),
        }
        for label, mutate in variants.items():
            with self.subTest(label=label):
                provenance_path = self.root / "provenance.json"
                provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
                mutate(provenance)
                provenance_path.write_text(json.dumps(provenance) + "\n", encoding="utf-8")
                self.assertEqual(self._validate()["errors"], ["provenance_invalid"])
                self.tearDown()
                self.setUp()

    def test_rgba_palette_chunk_is_legal(self) -> None:
        _replace_asset(
            self.root,
            "01.png",
            _png(270, 270, animated=True, marker="01-plte", extra_chunks=[("PLTE", b"\x00\x00\x00")]),
        )
        self.assertEqual(self._validate()["status"], "ready")

    def test_rgba_trns_chunk_is_rejected(self) -> None:
        _replace_asset(
            self.root,
            "01.png",
            _png(270, 270, animated=True, marker="01-trns", extra_chunks=[("tRNS", b"\x00\x00")]),
        )
        self.assertEqual(self._validate()["errors"], ["png_trns_invalid:01.png"])

    def test_zip_declared_expansion_is_rejected_before_read(self) -> None:
        entries = {name: (self.root / name).read_bytes() for name in PNG_NAMES}
        entries["01.png"] = b"\x00" * 1_000_001
        _with_zip_entries(self.root, entries)
        self.assertEqual(self._validate()["errors"], ["zip_file_too_large:01.png"])

    def test_ffmpeg_timeout_is_a_stable_error(self) -> None:
        original_run = MODULE.subprocess.run

        def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            self.assertGreater(float(kwargs["timeout"]), 0)
            path = Path(command[command.index("-i") + 1])
            if path.name == "01.png":
                raise subprocess.TimeoutExpired(command, float(kwargs["timeout"]))
            return original_run(command, **kwargs)

        with mock.patch.object(MODULE.subprocess, "run", side_effect=run):
            self.assertEqual(self._validate()["errors"], ["decode_timeout:01.png"])

    def test_real_ffmpeg_generated_apng_decodes(self) -> None:
        real_apng = Path(self.tempdir.name) / "real.png"
        generated = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "nullsrc=size=270x270:rate=5,format=rgba,geq=r='random(1)*255':g='random(2)*255':b='random(3)*255':a='if(eq(X,0)+eq(X,W-1)+eq(Y,0)+eq(Y,H-1),0,255)'",
                "-frames:v",
                "5",
                "-plays",
                "1",
                "-f",
                "apng",
                str(real_apng),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr.decode(errors="replace"))
        parsed = MODULE.parse_png(real_apng)
        self.assertTrue(parsed["animated"])
        self.assertEqual(MODULE._decode_and_check_alpha(real_apng, parsed, "ffmpeg", set()), None)

    def test_fcTL_frame_dimensions_must_match(self) -> None:
        dimensions = [(270, 270), (269, 270), (269, 270), (269, 270), (269, 270)]
        _replace_asset(self.root, "01.png", _png(270, 270, animated=True, frame_dimensions=dimensions, marker="01-dimension-mismatch"))
        self.assertEqual(self._validate()["errors"], ["dimensions_invalid:01.png"])

    def test_plte_legality_is_exact(self) -> None:
        variants = {
            "gray-alpha": _png(270, 270, animated=True, color_type=4, extra_chunks=[("PLTE", b"\x00\x00\x00")], marker="01-plte-gray-alpha"),
            "zero-length": _png(270, 270, animated=True, extra_chunks=[("PLTE", b"")], marker="01-plte-zero"),
            "not-divisible": _png(270, 270, animated=True, extra_chunks=[("PLTE", b"\x00\x00\x00\x00")], marker="01-plte-four"),
            "too-many": _png(270, 270, animated=True, extra_chunks=[("PLTE", b"\x00" * 769)], marker="01-plte-large"),
            "after-idat": _png(270, 270, animated=True, after_idat_chunks=[("PLTE", b"\x00\x00\x00")], marker="01-plte-after"),
        }
        for label, contents in variants.items():
            with self.subTest(label=label):
                try:
                    _replace_asset(self.root, "01.png", contents)
                    self.assertEqual(self._validate()["errors"], ["png_palette_invalid:01.png"])
                finally:
                    self.tearDown()
                    self.setUp()

    def test_unknown_zip_bomb_is_bounded_before_read(self) -> None:
        entries = {name: (self.root / name).read_bytes() for name in PNG_NAMES}
        entries["unknown.bin"] = b"\x00" * 1_000_001
        _with_zip_entries(self.root, entries)
        original_read = MODULE.zipfile.ZipFile.read

        def read(archive: zipfile.ZipFile, info: zipfile.ZipInfo, *args: object, **kwargs: object) -> bytes:
            if info.filename == "unknown.bin":
                raise AssertionError("unknown entry was decompressed before preflight")
            return original_read(archive, info, *args, **kwargs)

        with mock.patch.object(MODULE.zipfile.ZipFile, "read", autospec=True, side_effect=read):
            self.assertEqual(
                self._validate()["errors"],
                ["zip_file_too_large:unknown.bin", "zip_membership_mismatch"],
            )

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

    def test_every_cli_parse_error_is_one_stable_json_object(self) -> None:
        for arguments in ([], ["--help"], ["unknown"], ["validate"], ["validate", "--package"]):
            with self.subTest(arguments=arguments):
                completed = subprocess.run(
                    [sys.executable, str(MODULE_ROOT / "line_sticker.py"), *arguments],
                    check=False,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stderr, "")
                self.assertEqual(len(completed.stdout.splitlines()), 1)
                payload = json.loads(completed.stdout)
                self.assertEqual(payload["errors"], ["configuration_error"])
                self.assertNotIn(str(self.root), completed.stdout)
                self.assertNotIn("prompt:", completed.stdout)

    def test_cli_invalid_policy_is_stable_json_exit_two(self) -> None:
        invalid_policy = self.root.parent / "invalid-policy.json"
        invalid_policy.write_text('{"prompt": "do not leak"}\n', encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(MODULE_ROOT / "line_sticker.py"),
                "validate",
                "--package",
                str(self.root),
                "--policy",
                str(invalid_policy),
                "--ffmpeg",
                str(self.ffmpeg),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(len(completed.stdout.splitlines()), 1)
        self.assertEqual(json.loads(completed.stdout)["errors"], ["policy_hash_mismatch"])
        self.assertNotIn("do not leak", completed.stdout)

    def test_fail_closed_mutations(self) -> None:
        mutations = {
            "policy_hash_mismatch": lambda: self._validate(policy=_copy_policy(self.root, observed_at="2026-01-01")),
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
                try:
                    try:
                        result = mutate()
                    except ValueError as exc:
                        result = {"status": "error", "errors": [str(exc)]}
                    if result is None:
                        result = self._validate()
                    self.assertNotEqual(result["status"], "ready")
                    self.assertEqual(result["errors"], [expected])
                finally:
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
        path = self.root / "provenance.json"
        provenance = json.loads(path.read_text(encoding="utf-8"))
        del provenance["prompt_hashes"]["01.png"]
        path.write_text(json.dumps(provenance, sort_keys=True) + "\n", encoding="utf-8")

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
        _replace_asset(
            self.root,
            "01.png",
            _png(270, 270, animated=True, plays=5, delay_num=1, delay_den=100, marker="01-plays"),
        )

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

    def _make_asset_at_limit(self) -> None:
        contents = bytearray((self.root / "01.png").read_bytes())
        iend = contents.rfind(b"IEND") - 4
        payload_size = 1_000_000 - len(contents) - 12
        self.assertGreater(payload_size, 0)
        contents[iend:iend] = _chunk("tEXt", b"x" * payload_size)
        self.assertEqual(len(contents), 1_000_000)
        _replace_asset(self.root, "01.png", bytes(contents))

    def _make_large_zip(self) -> None:
        with (self.root / "submission.zip").open("r+b") as stream:
            stream.seek(60_000_000)
            stream.write(b"x")


if __name__ == "__main__":
    unittest.main()
