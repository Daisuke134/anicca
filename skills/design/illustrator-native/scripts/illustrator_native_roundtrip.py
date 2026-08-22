#!/usr/bin/env python3
"""Save an SVG/PDF as native Illustrator AI and verify one official reopen."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time


APP_ID = "com.adobe.illustrator"
APP_PATH = Path("/Applications/Adobe Illustrator 2026/Adobe Illustrator.app")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _javascript(source: str) -> str:
    return subprocess.run(
        ["osascript", "-e", f'tell application id "{APP_ID}" to do javascript {json.dumps(source)}'],
        check=True, capture_output=True, text=True, timeout=180,
    ).stdout.strip()


def _open(path: Path) -> None:
    subprocess.run(
        ["osascript", "-e", f'tell application id "{APP_ID}" to open POSIX file {json.dumps(str(path))}'],
        check=True, capture_output=True, text=True, timeout=180,
    )


def roundtrip(source: Path, output: Path, receipt: Path) -> dict[str, object]:
    source, output, receipt = source.resolve(), output.resolve(), receipt.resolve()
    if not APP_PATH.is_dir():
        raise RuntimeError(f"Illustrator is not installed at {APP_PATH}")
    if not source.is_file() or source.stat().st_size == 0 or source.suffix.casefold() not in {".svg", ".pdf"}:
        raise ValueError("input must be a non-empty SVG or PDF")
    if output.suffix.casefold() != ".ai" or output == source:
        raise ValueError("output must be a distinct .ai path")
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)

    subprocess.run(["open", "-a", str(APP_PATH), str(source)], check=True, timeout=30)
    for _ in range(60):
        try:
            count = subprocess.run(
                ["osascript", "-e", f'tell application id "{APP_ID}" to count documents'],
                check=True, capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            if int(count or "0") > 0:
                break
        except (subprocess.SubprocessError, ValueError):
            pass
        time.sleep(1)
    else:
        raise RuntimeError("Illustrator did not open the source document")

    save_js = (
        f"var f=new File({json.dumps(str(output))});"
        "var o=new IllustratorSaveOptions();o.pdfCompatible=true;"
        "app.activeDocument.saveAs(f,o);"
    )
    _javascript(save_js)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Illustrator did not create the AI output")
    _javascript("app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);")
    _open(output)
    counts_text = _javascript(
        "var d=app.activeDocument;"
        "[d.pageItems.length,d.textFrames.length,d.layers.length,d.artboards.length,app.version].join('|');"
    )
    page_items, text_frames, layers, artboards, illustrator_version = counts_text.split("|", 4)
    data = output.read_bytes()
    source_sha256, output_sha256 = _sha256(source), _sha256(output)
    payload: dict[str, object] = {
        "version": 1,
        "status": "ok",
        "source_path": str(source),
        "source_sha256": source_sha256,
        "output_path": str(output),
        "output_sha256": output_sha256,
        "output_bytes": len(data),
        "illustrator_version": illustrator_version,
        "page_items": int(page_items),
        "text_frames": int(text_frames),
        "layers": int(layers),
        "artboards": int(artboards),
        "native_private_data": b"/AIPrivateData1" in data,
        "creator_metadata": b"Adobe Illustrator" in data,
    }
    if (source_sha256 == output_sha256 or not payload["native_private_data"]
            or int(page_items) < 1 or int(layers) < 1 or int(artboards) < 1):
        raise RuntimeError("native Illustrator roundtrip verification failed")
    receipt.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(roundtrip(args.input, args.output, args.receipt), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
