#!/usr/bin/env python3
"""Append direct OpenAI API usage to the shared Anicca agent telemetry ledger."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_LEDGER = (
    Path.home() / ".local" / "state" / "anicca" / "telemetry" / "agent-usage.jsonl"
)


def nonnegative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", required=True)
    parser.add_argument("--task-label", required=True)
    parser.add_argument("--task-class", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--operation", required=True)
    args = parser.parse_args()

    try:
        response = json.load(sys.stdin)
        usage = response["usage"]
        input_tokens = nonnegative_int(usage.get("prompt_tokens"))
        output_tokens = nonnegative_int(usage.get("completion_tokens"))
        total_tokens = nonnegative_int(usage.get("total_tokens"))
        cached_tokens = nonnegative_int(
            (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
        ) or 0
        if input_tokens is None or output_tokens is None or total_tokens is None:
            raise ValueError("response has no complete token usage")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"record_openai_usage: invalid response: {error}", file=sys.stderr)
        return 2

    timestamp = datetime.now(timezone.utc).isoformat()
    event_seed = f"{timestamp}:{args.loop}:{args.task_label}:{args.model}:{total_tokens}"
    event = {
        "version": 1,
        "event_id": hashlib.sha256(event_seed.encode()).hexdigest()[:24],
        "timestamp": timestamp,
        "loop": args.loop,
        "task_label": args.task_label,
        "task_class": args.task_class,
        "attempt": 1,
        "provider": "openai-api",
        "provider_name": "openai",
        "model": args.model,
        "upstream_model": args.model,
        "effort": None,
        "status": "success",
        "error_class": None,
        "duration_ms": 0,
        "measurement": "provider_reported",
        "tokens": {
            "input": input_tokens,
            "cached_input": cached_tokens,
            "cache_creation_input": 0,
            "output": output_tokens,
            "reasoning_output": 0,
            "total": total_tokens,
        },
        "provider_cost_usd": None,
        "cost_basis": "unavailable",
        "gen_ai": {
            "operation_name": args.operation,
            "provider_name": "openai",
            "request_model": args.model,
        },
    }

    ledger = Path(os.environ.get("ANICCA_USAGE_LEDGER", DEFAULT_LEDGER)).expanduser()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
