#!/usr/bin/env python3
"""E1 — verify copy_to_clipboard.py honors EXIF orientation for tags 6, 3, 8.

For each tag, builds a synthetic JPG with a non-square shape and that EXIF
orientation, runs `copy_to_clipboard.py image <jpg> --quality 90 --dry-write
<out.jpg>`, then re-opens <out.jpg> and asserts:
  - orientation EXIF tag is stripped (None or 1)
  - dimensions match the visually-correct (= transposed) shape for tag 6/8

Exits 0 if all 3 cases pass.
"""
from __future__ import annotations
import io, os, pathlib, subprocess, sys, tempfile
from PIL import Image


SCRIPT = pathlib.Path.home() / ".claude/skills/x-article-publisher/scripts/copy_to_clipboard.py"
HERE = pathlib.Path(__file__).resolve().parent
WORK = HERE / "_e1_work"
WORK.mkdir(exist_ok=True)


def make_jpg(path: pathlib.Path, w: int, h: int, orientation: int) -> None:
    """Use PIL's native Exif class — no piexif dependency."""
    img = Image.new("RGB", (w, h), color=(120, 60, 200))
    exif = Image.Exif()
    exif[274] = orientation  # 274 = Orientation tag
    img.save(str(path), "JPEG", exif=exif.tobytes(), quality=90)


def assert_dry_write(in_path: pathlib.Path, orientation: int, expected_size: tuple) -> tuple[bool, str]:
    out_path = WORK / f"out_orient{orientation}.jpg"
    res = subprocess.run(
        [
            "python3", str(SCRIPT), "image", str(in_path),
            "--quality", "90",
            "--dry-write", str(out_path),
        ],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        return False, f"orient={orientation}: script exit {res.returncode}: {res.stderr.strip()}"
    if not out_path.exists():
        return False, f"orient={orientation}: out file not written"
    try:
        out = Image.open(str(out_path))
        exif = out._getexif() or {}
        tag = exif.get(274)  # 274 = Orientation
        if tag not in (None, 1):
            return False, f"orient={orientation}: out EXIF orientation still {tag!r}"
        if out.size != expected_size:
            return False, f"orient={orientation}: size {out.size} != expected {expected_size}"
    finally:
        try:
            out.close()
        except Exception:
            pass
    return True, f"orient={orientation}: PASS (out size={out.size}, exif orient stripped)"


def assert_dry_write_no_quality(in_path: pathlib.Path, orientation: int, expected_size: tuple) -> tuple[bool, str]:
    """Exercise the load_exif_corrected_bytes() path (= no --quality)."""
    out_path = WORK / f"out_noq_orient{orientation}.jpg"
    res = subprocess.run(
        [
            "python3", str(SCRIPT), "image", str(in_path),
            "--dry-write", str(out_path),
        ],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        return False, f"orient={orientation} (no-q): script exit {res.returncode}: {res.stderr.strip()}"
    if not out_path.exists():
        return False, f"orient={orientation} (no-q): out file not written"
    out = Image.open(str(out_path))
    exif = out._getexif() or {}
    tag = exif.get(274)
    if tag not in (None, 1):
        return False, f"orient={orientation} (no-q): out EXIF orientation still {tag!r}"
    if out.size != expected_size:
        return False, f"orient={orientation} (no-q): size {out.size} != expected {expected_size}"
    return True, f"orient={orientation} (no-q via load_exif_corrected_bytes): PASS"


def main() -> int:
    src_w, src_h = 300, 400  # source shape (portrait by intent)
    # orientation tag => expected DISPLAYED (= transposed) dimensions
    expected = {
        1: (src_w, src_h),
        3: (src_w, src_h),  # 180° — same dimensions
        6: (src_h, src_w),  # 90° CW — swap
        8: (src_h, src_w),  # 90° CCW — swap
    }
    overall = True
    for tag in (6, 3, 8):
        src = WORK / f"src_orient{tag}.jpg"
        make_jpg(src, src_w, src_h, tag)
        # ★ Two passes: --quality 90 (exercises compress_image) + no --quality
        # (exercises load_exif_corrected_bytes). Both pipelines must respect
        # EXIF — adversary r2 noted that only one was being tested.
        ok, msg = assert_dry_write(src, tag, expected[tag])
        print(msg)
        overall = overall and ok
        ok, msg = assert_dry_write_no_quality(src, tag, expected[tag])
        print(msg)
        overall = overall and ok
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
