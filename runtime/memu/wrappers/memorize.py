#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# wrappers/memorize.py — feed a conversation to memU and persist memory items.
#
# Usage:
#   python wrappers/memorize.py < conv.json
#   python wrappers/memorize.py path/to/conv.json
#   python wrappers/memorize.py --text "raw text" --user '{"user_id":"daisuke"}'
#
# Conversation JSON = list of {role, content}. Persisted to ~/.openclaw/state/memu-resources/.

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

from _common import DATA_DIR, load_service, log_cost, stderr


def _conv_to_text(conv) -> str:
    if isinstance(conv, str):
        return conv
    parts = []
    for msg in conv:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"[{role}] {content}")
    return "\n".join(parts)


def _stage_resource(text: str) -> str:
    resources_dir = DATA_DIR / "resources"
    resources_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    name = f"conv-{ts}-{digest}.txt"
    path = resources_dir / name
    path.write_text(text, encoding="utf-8")
    # memU blob layer treats local paths (not file:// URIs) as Path objects.
    return str(path.resolve())


async def _run(text: str, user: dict | None) -> dict:
    svc = load_service()
    resource_url = _stage_resource(text)
    started = time.monotonic()
    result = await svc.memorize(
        resource_url=resource_url,
        modality="text",
        user=user,
    )
    elapsed = time.monotonic() - started
    items = result.get("items") if isinstance(result, dict) else []
    log_cost(
        "memorize",
        elapsed,
        {"input_chars": len(text), "items_extracted": len(items) if items is not None else None},
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", help="path to conversation JSON; default stdin")
    parser.add_argument("--text", help="raw text instead of conversation list")
    parser.add_argument("--user", help="JSON user scope, e.g. '{\"user_id\":\"daisuke\"}'")
    args = parser.parse_args()

    if args.text is not None:
        text = args.text
    else:
        if args.path:
            raw = Path(args.path).read_text(encoding="utf-8")
        else:
            raw = sys.stdin.read()
        try:
            data = json.loads(raw)
            text = _conv_to_text(data)
        except json.JSONDecodeError:
            text = raw

    user = json.loads(args.user) if args.user else None
    try:
        result = asyncio.run(_run(text, user))
    except Exception as exc:
        log_cost("memorize", 0.0, {"input_chars": len(text), "ok": False})
        stderr(f"memorize failed: {type(exc).__name__}: {exc}")
        return 2

    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
