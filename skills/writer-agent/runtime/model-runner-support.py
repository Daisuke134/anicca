#!/usr/bin/env python3
"""Small state, classification, and redaction helpers for model-runner.sh."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        value = {}
    if not isinstance(value, dict):
        value = {}
    entries = value.get("entries")
    return {"version": 1, "entries": entries if isinstance(entries, dict) else {}}


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def with_lock(path: Path, mutation) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = load(path)
        mutation(state)
        atomic_write(path, state)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return state


def health_key(provider: str, mode: str) -> str:
    return f"{provider}:{mode}"


def eligible(args: argparse.Namespace) -> int:
    state = load(args.file)
    entry = state["entries"].get(health_key(args.provider, args.mode), {})
    try:
        unhealthy_until = int(entry.get("unhealthy_until", 0))
    except (AttributeError, TypeError, ValueError):
        unhealthy_until = 0
    if unhealthy_until > args.now:
        print("cooldown")
        return 1
    print("eligible")
    return 0


def record(args: argparse.Namespace) -> int:
    key = health_key(args.provider, args.mode)

    def mutation(state: dict[str, Any]) -> None:
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(args.now))
        if args.status == "success":
            state["entries"][key] = {
                "status": "healthy",
                "last_success_at": now_iso,
                "run_id": args.run_id,
            }
            return
        entry: dict[str, Any] = {
            "status": args.status,
            "error_class": args.error_class,
            "last_failure_at": now_iso,
            "run_id": args.run_id,
        }
        if args.status == "retryable":
            entry["unhealthy_until"] = args.now + args.cooldown
        state["entries"][key] = entry

    with_lock(args.file, mutation)
    return 0


def classify(args: argparse.Namespace) -> int:
    text = ""
    for path in (args.stdout, args.stderr):
        try:
            text += "\n" + path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    lowered = text.lower()
    if args.return_code == 124 or re.search(r"\b(timed?\s*out|timeout)\b", lowered):
        print("timeout")
    elif "weekly limit" in lowered or "usage limit" in lowered or "credit balance" in lowered:
        print("quota")
    elif re.search(r"\b429\b|rate[_ -]?limit|too many requests", lowered):
        print("rate_limit")
    elif re.search(r"\b(?:http\s*)?5\d\d\b", lowered):
        print("server_5xx")
    elif any(
        token in lowered
        for token in (
            "overloaded",
            "service unavailable",
            "provider unavailable",
            "temporarily unavailable",
            "model unavailable",
            "model is not available",
        )
    ):
        print("provider_unavailable")
    elif any(
        token in lowered
        for token in (
            "failed to authenticate",
            "authentication failed",
            "oauth session expired",
            "could not be refreshed",
            "not logged in",
        )
    ):
        print("auth")
    elif any(
        token in lowered
        for token in (
            "connection reset",
            "connection refused",
            "network is unreachable",
            "network error",
            "transport error",
            "econnreset",
            "econnrefused",
            "fetch failed",
        )
    ):
        print("connection")
    else:
        print("fatal")
    return 0


def secret_values() -> list[bytes]:
    exact = {
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "OPENAI_API_KEY",
        "CODEX_API_KEY",
        "CLI_PROXY_API_KEY",
    }
    values: set[bytes] = set()
    for name, value in os.environ.items():
        upper = name.upper()
        sensitive = (
            name in exact
            or upper.endswith(("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD"))
            or "CREDENTIAL" in upper
        )
        if sensitive and len(value) >= 4:
            values.add(value.encode())
    return sorted(values, key=len, reverse=True)


def redact_stream() -> int:
    secrets = secret_values()
    maximum = max((len(secret) for secret in secrets), default=0)
    pending = b""
    reader = sys.stdin.buffer
    writer = sys.stdout.buffer
    while True:
        chunk = reader.read(4096)
        if not chunk:
            break
        pending += chunk
        # Replace before slicing: a secret that starts before the held-back
        # tail but crosses into it would otherwise be split and never masked.
        for secret in secrets:
            pending = pending.replace(secret, b"[REDACTED]")
        stable_end = len(pending) if maximum == 0 else max(0, len(pending) - maximum + 1)
        stable, pending = pending[:stable_end], pending[stable_end:]
        writer.write(stable)
        writer.flush()
    for secret in secrets:
        pending = pending.replace(secret, b"[REDACTED]")
    writer.write(pending)
    writer.flush()
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    subparsers = root.add_subparsers(dest="command", required=True)

    eligible_parser = subparsers.add_parser("eligible")
    eligible_parser.add_argument("--file", required=True, type=Path)
    eligible_parser.add_argument("--provider", required=True)
    eligible_parser.add_argument("--mode", required=True)
    eligible_parser.add_argument("--now", type=int, default=lambda: int(time.time()))
    eligible_parser.set_defaults(function=eligible)

    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--file", required=True, type=Path)
    record_parser.add_argument("--provider", required=True)
    record_parser.add_argument("--mode", required=True)
    record_parser.add_argument("--status", choices=("success", "retryable", "fatal"), required=True)
    record_parser.add_argument("--error-class", default="")
    record_parser.add_argument("--cooldown", type=int, default=21600)
    record_parser.add_argument("--run-id", default="unknown")
    record_parser.add_argument("--now", type=int, default=lambda: int(time.time()))
    record_parser.set_defaults(function=record)

    classify_parser = subparsers.add_parser("classify")
    classify_parser.add_argument("--return-code", type=int, required=True)
    classify_parser.add_argument("--stdout", type=Path, required=True)
    classify_parser.add_argument("--stderr", type=Path, required=True)
    classify_parser.set_defaults(function=classify)

    redact_parser = subparsers.add_parser("redact")
    redact_parser.set_defaults(function=lambda _args: redact_stream())
    return root


def main() -> int:
    args = parser().parse_args()
    if callable(getattr(args, "now", None)):
        args.now = args.now()
    return args.function(args)


if __name__ == "__main__":
    raise SystemExit(main())
