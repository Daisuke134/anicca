#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# runtime/memu/migrate-from-learnings.py — one-time migration of historical
# learnings into the memU JSONL snapshot at runtime/memu/data/items.jsonl.
#
# Sources (in priority order, all optional):
#   ~/.openclaw/.learnings/LEARNINGS.md
#   ~/.openclaw/.learnings/ERRORS.md
#   ~/.openclaw/.learnings/FEATURE_REQUESTS.md
#   ~/.openclaw/.learnings/*.jsonl   (event-log format)
#
# Strategy: each markdown bullet OR JSONL line becomes one memU memorize() call
# with the line as raw text; extracted items append to data/items.jsonl with a
# migration tag. Re-running is safe: dedup by sha256(summary).

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
import time
from pathlib import Path

WRAPPERS = Path(__file__).resolve().parent / "wrappers"
sys.path.insert(0, str(WRAPPERS))

from _common import DATA_DIR, load_service  # noqa: E402

LEARNINGS_DIR = Path.home() / ".openclaw" / ".learnings"
ITEMS_LOG = DATA_DIR / "items.jsonl"
USER = {"user_id": "anicca-001"}


def _existing_hashes() -> set[str]:
    if not ITEMS_LOG.exists():
        return set()
    out: set[str] = set()
    for ln in ITEMS_LOG.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        s = e.get("summary") or ""
        if s:
            out.add(hashlib.sha256(s.encode("utf-8")).hexdigest())
    return out


def _extract_lines() -> list[tuple[str, str]]:
    """Return (source, text) tuples, one per migratable unit."""
    out: list[tuple[str, str]] = []
    if not LEARNINGS_DIR.exists():
        return out
    for md in sorted(LEARNINGS_DIR.glob("*.md")):
        for raw in md.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith(("#", "---", "```")):
                continue
            line = re.sub(r"^[-*]\s+", "", line)
            line = re.sub(r"^\d+\.\s+", "", line)
            if len(line) < 12:
                continue
            out.append((md.name, line))
    for jl in sorted(LEARNINGS_DIR.glob("*.jsonl")):
        for raw in jl.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            text = obj.get("summary") or obj.get("text") or obj.get("body") or obj.get("learning")
            if text and len(str(text)) >= 12:
                out.append((jl.name, str(text)))
    return out


async def _migrate_one(svc, text: str) -> list[dict]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "resources").mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    p = DATA_DIR / "resources" / f"migrate-{ts}-{digest}.txt"
    p.write_text(text, encoding="utf-8")
    res = await svc.memorize(resource_url=str(p), modality="text", user=USER)
    return res.get("items", []) if isinstance(res, dict) else []


async def _amain() -> int:
    lines = _extract_lines()
    if not lines:
        print(f"no migratable entries under {LEARNINGS_DIR}")
        return 0
    print(f"migrating {len(lines)} units from {LEARNINGS_DIR}")

    svc = load_service()
    seen = _existing_hashes()
    new_count = 0
    with ITEMS_LOG.open("a", encoding="utf-8") as fh:
        for idx, (src, text) in enumerate(lines, 1):
            items = await _migrate_one(svc, text)
            for it in items:
                summary = it.get("summary") or it.get("content")
                if not summary:
                    continue
                h = hashlib.sha256(summary.encode("utf-8")).hexdigest()
                if h in seen:
                    continue
                seen.add(h)
                entry = {
                    "id": it.get("id"),
                    "summary": summary,
                    "memory_type": it.get("memory_type"),
                    "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "source": src,
                    "migration": True,
                    "user_id": USER["user_id"],
                }
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
                new_count += 1
            if idx % 5 == 0:
                print(f"  {idx}/{len(lines)} done, {new_count} new items")
    print(f"migration complete: {new_count} new items in {ITEMS_LOG}")
    return 0


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    sys.exit(main())
