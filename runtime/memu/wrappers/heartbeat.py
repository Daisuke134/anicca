#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# wrappers/heartbeat.py — beat-local memU loop used by _shared/heartbeat-memu.sh.
#
# Modes:
#   retrieve   stdin = JSON {queries:[...]}, stdout = JSON {items:[...]}.
#              Replays data/items.jsonl into a fresh service then queries.
#   memorize   stdin = JSON {role,content}[] OR raw text. memorize() + persist
#              each extracted summary to data/items.jsonl (= next-beat memory).
#
# Why this exists: memu-py 1.5.1's sqlite store fails to map list[float] embedding
# columns under sqlmodel ("no matching SQLAlchemy type"). Until upstream fix or
# postgres provisioning, persistence is a JSONL of summaries that get re-memorized
# at the start of each beat. Costs an extra LLM call per beat but is fully correct.
#
# Loud-fail by design (no try/except wrappers swallowing errors).

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

from _common import DATA_DIR, load_service, log_cost

ITEMS_LOG = DATA_DIR / "items.jsonl"
MAX_REPLAY_ITEMS = 80


def _conv_to_text(conv) -> str:
    if isinstance(conv, str):
        return conv
    parts = []
    for msg in conv:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"[{role}] {content}")
    return "\n".join(parts)


def _stage(text: str, prefix: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "resources").mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    p = DATA_DIR / "resources" / f"{prefix}-{ts}-{digest}.txt"
    p.write_text(text, encoding="utf-8")
    return p


async def _replay_into(svc, user: dict | None) -> int:
    """Read items.jsonl, concatenate summaries into one synthetic transcript,
    memorize it so retrieve has context. Returns count replayed."""
    if not ITEMS_LOG.exists():
        return 0
    lines = ITEMS_LOG.read_text(encoding="utf-8").splitlines()
    lines = [ln for ln in lines if ln.strip()]
    if not lines:
        return 0
    items = []
    for ln in lines[-MAX_REPLAY_ITEMS:]:
        try:
            items.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    if not items:
        return 0
    transcript_lines = []
    for it in items:
        s = it.get("summary") or it.get("content") or ""
        if s:
            transcript_lines.append(f"[recall] {s}")
    transcript = "\n".join(transcript_lines)
    if not transcript:
        return 0
    p = _stage(transcript, "replay")
    await svc.memorize(resource_url=str(p), modality="text", user=user)
    return len(items)


def _append_items(items, user: dict | None) -> int:
    n = 0
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with ITEMS_LOG.open("a", encoding="utf-8") as fh:
        for it in items:
            entry = {
                "id": it.get("id"),
                "summary": it.get("summary") or it.get("content"),
                "memory_type": it.get("memory_type"),
                "happened_at": str(it.get("happened_at")) if it.get("happened_at") else None,
                "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "user_id": (user or {}).get("user_id"),
            }
            if not entry["summary"]:
                continue
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            n += 1
    return n


async def _run_memorize(text: str, user: dict | None) -> dict:
    svc = load_service()
    p = _stage(text, "beat")
    started = time.monotonic()
    res = await svc.memorize(resource_url=str(p), modality="text", user=user)
    elapsed = time.monotonic() - started
    items = res.get("items") if isinstance(res, dict) else []
    persisted = _append_items(items or [], user)
    log_cost(
        "heartbeat.memorize",
        elapsed,
        {"input_chars": len(text), "items_extracted": persisted},
    )
    return {"items": items or [], "persisted": persisted}


async def _run_retrieve(queries: list, user: dict | None) -> dict:
    svc = load_service()
    started = time.monotonic()
    replayed = await _replay_into(svc, user)
    norm = [
        q if (isinstance(q, dict) and "content" in q)
        else {"role": "user", "content": q.get("query", "") if isinstance(q, dict) else str(q)}
        for q in queries
    ]
    where = {"user_id": (user or {}).get("user_id")} if user else None
    res = await svc.retrieve(queries=norm, where=where)
    elapsed = time.monotonic() - started
    items = []
    if isinstance(res, dict):
        items = res.get("items") or res.get("results") or []
    log_cost(
        "heartbeat.retrieve",
        elapsed,
        {"results_count": len(items), "replayed": replayed},
    )
    return {"items": items, "replayed": replayed, "raw_keys": list(res.keys()) if isinstance(res, dict) else []}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["memorize", "retrieve"])
    parser.add_argument("--user", default='{"user_id":"anicca-001"}')
    parser.add_argument("--text")
    args = parser.parse_args()

    user = json.loads(args.user) if args.user else None
    raw = args.text if args.text else sys.stdin.read()

    if args.mode == "memorize":
        try:
            data = json.loads(raw)
            text = _conv_to_text(data)
        except json.JSONDecodeError:
            text = raw
        if not text.strip():
            sys.stderr.write("heartbeat.memorize: empty input — skipping\n")
            return 0
        result = asyncio.run(_run_memorize(text, user))
    else:
        data = json.loads(raw) if raw.strip() else {}
        queries = data.get("queries", [])
        if not queries:
            queries = [{"query": data.get("query", "")}] if data.get("query") else []
        if not queries:
            sys.stderr.write("heartbeat.retrieve: no queries — skipping\n")
            sys.stdout.write(json.dumps({"items": [], "replayed": 0}) + "\n")
            return 0
        result = asyncio.run(_run_retrieve(queries, user))

    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
