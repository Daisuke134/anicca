#!/usr/bin/env python3
"""Save an SVG/PDF as native Illustrator AI and verify one official reopen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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


def _javascript(source: str, timeout: int = 180) -> str:
    return subprocess.run(
        ["osascript", "-e", f'tell application id "{APP_ID}" to do javascript {json.dumps(source)}'],
        check=True, capture_output=True, text=True, timeout=timeout,
    ).stdout.strip()


def _ensure_responsive() -> None:
    """Recover only an empty, stale Illustrator automation session."""
    try:
        _javascript("app.version", timeout=10)
        return
    except subprocess.SubprocessError:
        windows = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to tell process '
             '"Adobe Illustrator" to get name of every window'],
            check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip().strip(", ")
        if windows not in {"", "Adobe Illustrator 2026"}:
            raise RuntimeError("Illustrator is unresponsive with an open document")
        pids = subprocess.run(
            ["pgrep", "-x", "Adobe Illustrator"], check=False,
            capture_output=True, text=True, timeout=5,
        ).stdout.split()
        for pid in pids:
            os.kill(int(pid), 15)
        time.sleep(3)
        subprocess.run(["open", "-a", str(APP_PATH)], check=True, timeout=30)
        for _ in range(30):
            try:
                _javascript("app.version", timeout=5)
                return
            except subprocess.SubprocessError:
                time.sleep(1)
        raise RuntimeError("Illustrator did not recover")


def _open(path: Path, *, recover_empty_session: bool = True) -> None:
    # Illustrator 30.7 can finish opening a PDF while leaving the synchronous
    # `app.open()` JavaScript call unanswered. Use Illustrator's native Apple
    # Event open command, then bind through a separate short readback.
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application id "{APP_ID}" to open POSIX file {json.dumps(str(path))}'],
            check=True, capture_output=True, text=True, timeout=30,
        )
    except subprocess.TimeoutExpired:
        pass
    for _ in range(60):
        try:
            opened = _javascript(
                f"var f=new File({json.dumps(str(path))});var d=null;"
                "for(var i=0;i<app.documents.length;i++){"
                "if(app.documents[i].fullName.fsName==f.fsName){d=app.documents[i];break;}}"
                "d===null?'':(d.activate(),d.fullName.fsName);",
                timeout=5,
            )
            if opened and Path(opened).resolve() == path.resolve():
                return
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
        time.sleep(1)
    if recover_empty_session:
        try:
            document_count = int(_javascript("app.documents.length", timeout=5))
        except (OSError, subprocess.SubprocessError, ValueError):
            document_count = -1
        if document_count == 0:
            pids = subprocess.run(
                ["pgrep", "-x", "Adobe Illustrator"], check=False,
                capture_output=True, text=True, timeout=5,
            ).stdout.split()
            for pid in pids:
                os.kill(int(pid), 15)
            time.sleep(3)
            subprocess.run(["open", "-a", str(APP_PATH)], check=True, timeout=30)
            for _ in range(30):
                try:
                    _javascript("app.version", timeout=5)
                    break
                except subprocess.SubprocessError:
                    time.sleep(1)
            else:
                raise RuntimeError("Illustrator did not recover")
            return _open(path, recover_empty_session=False)
    raise RuntimeError("Illustrator opened a different document")


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

    _ensure_responsive()
    # `open -a` does not make the requested document active when Illustrator already
    # owns another window. Use Illustrator's own open command so the subsequent
    # active-document verification is bound to the exact source.
    _open(source)
    for _ in range(60):
        try:
            active_path = subprocess.run(
                ["osascript", "-e", f'tell application id "{APP_ID}" to do javascript '
                 '"app.activeDocument.fullName.fsName"'],
                check=True, capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            if Path(active_path).resolve() == source:
                break
        except (OSError, subprocess.SubprocessError, ValueError):
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
    structure_text = _javascript(
        "var d=app.activeDocument;"
        "[d.layers.length,d.artboards.length,app.version,d.fullName.fsName].join('|');"
    )
    layers, artboards, illustrator_version, reopened_path = structure_text.split("|", 3)
    if Path(reopened_path).resolve() != output:
        raise RuntimeError("Illustrator reopened a different AI output")
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
        "reopened_output_path": reopened_path,
        "layers": int(layers),
        "artboards": int(artboards),
        "native_private_data": b"/AIPrivateData1" in data,
        "creator_metadata": b"Adobe Illustrator" in data,
    }
    if (source_sha256 == output_sha256 or not payload["native_private_data"]
            or int(layers) < 1 or int(artboards) < 1):
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
