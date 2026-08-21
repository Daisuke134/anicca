#!/usr/bin/env python3
"""Tracked macOS clipboard bridge for rich HTML and image paste operations."""

from __future__ import annotations

import argparse
import base64
import html as html_lib
import json
import mimetypes
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _plain_text(value: str) -> str:
    return " ".join(
        html_lib.unescape(re.sub(r"<[^>]+>", " ", value)).split()
    )


def browser_write_html(page, value: str) -> None:
    """Write rich content through the page's granted clipboard permission.

    The launchd process has no reliable AppKit pasteboard server, while the
    authenticated X page grants clipboard-write. Keeping the write in that
    page avoids a second browser owner and preserves the existing Meta+V flow.
    """
    page.evaluate(
        """async ({html, plain}) => {
            const item = new ClipboardItem({
                'text/html': new Blob([html], {type: 'text/html'}),
                'text/plain': new Blob([plain], {type: 'text/plain'})
            });
            await navigator.clipboard.write([item]);
        }""",
        {"html": value, "plain": _plain_text(value)},
    )


def browser_write_image(page, path: str) -> None:
    """Write one local image through the page's granted clipboard permission."""
    image = Path(path)
    payload = base64.b64encode(image.read_bytes()).decode("ascii")
    mime = mimetypes.guess_type(image.name)[0] or "image/png"
    page.evaluate(
        """async ({data, mime}) => {
            const raw = atob(data);
            const bytes = new Uint8Array(raw.length);
            for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
            const blob = new Blob([bytes], {type: mime});
            const item = new ClipboardItem({[mime]: blob});
            await navigator.clipboard.write([item]);
        }""",
        {"data": payload, "mime": mime},
    )


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
