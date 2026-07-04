#!/usr/bin/env python3
"""note-create-rich-draft.py -- REQ-3 (Sprint 2 fix, defect #1): create a REAL note.com draft whose body
embeds a hero diagram + inline figures -- via note_mcp's EXISTING, already-proven API functions
(create_draft, upload_body_image, generate_image_html). This file never reimplements note_mcp; it only
orchestrates it.

WHY this exists: the prior Mode-A draft (lib/note_publish.sh's note_create_draft_from_file) sent the
markdown body VERBATIM with no images at all -- REQ-3 mandates a "deeply-researched, VISUAL explainer",
not pure text. This script resolves body markers (e.g. "@@HERO@@") to real uploaded images BEFORE the
body is saved, so the resulting note.com draft actually contains a hero diagram + inline figures.

EYECATCH IS DELIBERATELY NOT HANDLED HERE (defect #2 -- see lib/note-set-eyecatch.py instead): this
script's author first tried note_mcp.api.images.upload_eyecatch_image and it reproducibly raises
"Image upload failed: API response missing required field 'url'" on every call (verified live,
2026-07-04) -- the same defect SKILL.md's older notes describe for that specific endpoint, even though
the OTHER note_mcp image functions used here (upload_body_image, create_draft) work correctly via the
API. lib/note-set-eyecatch.py uses the editor's own "画像を追加" button instead (verified to persist:
the URL survives a reload and shows up in GET /v3/notes/{key}'s `eyecatch` field).

INTERFACE (env-overridable so this stays testable without touching real creds/paths -- same convention
as lib/note_publish.sh):
  argv:
    --title TITLE                 article title (required)
    --body PATH                   markdown draft path, containing marker tokens on their own lines
                                   (e.g. "@@HERO@@") -- required
    --marker NAME=IMG_PATH:W:H    repeatable; replaces the line "@@NAME@@" in --body with the uploaded
                                   image, embedded via note_mcp's generate_image_html at WxH (the
                                   caller supplies the already-known native pixel size so this script
                                   never needs an image-decoding dependency)
  env in:
    NOTE_COOKIES_FILE             default: $HOME/.cloak/note-work/note-cookies.json
    NOTE_MCP_SRC                  default: $HOME/.openclaw/external/note-mcp/src
    NOTE_USER_ID / NOTE_USERNAME  default: "14651590" / "anicca123" (the existing note-mcp Session
                                   convention lib/note_publish.sh already uses)
  stdout on success: one line per fact, machine-parseable (grep -oE '^KEY: .*'):
    NOTE_DRAFT_KEY: <key>
    NOTE_DRAFT_NUM: <numeric id>
    NOTE_VISUAL_<NAME>_URL: <url>     (one per --marker, only on successful upload)
  exit: 0 on success (draft created); non-zero + reason on stderr on ANY failure. Never fakes a URL --
  if an individual visual upload fails, that ONE fact is simply absent from stdout (fail-closed per
  marker), but the draft itself is still created with whatever markers DID resolve, so a genuine
  network hiccup on one image never blocks producing a REAL note draft.
"""
import argparse
import asyncio
import json
import os
import struct
import sys


def _png_size(path: str) -> tuple[int, int] | None:
    """Read (width, height) from a PNG file header without any image-decoding dependency.

    PNG layout: 8-byte signature, then a 4-byte length + 4-byte "IHDR" chunk whose first 8 bytes are
    big-endian width/height (see the PNG spec, section 11.2.2). Returns None if the file is not a
    recognizable PNG (caller falls back to the caller-supplied width/height in that case).
    """
    try:
        with open(path, "rb") as f:
            header = f.read(33)
        if len(header) < 33 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
            return None
        width, height = struct.unpack(">II", header[16:24])
        return width, height
    except OSError:
        return None


def _parse_marker_arg(raw: str) -> tuple[str, str, int, int]:
    """Parse "NAME=IMG_PATH:W:H" (W/H optional -- if omitted, read from the PNG header)."""
    name, _, rest = raw.partition("=")
    if not name or not rest:
        raise ValueError(f"--marker must be NAME=IMG_PATH[:W:H], got: {raw!r}")
    parts = rest.split(":")
    img_path = parts[0]
    if len(parts) >= 3:
        width, height = int(parts[1]), int(parts[2])
    else:
        dims = _png_size(img_path)
        if dims is None:
            raise ValueError(f"--marker {name}: no W:H given and {img_path!r} is not a readable PNG")
        width, height = dims
    return name, img_path, width, height


async def _run(args: argparse.Namespace) -> int:
    note_mcp_src = os.environ.get("NOTE_MCP_SRC", os.path.expanduser("~/.openclaw/external/note-mcp/src"))
    sys.path.insert(0, note_mcp_src)
    try:
        from note_mcp.api.articles import create_draft, generate_image_html
        from note_mcp.api.images import upload_body_image
        from note_mcp.models import ArticleInput, Session
    except Exception as e:  # pragma: no cover -- exercised via the missing-dependency integration path
        print(f"note-create-rich-draft: note_mcp import failed (NOTE_MCP_SRC={note_mcp_src}): {e}", file=sys.stderr)
        return 1

    cookies_file = os.environ.get("NOTE_COOKIES_FILE", os.path.expanduser("~/.cloak/note-work/note-cookies.json"))
    if not os.path.isfile(cookies_file):
        print(f"note-create-rich-draft: NOTE_COOKIES_FILE missing at {cookies_file!r}", file=sys.stderr)
        return 1
    if not os.path.isfile(args.body):
        print(f"note-create-rich-draft: --body path does not exist: {args.body!r}", file=sys.stderr)
        return 1

    with open(cookies_file) as f:
        cookies = json.load(f)
    user_id = os.environ.get("NOTE_USER_ID", "14651590")
    username = os.environ.get("NOTE_USERNAME", "anicca123")
    session = Session(cookies=cookies, user_id=user_id, username=username, created_at=0)

    with open(args.body) as f:
        body = f.read()
    # note-mcp's create_draft() takes the title separately -- strip a leading H1 so it never duplicates
    # as the first body line (same convention lib/note_publish.sh's note_create_draft_from_file uses).
    lines = body.split("\n")
    if lines and lines[0].strip().startswith("# "):
        body = "\n".join(lines[1:]).lstrip("\n")

    visual_urls: dict[str, str] = {}
    for name, img_path, width, height in args.markers:
        marker_line = f"@@{name}@@"
        if marker_line not in body:
            print(f"note-create-rich-draft: marker {marker_line!r} not found in --body (skipping upload)", file=sys.stderr)
            continue
        if not os.path.isfile(img_path):
            print(f"note-create-rich-draft: marker {name!r} image not found at {img_path!r} (leaving marker unresolved)", file=sys.stderr)
            continue
        try:
            image = await upload_body_image(session, img_path, note_id="pending")
        except Exception as e:
            print(f"note-create-rich-draft: upload_body_image failed for {name!r} ({img_path!r}): {e}", file=sys.stderr)
            continue
        fig_html = generate_image_html(image.url, caption="", width=width, height=height)
        body = body.replace(marker_line, fig_html)
        visual_urls[name] = image.url

    try:
        article = await create_draft(session, ArticleInput(title=args.title, body=body, tags=[]))
    except Exception as e:
        print(f"note-create-rich-draft: create_draft failed: {e}", file=sys.stderr)
        return 1

    print(f"NOTE_DRAFT_KEY: {article.key}")
    print(f"NOTE_DRAFT_NUM: {article.id}")
    for name, url in visual_urls.items():
        print(f"NOTE_VISUAL_{name}_URL: {url}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--marker", action="append", default=[], dest="raw_markers")
    args = parser.parse_args()
    try:
        args.markers = [_parse_marker_arg(m) for m in args.raw_markers]
    except ValueError as e:
        print(f"note-create-rich-draft: {e}", file=sys.stderr)
        return 2
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
