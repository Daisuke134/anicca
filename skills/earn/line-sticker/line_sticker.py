"""Deterministic validation for a LINE animated-sticker package."""

from __future__ import annotations

import argparse
from collections import deque
from datetime import date, datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import zipfile
import zlib


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_NAMES = tuple(sorted(["main.png", "tab.png"] + [f"{number:02d}.png" for number in range(1, 25)]))
PACKAGE_NAMES = frozenset((*PNG_NAMES, "provenance.json", "submission.zip"))
REQUIRED_COLOR_TYPES = frozenset((4, 6))
KNOWN_CRITICAL_CHUNKS = frozenset(("IHDR", "PLTE", "IDAT", "IEND", "acTL", "fcTL", "fdAT"))
SINGLETON_CHUNKS = frozenset(
    {
        "IHDR",
        "PLTE",
        "tRNS",
        "cHRM",
        "gAMA",
        "iCCP",
        "sBIT",
        "sRGB",
        "bKGD",
        "hIST",
        "pHYs",
        "tIME",
        "eXIf",
        "acTL",
        "IEND",
    }
)
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


class PngError(ValueError):
    """A parse failure with a stable, non-sensitive error code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_chunks(data: bytes) -> list[tuple[str, bytes, str]]:
    if not data.startswith(PNG_SIGNATURE):
        raise PngError("png_signature_invalid")
    offset = len(PNG_SIGNATURE)
    chunks: list[tuple[str, bytes, str]] = []
    seen: set[str] = set()
    ended = False
    while offset < len(data):
        if len(data) - offset < 12:
            raise PngError("png_trailing_bytes" if ended else "png_chunk_truncated")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        end = offset + 12 + length
        if end > len(data):
            raise PngError("png_chunk_truncated")
        kind_bytes = data[offset + 4 : offset + 8]
        if len(kind_bytes) != 4 or not all(65 <= c <= 122 and (c < 91 or c > 96) for c in kind_bytes):
            raise PngError("png_chunk_invalid")
        kind = kind_bytes.decode("ascii")
        payload_start = offset + 8
        payload_end = payload_start + length
        payload = data[payload_start:payload_end]
        actual_crc = struct.unpack(">I", data[payload_end : payload_end + 4])[0]
        expected_crc = zlib.crc32(kind_bytes + payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise PngError("png_crc_invalid")
        if kind_bytes[0] & 0x20 == 0 and kind not in KNOWN_CRITICAL_CHUNKS:
            raise PngError("png_critical_chunk_unknown")
        if kind in SINGLETON_CHUNKS and kind in seen:
            raise PngError("png_duplicate_chunk")
        seen.add(kind)
        chunks.append((kind, payload, _sha256(kind_bytes + payload)))
        offset = end
        if kind == "IEND":
            if length != 0:
                raise PngError("png_iend_invalid")
            ended = True
            if offset != len(data):
                raise PngError("png_trailing_bytes")
            break
    if not ended:
        raise PngError("png_iend_missing")
    return chunks


def _parse_frame_control(payload: bytes) -> tuple[int, int, int, int, int, int, int, int, int]:
    if len(payload) != 26:
        raise PngError("fcTL_invalid")
    sequence, width, height, x, y, delay_num, delay_den, dispose, blend = struct.unpack(
        ">IIIIIHHBB", payload
    )
    if width == 0 or height == 0 or dispose > 2 or blend > 1:
        raise PngError("fcTL_invalid")
    return sequence, width, height, x, y, delay_num, delay_den or 100, dispose, blend


def parse_png(path: Path) -> dict[str, object]:
    """Parse PNG/APNG structure without trusting a decoder for metadata."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise PngError("png_unreadable") from exc
    chunks = _read_chunks(data)
    if not chunks or chunks[0][0] != "IHDR":
        raise PngError("png_ihdr_missing")
    ihdr = chunks[0][1]
    if len(ihdr) != 13:
        raise PngError("png_ihdr_invalid")
    width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
        ">IIBBBBB", ihdr
    )
    if width == 0 or height == 0:
        raise PngError("dimensions_invalid")
    if bit_depth != 8 or compression != 0 or filter_method != 0 or interlace not in (0, 1):
        raise PngError("png_ihdr_invalid")
    if color_type not in REQUIRED_COLOR_TYPES:
        raise PngError("color_type_invalid")

    by_kind: dict[str, list[bytes]] = {}
    for kind, payload, _digest in chunks:
        by_kind.setdefault(kind, []).append(payload)
    if len(by_kind.get("IEND", [])) != 1:
        raise PngError("png_iend_missing")
    if "PLTE" in by_kind and color_type in REQUIRED_COLOR_TYPES:
        raise PngError("png_palette_invalid")

    actl = by_kind.get("acTL")
    animated = actl is not None
    if actl is not None:
        if len(actl) != 1 or len(actl[0]) != 8:
            raise PngError("acTL_invalid")
        declared_frames, plays = struct.unpack(">II", actl[0])
        if declared_frames == 0:
            raise PngError("acTL_invalid")
    else:
        declared_frames, plays = 1, 1

    frame_controls: list[tuple[int, int, int, int, int, int, int, int, int]] = []
    expected_sequence = 0
    saw_idat = False
    saw_fdat = False
    first_frame_has_data = False
    current_frame = -1
    frame_has_data: list[bool] = []
    for kind, payload, _digest in chunks:
        if kind == "fcTL":
            if not animated:
                raise PngError("png_apng_invalid")
            if current_frame >= 0 and not frame_has_data[current_frame]:
                raise PngError("png_apng_invalid")
            frame = _parse_frame_control(payload)
            sequence = frame[0]
            if sequence != expected_sequence:
                raise PngError("png_sequence_invalid")
            expected_sequence += 1
            _sequence, frame_width, frame_height, x, y, *_ = frame
            if x + frame_width > width or y + frame_height > height:
                raise PngError("dimensions_invalid")
            if frame_controls and (frame_width, frame_height) != frame_controls[0][1:3]:
                raise PngError("frame_dimensions_invalid")
            frame_controls.append(frame)
            frame_has_data.append(False)
            current_frame += 1
        elif kind == "IDAT":
            if animated and current_frame != 0:
                raise PngError("png_apng_invalid")
            saw_idat = True
            if animated and current_frame == 0:
                first_frame_has_data = True
                frame_has_data[0] = True
        elif kind == "fdAT":
            if not animated or len(payload) < 5:
                raise PngError("png_apng_invalid")
            sequence = struct.unpack(">I", payload[:4])[0]
            if sequence != expected_sequence:
                raise PngError("png_sequence_invalid")
            expected_sequence += 1
            saw_fdat = True
            if current_frame <= 0:
                raise PngError("png_apng_invalid")
            frame_has_data[current_frame] = True
    if not saw_idat:
        raise PngError("png_image_data_missing")
    if animated:
        if not frame_controls or not first_frame_has_data or len(frame_controls) != declared_frames:
            raise PngError("frame_count_invalid")
        if not saw_fdat and declared_frames > 1:
            raise PngError("png_apng_invalid")
        if not all(frame_has_data):
            raise PngError("png_apng_invalid")
        if expected_sequence == 0:
            raise PngError("png_sequence_invalid")
        delays = [Fraction(frame[5], frame[6]) * 1000 for frame in frame_controls]
        if any(delay <= 0 for delay in delays):
            raise PngError("duration_invalid")
        total = sum(delays, Fraction(0, 1)) * plays
        duration_ms: int | float = int(total) if total.denominator == 1 else float(total)
        frames = declared_frames
    else:
        if by_kind.get("fcTL") or by_kind.get("fdAT") or len(by_kind.get("IDAT", [])) == 0:
            raise PngError("png_apng_invalid")
        frames, plays, duration_ms = 1, 1, 0

    chunk_hashes: dict[str, list[str]] = {}
    for kind, _payload, digest in chunks:
        chunk_hashes.setdefault(kind, []).append(digest)
    return {
        "width": width,
        "height": height,
        "color_type": color_type,
        "animated": animated,
        "frames": frames,
        "plays": plays,
        "duration_ms": duration_ms,
        "chunk_hashes": chunk_hashes,
    }


def _load_policy(path: Path) -> dict[str, object]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("policy_invalid") from exc
    if not isinstance(policy, dict):
        raise ValueError("policy_invalid")
    required = {
        "version",
        "source_url",
        "observed_at",
        "max_policy_age_days",
        "sticker_count",
        "main",
        "tab",
        "sticker",
        "apng",
        "max_file_bytes",
        "max_zip_bytes",
        "required_color_types",
    }
    if not required.issubset(policy):
        raise ValueError("policy_invalid")
    return policy


def _policy_is_stale(policy: dict[str, object]) -> bool:
    try:
        observed = date.fromisoformat(str(policy["observed_at"]))
        max_age = int(policy["max_policy_age_days"])
    except (TypeError, ValueError):
        return True
    age = (datetime.now(timezone.utc).date() - observed).days
    return age > max_age


def _error_for_file(code: str, name: str) -> str:
    return code if ":" in code else f"{code}:{name}"


def _safe_zip_name(name: str) -> bool:
    return bool(name) and "\\" not in name and "\x00" not in name and not name.startswith("/") and ".." not in name.split("/")


def _hole_seeds(provenance: dict[str, object], name: str) -> set[tuple[int, int]]:
    values: object = []
    assets = provenance.get("assets")
    if isinstance(assets, dict) and isinstance(assets.get(name), dict):
        values = assets[name].get("intentional_alpha_holes", [])
    root_holes = provenance.get("intentional_alpha_holes")
    if isinstance(root_holes, dict) and name in root_holes:
        values = root_holes[name]
    if not isinstance(values, list):
        return set()
    seeds: set[tuple[int, int]] = set()
    for value in values:
        if isinstance(value, dict) and isinstance(value.get("x"), int) and isinstance(value.get("y"), int):
            seeds.add((value["x"], value["y"]))
        elif isinstance(value, (list, tuple)) and len(value) == 2 and all(isinstance(item, int) for item in value):
            seeds.add((value[0], value[1]))
    return seeds


def _has_unexpected_alpha_hole(raw: bytes, width: int, height: int, seeds: set[tuple[int, int]]) -> bool:
    if len(raw) != width * height * 4:
        return True
    transparent = bytearray(width * height)
    for index in range(width * height):
        transparent[index] = raw[index * 4 + 3] == 0
    outside = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()
    for y in range(height):
        for x in (0, width - 1):
            index = y * width + x
            if transparent[index] and not outside[index]:
                outside[index] = 1
                queue.append((x, y))
    for x in range(width):
        for y in (0, height - 1):
            index = y * width + x
            if transparent[index] and not outside[index]:
                outside[index] = 1
                queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height:
                index = ny * width + nx
                if transparent[index] and not outside[index]:
                    outside[index] = 1
                    queue.append((nx, ny))
    visited = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            start = y * width + x
            if not transparent[start] or outside[start] or visited[start]:
                continue
            component: set[tuple[int, int]] = set()
            queue.append((x, y))
            visited[start] = 1
            while queue:
                cx, cy = queue.popleft()
                component.add((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < width and 0 <= ny < height:
                        index = ny * width + nx
                        if transparent[index] and not outside[index] and not visited[index]:
                            visited[index] = 1
                            queue.append((nx, ny))
            if not component.intersection(seeds):
                return True
    return False


def _decode_and_check_alpha(path: Path, parsed: dict[str, object], ffmpeg: str, seeds: set[tuple[int, int]]) -> str | None:
    try:
        decoded = subprocess.run(
            [
                ffmpeg,
                "-v",
                "error",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgba",
                "-",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return "decode_failed"
    width, height = int(parsed["width"]), int(parsed["height"])
    if len(decoded) != width * height * 4:
        return "decoded_byte_count"
    if _has_unexpected_alpha_hole(decoded, width, height, seeds):
        return "alpha_hole_unexpected"
    return None


def _provenance_errors(provenance: object, root: Path) -> list[str]:
    if not isinstance(provenance, dict):
        return ["provenance_missing"]
    errors: list[str] = []
    if not isinstance(provenance.get("set_id"), str) or not provenance["set_id"]:
        errors.append("provenance_incomplete")
    if not isinstance(provenance.get("character_id"), str) or not provenance["character_id"]:
        errors.append("provenance_incomplete")
    if provenance.get("rights") != "original_ai_generated":
        errors.append("provenance_incomplete")
    providers = provenance.get("providers")
    if not isinstance(providers, dict) or not all(isinstance(providers.get(key), str) and providers[key] for key in ("image", "animation")):
        errors.append("provenance_incomplete")
    prompt_hashes = provenance.get("prompt_hashes")
    assets = provenance.get("assets")
    if not isinstance(prompt_hashes, dict) or not isinstance(assets, dict):
        errors.append("provenance_missing")
        return sorted(set(errors))
    for name in PNG_NAMES:
        if name not in prompt_hashes or not isinstance(prompt_hashes[name], str) or not HEX64.fullmatch(prompt_hashes[name]):
            errors.append("provenance_missing")
        entry = assets.get(name)
        if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str) or not HEX64.fullmatch(entry["sha256"]):
            errors.append("provenance_missing")
    actual_names = {name for name in assets if isinstance(name, str)}
    if actual_names != set(PNG_NAMES):
        errors.append("provenance_missing")
    for name in PNG_NAMES:
        entry = assets.get(name)
        if isinstance(entry, dict) and isinstance(entry.get("sha256"), str) and HEX64.fullmatch(entry["sha256"]):
            actual = _sha256((root / name).read_bytes()) if (root / name).is_file() else ""
            if actual.lower() != entry["sha256"].lower():
                errors.append(f"provenance_hash_mismatch:{name}")
    return sorted(set(errors))


def _canonical_package_hash(root: Path, provenance: object, zip_payloads: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in PNG_NAMES:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        path = root / name
        if path.is_file():
            digest.update(path.read_bytes())
    if isinstance(provenance, dict):
        digest.update(json.dumps(provenance, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    for name in sorted(zip_payloads):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(zip_payloads[name])
    return digest.hexdigest()


def validate_package(root: Path, policy_path: Path, ffmpeg: str = "ffmpeg") -> dict[str, object]:
    """Return a stable, effect-free acceptance record for one package directory."""
    root = Path(root)
    policy = _load_policy(Path(policy_path))
    errors: set[str] = set()
    if _policy_is_stale(policy):
        errors.add("policy_stale")
    try:
        provenance = json.loads((root / "provenance.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        provenance = None
        errors.add("provenance_missing")
    errors.update(_provenance_errors(provenance, root))

    try:
        actual_members = {entry.name for entry in root.iterdir()} if root.is_dir() else set()
    except OSError:
        actual_members = set()
    if actual_members != PACKAGE_NAMES:
        errors.add("package_membership_mismatch")

    parsed_files: dict[str, dict[str, object]] = {}
    file_records: list[dict[str, object]] = []
    file_hashes: dict[str, str] = {}
    max_file_bytes = int(policy["max_file_bytes"])
    for name in PNG_NAMES:
        path = root / name
        if not path.is_file():
            errors.add(f"file_missing:{name}")
            file_records.append({"name": name, "bytes": 0, "sha256": ""})
            continue
        contents = path.read_bytes()
        file_hashes[name] = _sha256(contents)
        record: dict[str, object] = {"name": name, "bytes": len(contents), "sha256": file_hashes[name]}
        if len(contents) > max_file_bytes:
            errors.add(f"file_too_large:{name}")
        try:
            parsed = parse_png(path)
        except PngError as exc:
            errors.add(_error_for_file(exc.code, name))
        else:
            parsed_files[name] = parsed
            record.update(parsed)
        file_records.append(record)

    for digest, names in _group_duplicate_hashes(file_hashes).items():
        if len(names) > 1:
            for left, right in zip(names, names[1:]):
                errors.add(f"duplicate_asset:{left}:{right}")

    main = parsed_files.get("main.png")
    tab = parsed_files.get("tab.png")
    if main is not None:
        expected_main = policy["main"]
        if not isinstance(expected_main, dict) or (main["width"], main["height"]) != (expected_main.get("width"), expected_main.get("height")):
            errors.add("dimensions_invalid:main.png")
        if bool(main["animated"]) != bool(expected_main.get("animated")):
            errors.add("animation_required:main.png")
    if tab is not None:
        expected_tab = policy["tab"]
        if not isinstance(expected_tab, dict) or (tab["width"], tab["height"]) != (expected_tab.get("width"), expected_tab.get("height")):
            errors.add("dimensions_invalid:tab.png")
        if bool(tab["animated"]) != bool(expected_tab.get("animated")):
            errors.add("animation_forbidden:tab.png")

    sticker_policy = policy["sticker"]
    apng_policy = policy["apng"]
    for name in PNG_NAMES:
        if name == "tab.png" or name not in parsed_files:
            continue
        parsed = parsed_files[name]
        if not parsed["animated"] and name != "main.png":
            errors.add(f"animation_required:{name}")
        if name != "main.png" and (not isinstance(sticker_policy, dict) or int(parsed["width"]) > int(sticker_policy["max_width"]) or int(parsed["height"]) > int(sticker_policy["max_height"]) or int(sticker_policy["required_side"]) not in (parsed["width"], parsed["height"])):
            errors.add(f"dimensions_invalid:{name}")
        if parsed["animated"] and isinstance(apng_policy, dict):
            if int(parsed["frames"]) < int(apng_policy["min_frames"]) or int(parsed["frames"]) > int(apng_policy["max_frames"]):
                errors.add(f"frame_count_invalid:{name}")
            if int(parsed["plays"]) < int(apng_policy["min_plays"]) or int(parsed["plays"]) > int(apng_policy["max_plays"]):
                errors.add(f"play_count_invalid:{name}")
            if float(parsed["duration_ms"]) <= 0 or float(parsed["duration_ms"]) > float(apng_policy["max_duration_ms"]):
                errors.add(f"duration_invalid:{name}")

    zip_payloads: dict[str, bytes] = {}
    zip_path = root / "submission.zip"
    max_zip_bytes = int(policy["max_zip_bytes"])
    if not zip_path.is_file():
        errors.add("zip_membership_mismatch")
    elif zip_path.stat().st_size > max_zip_bytes:
        errors.add("zip_too_large")
    else:
        try:
            with zipfile.ZipFile(zip_path) as archive:
                infos = archive.infolist()
                names = [info.filename for info in infos]
                if len(names) != len(set(names)) or set(names) != set(PNG_NAMES) or any(not _safe_zip_name(name) for name in names):
                    errors.add("zip_membership_mismatch")
                for info in infos:
                    if not _safe_zip_name(info.filename) or info.is_dir():
                        continue
                    try:
                        zip_payloads[info.filename] = archive.read(info)
                    except (OSError, RuntimeError, zipfile.BadZipFile):
                        errors.add("zip_invalid")
        except (OSError, zipfile.BadZipFile, RuntimeError):
            errors.add("zip_invalid")
        for name in PNG_NAMES:
            if name in zip_payloads and name in file_hashes and zip_payloads[name] != (root / name).read_bytes():
                errors.add(f"zip_content_mismatch:{name}")

    required_color_types = set(policy.get("required_color_types", REQUIRED_COLOR_TYPES))
    for name, parsed in parsed_files.items():
        if int(parsed["color_type"]) not in required_color_types:
            errors.add(f"color_type_invalid:{name}")
        if isinstance(provenance, dict):
            alpha_error = _decode_and_check_alpha(root / name, parsed, ffmpeg, _hole_seeds(provenance, name))
            if alpha_error:
                errors.add(f"{alpha_error}:{name}")

    package_sha256 = _canonical_package_hash(root, provenance, zip_payloads)
    errors_list = sorted(errors)
    return {
        "status": "ready" if not errors_list else "invalid",
        "effect": 0,
        "readback": 0,
        "package_sha256": package_sha256,
        "files": sorted(file_records, key=lambda record: str(record["name"])),
        "errors": errors_list,
    }


def _group_duplicate_hashes(hashes: dict[str, str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for name, digest in hashes.items():
        grouped.setdefault(digest, []).append(name)
    for names in grouped.values():
        names.sort()
    return grouped


def _configuration_result(code: str) -> dict[str, object]:
    return {"status": "error", "effect": 0, "readback": 0, "package_sha256": "", "files": [], "errors": [code]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="line_sticker.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--package", required=True, type=Path)
    validate.add_argument("--policy", required=True, type=Path)
    validate.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args(argv)
    if args.command != "validate":
        print(json.dumps(_configuration_result("configuration_error"), sort_keys=True, separators=(",", ":")))
        return 2
    if not args.package.is_dir() or not args.policy.is_file():
        print(json.dumps(_configuration_result("configuration_error"), sort_keys=True, separators=(",", ":")))
        return 2
    if shutil.which(str(args.ffmpeg)) is None:
        print(json.dumps(_configuration_result("configuration_error"), sort_keys=True, separators=(",", ":")))
        return 2
    try:
        result = validate_package(args.package, args.policy, ffmpeg=args.ffmpeg)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        result = _configuration_result(str(exc) if str(exc) else "configuration_error")
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    sys.exit(main())
