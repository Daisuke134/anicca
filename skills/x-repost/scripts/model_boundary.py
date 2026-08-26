#!/usr/bin/env python3
"""Prepare isolated Codex auth and classify deterministic provider failures."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def prepare(home: Path, auth: Path) -> Path:
    try:
        auth_source = auth.expanduser().resolve(strict=True)
    except OSError as error:
        raise ValueError("automation auth unavailable") from error
    if not auth_source.is_file():
        raise ValueError("automation auth unavailable")
    automation_home = home.expanduser()
    automation_home.mkdir(parents=True, exist_ok=True, mode=0o700)
    automation_home.chmod(0o700)
    auth_target = automation_home / "auth.json"
    if auth_target.exists() or auth_target.is_symlink():
        try:
            if auth_target.resolve(strict=True) != auth_source:
                raise ValueError("auth target mismatch")
        except OSError as error:
            raise ValueError("auth target invalid") from error
    else:
        auth_target.symlink_to(auth_source)
    return automation_home.resolve()


def classify(paths: list[Path], returncode: int | None) -> str:
    messages = []
    for item in paths:
        if not item.is_file():
            continue
        for line in item.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                messages.append(line)
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") == "error":
                messages.append(str(event.get("message") or ""))
            elif event.get("type") == "turn.failed":
                error = event.get("error")
                messages.append(str(error.get("message") if isinstance(error, dict) else error or ""))
    text = "\n".join(messages).lower()
    if any(token in text for token in (
        "failed to lookup address information", "connection failed",
        "error sending request", "stream disconnected before completion",
    )):
        return "network"
    if returncode == 124:
        return "timeout"
    if any(token in text for token in (
        "unauthorized", "invalid credentials", "invalid token",
        "authentication session expired", "token refresh failed",
    )):
        return "auth"
    if any(token in text for token in (
        "usage limit", "usage_limit", "weekly limit", "quota",
        "rate limit", "rate_limit", "temporarily unavailable", "overloaded",
    )):
        return "quota"
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_cmd = commands.add_parser("prepare")
    prepare_cmd.add_argument("--home", required=True, type=Path)
    prepare_cmd.add_argument("--auth", required=True, type=Path)
    classify_cmd = commands.add_parser("classify")
    classify_cmd.add_argument("paths", nargs="*", type=Path)
    classify_cmd.add_argument("--returncode", type=int)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            print(prepare(args.home, args.auth))
        else:
            print(classify(args.paths, args.returncode))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return os.EX_CONFIG
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
