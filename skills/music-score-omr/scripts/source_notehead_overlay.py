#!/usr/bin/env python3
"""Render Audiveris-recognized noteheads over source-only page images."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw


def default_audiveris() -> Path:
    configured = os.environ.get("AUDIVERIS_BIN")
    if configured:
        return Path(configured).expanduser()
    executable = shutil.which("Audiveris") or shutil.which("audiveris")
    if executable:
        return Path(executable)
    candidates = (
        Path.home() / "Applications/Audiveris.app/Contents/MacOS/Audiveris",
        Path("/Applications/Audiveris.app/Contents/MacOS/Audiveris"),
    )
    return next((path for path in candidates if path.is_file()), candidates[0])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--audiveris", type=Path, default=default_audiveris())
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / "audiveris.log").open("wb") as stream:
        subprocess.run(
            [str(args.audiveris), "-batch", "-transcribe", "-export", "-save",
             "-annotate", "-output", str(output), "--", str(source)],
            check=True, stdout=stream, stderr=subprocess.STDOUT,
        )
    archives = list(output.glob("*.annotations.zip"))
    if len(archives) != 1:
        raise RuntimeError(f"expected one annotation archive, found {len(archives)}")
    pages = []
    with zipfile.ZipFile(archives[0]) as archive:
        names = sorted(name for name in archive.namelist() if name.endswith(".annotations.xml"))
        for page, name in enumerate(names, start=1):
            root = ET.fromstring(archive.read(name))
            image_name = root.findtext("./Page/Image")
            if not image_name:
                raise RuntimeError(f"annotation image missing: {name}")
            source_image = output / f"page-{page:04d}-source.png"
            source_image.write_bytes(archive.read(image_name))
            source_pixels = Image.open(source_image).convert("RGB")
            overlay_pixels = source_pixels.copy()
            draw = ImageDraw.Draw(overlay_pixels)
            candidates = []
            for symbol in root.findall(".//Symbol"):
                shape = symbol.get("shape", "")
                bounds = symbol.find("Bounds")
                if not shape.startswith("notehead") or bounds is None:
                    continue
                x, y, width, height = (int(bounds.get(key, "0")) for key in ("x", "y", "w", "h"))
                crop = overlay_pixels.crop((max(0, x - 8), max(0, y - 8),
                                            min(overlay_pixels.width, x + width + 8),
                                            min(overlay_pixels.height, y + height + 8)))
                candidates.append({
                    "detector_id": f"page-{page:04d}-notehead-{len(candidates) + 1:04d}",
                    "shape": shape, "bounds": {"x": x, "y": y, "width": width, "height": height},
                    "source_crop_sha256": hashlib.sha256(crop.tobytes()).hexdigest(),
                })
                draw.ellipse((x - 6, y - 6, x + width + 6, y + height + 6),
                             fill=(0, 255, 80), outline=(255, 0, 0), width=5)
            overlay = output / f"page-{page:04d}-recognized-overlay.png"
            overlay_pixels.save(overlay)
            system_bounds = []
            for symbol in root.findall(".//Symbol"):
                bounds = symbol.find("Bounds")
                if symbol.get("shape") == "brace" and bounds is not None:
                    system_bounds.append((int(bounds.get("y", "0")), int(bounds.get("h", "0"))))
            systems = []
            for system, (top, height) in enumerate(sorted(system_bounds or [(0, source_pixels.height)]), start=1):
                y0, y1 = max(0, top - 100), min(source_pixels.height, top + height + 140)
                source_crop = source_pixels.crop((0, y0, source_pixels.width, y1))
                overlay_crop = overlay_pixels.crop((0, y0, overlay_pixels.width, y1))
                tile = Image.new("RGB", (source_crop.width, source_crop.height * 2 + 80), "white")
                tile.paste(source_crop, (0, 30)); tile.paste(overlay_crop, (0, source_crop.height + 70))
                labels = ImageDraw.Draw(tile)
                labels.text((12, 8), "SOURCE", fill=(0, 0, 0))
                labels.text((12, source_crop.height + 48), "RECOGNIZED = GREEN", fill=(0, 0, 0))
                tile_path = output / f"page-{page:04d}-system-{system:02d}-coverage.png"
                tile.save(tile_path)
                systems.append({"system": system, "coverage_tile": tile_path.name,
                                "coverage_tile_sha256": sha256(tile_path), "source_y": [y0, y1]})
            pages.append({"page": page, "source_image": source_image.name,
                          "source_image_sha256": sha256(source_image),
                          "overlay_image": overlay.name, "overlay_image_sha256": sha256(overlay),
                          "recognized_notehead_count": len(candidates), "systems": systems,
                          "candidates": candidates})
    manifest = {"version": 1, "source_path": str(source), "source_sha256": sha256(source),
                "audiveris_annotations_sha256": sha256(archives[0]), "pages": pages}
    manifest_path = output / "detector-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
