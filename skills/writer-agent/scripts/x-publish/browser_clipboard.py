#!/usr/bin/env python3
"""Tracked macOS clipboard bridge for rich HTML and image paste operations."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run_jxa(source: str, arguments: list[str]) -> None:
    result = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", source, *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("clipboard bridge failed")


def copy_html(path: Path) -> None:
    script = r"""
function run(argv) {
ObjC.import('AppKit'); ObjC.import('Foundation');
const path = $.NSString.stringWithString(argv[0]);
const html = $.NSString.stringWithContentsOfFileEncodingError(path, $.NSUTF8StringEncoding, null);
const pasteboard = $.NSPasteboard.generalPasteboard;
pasteboard.clearContents;
pasteboard.setStringForType(html, 'public.html');
pasteboard.setStringForType(html, 'public.utf8-plain-text');
}
"""
    run_jxa(script, [str(path)])


def copy_image(path: Path) -> None:
    script = r"""
function run(argv) {
ObjC.import('AppKit'); ObjC.import('Foundation');
const data = $.NSData.dataWithContentsOfFile(argv[0]);
if (!data) throw new Error('image data load failed');
const pasteboard = $.NSPasteboard.generalPasteboard;
pasteboard.clearContents;
if (!pasteboard.setDataForType(data, 'public.png')) {
  throw new Error('PNG pasteboard write failed');
}
}
"""
    run_jxa(script, [str(path)])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("html", "image"), nargs="?")
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--file", dest="file", type=Path)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.probe:
        ready = sys.platform == "darwin" and shutil.which("osascript") is not None
        print(json.dumps({"ready": ready, "bridge": "tracked-jxa"}))
        return 0 if ready else 75
    selected = args.file or args.path
    if selected is None or not selected.is_file():
        return 2
    try:
        copy_html(selected) if args.kind == "html" else copy_image(selected)
    except RuntimeError:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
