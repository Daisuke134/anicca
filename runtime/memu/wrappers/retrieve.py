#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# wrappers/retrieve.py — query memU and return ranked items.
#
# Usage:
#   echo '{"queries":[{"query":"Tanaka deadline"}],"top_k":5}' | python wrappers/retrieve.py
#   python wrappers/retrieve.py --query "Tanaka deadline" --top-k 5

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time

from _common import load_service, log_cost, stderr


def _normalize_queries(raw: list) -> list[dict]:
    """memU expects [{"role": "user", "content": "<text>"}, ...]; accept
    {"query": "..."} shorthand and lift it into that shape."""
    out: list[dict] = []
    for q in raw:
        if isinstance(q, str):
            out.append({"role": "user", "content": q})
        elif isinstance(q, dict):
            if "content" in q:
                out.append(q)
            elif "query" in q:
                out.append({"role": q.get("role", "user"), "content": str(q["query"])})
    return out


async def _run(queries: list, where: dict | None) -> dict:
    svc = load_service()
    queries = _normalize_queries(queries)
    if not queries:
        raise ValueError("no valid queries after normalization")
    started = time.monotonic()
    result = await svc.retrieve(queries=queries, where=where)
    elapsed = time.monotonic() - started

    items = []
    if isinstance(result, dict):
        items = result.get("items") or result.get("results") or []
    log_cost(
        "retrieve",
        elapsed,
        {
            "input_chars": sum(len(q.get("query", "")) for q in queries),
            "results_count": len(items) if isinstance(items, list) else None,
        },
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", help="single query string")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--user", help="JSON user filter, e.g. '{\"user_id\":\"daisuke\"}'")
    args = parser.parse_args()

    if args.query:
        queries = [{"query": args.query}]
        where = json.loads(args.user) if args.user else None
    else:
        raw = sys.stdin.read()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            stderr(f"invalid stdin JSON: {exc}")
            return 2
        if isinstance(data, dict):
            queries = data.get("queries") or [{"query": data.get("query", "")}]
            where = data.get("where") or data.get("user")
        else:
            queries = data
            where = None

    if not queries or not any(q.get("query") for q in queries):
        stderr("no queries provided")
        return 2

    try:
        result = asyncio.run(_run(queries, where))
    except Exception as exc:
        log_cost("retrieve", 0.0, {"results_count": 0, "ok": False})
        stderr(f"retrieve failed: {type(exc).__name__}: {exc}")
        return 2

    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
