#!/usr/bin/env python3
"""Publish a delivery artifact as a shared Google Doc, for buyers who ask for one.

§EM' (2026-08-09). Real precedent: order 91000001, buyer message 「納品はグーグル
ドキュメントでお願いします」. The manual round trip that satisfied it was two `gog`
calls -- upload with --convert-to doc, then share --to anyone --role commenter --
run by hand. This script is that same two-call round trip made deterministic and
callable by the PAID_WORK builder, which already has exec/bash access (see
agent-runner's OPENCLAW_WRITE_TOOLS) and already reads the buyer's own words, so
it -- not this script -- decides WHETHER the buyer asked for Google Docs.

Fail-closed: any `gog` error (auth, quota, a locked file) comes back as
{"ok": false, "reason": "..."} on stdout and a nonzero exit, never a partial or
invented link.

★ --replace is real but narrower than it looks. ★ Live-verified 2026-08-09: `gog
drive upload --replace` refuses outright once the target is already a native
Google Doc --
    cannot replace content for Google Workspace files (mimeType=application/vnd.google-apps.document)
-- which is exactly what --convert-to doc produces. A revision therefore cannot
reuse the first delivery's link; it fails closed here with that same gog stderr
as the reason, and the caller creates a new doc (new link) instead of silently
lying about which one is current.
# ponytail: revision path always creates a fresh doc/link (gog has no Docs-API
# write path here); upgrade to `gog docs` content replace if that ships.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

GOG = "gog"
DEFAULT_ACCOUNT = os.environ.get("GIG_GOG_ACCOUNT", "operator@example.com")
SHARE_ROLE = "commenter"

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def upload_argv(
    *, input_path: Path, title: str, account: str, replace: str | None
) -> list[str]:
    argv = [GOG, "drive", "upload", str(input_path), "-a", account, "--json"]
    if replace:
        argv += ["--replace", replace]
    else:
        argv += ["--convert-to", "doc", "--name", title]
    return argv


def share_argv(*, file_id: str, account: str) -> list[str]:
    return [
        GOG, "drive", "share", file_id,
        "--to", "anyone", "--role", SHARE_ROLE,
        "-a", account, "--json", "-y",
    ]


def _run_json(argv: list[str], runner: Runner) -> dict[str, Any]:
    completed = runner(
        argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
        timeout=120, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "gog_failed").strip()[:500])
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gog_output_not_json:{exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("gog_output_not_object")
    return payload


def publish(
    *,
    input_path: Path,
    title: str,
    account: str = DEFAULT_ACCOUNT,
    replace: str | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    if not input_path.is_file() or input_path.stat().st_size <= 0:
        return {"ok": False, "reason": f"missing_or_empty_input:{input_path}"}
    try:
        upload = _run_json(
            upload_argv(input_path=input_path, title=title, account=account, replace=replace),
            runner,
        )
    except RuntimeError as exc:
        return {"ok": False, "reason": str(exc)}
    file_info = upload.get("file") if isinstance(upload.get("file"), dict) else {}
    file_id = str(file_info.get("id") or "")
    if not file_id:
        return {"ok": False, "reason": "gog_upload_no_file_id"}
    if replace:
        # --replace preserves the existing share, per gog's own flag description --
        # no re-share call, no new link.
        link = str(file_info.get("webViewLink") or "")
        if not link:
            return {"ok": False, "reason": "gog_replace_no_link"}
        return {"ok": True, "file_id": file_id, "link": link, "replaced": True}
    try:
        share = _run_json(share_argv(file_id=file_id, account=account), runner)
    except RuntimeError as exc:
        return {"ok": False, "reason": str(exc), "file_id": file_id}
    link = str(share.get("link") or file_info.get("webViewLink") or "")
    if not link:
        return {"ok": False, "reason": "gog_share_no_link", "file_id": file_id}
    return {"ok": True, "file_id": file_id, "link": link, "replaced": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    parser.add_argument(
        "--replace", default=None,
        help="existing Drive file id to update instead of creating a new doc "
             "(fails closed for an already-converted Google Doc; see module docstring)",
    )
    args = parser.parse_args(argv)
    result = publish(
        input_path=args.input.expanduser().resolve(),
        title=args.title,
        account=args.account,
        replace=args.replace,
    )
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
