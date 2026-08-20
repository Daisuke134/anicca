#!/usr/bin/env python3
"""Execute one persisted, already-preflighted staging row for a missing target."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


TARGET_KINDS = {
    "note/ja": "note-key",
    "devto/en": "devto-article-id",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", required=True, choices=tuple(TARGET_KINDS))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--ledger", required=True)
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    state_path = Path(args.state).resolve()
    ledger_path = Path(args.ledger).resolve()
    manifest_path = run_dir / "gates" / "platform-dispatch.jsonl"
    state = json.loads(state_path.read_text())
    if args.pair in state.get("pairs", {}):
        raise SystemExit(f"refuse initialization: {args.pair} already has a persisted pair")

    platform, lang = args.pair.split("/", 1)
    rows = [
        json.loads(line)
        for line in manifest_path.read_text().splitlines()
        if line.strip()
    ]
    matching = [
        row
        for row in rows
        if row.get("platform") == platform and row.get("lang") == lang
    ]
    if len(matching) != 1:
        raise SystemExit(
            f"refuse initialization: expected one {args.pair} manifest row, got {len(matching)}"
        )
    row = matching[0]
    argv = row.get("argv")
    persisted_env = row.get("env")
    if not isinstance(argv, list) or not argv or not all(
        isinstance(value, str) and value for value in argv
    ):
        raise SystemExit("refuse initialization: invalid argv")
    if not isinstance(persisted_env, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in persisted_env.items()
    ):
        raise SystemExit("refuse initialization: invalid env")

    required_paths = {
        "ARTICLE_RUN_DIR": run_dir,
        "ARTICLE_PUBLICATION_STATE": state_path,
        "ARTICLE_LEDGER": ledger_path,
    }
    for key, expected in required_paths.items():
        actual = persisted_env.get(key)
        if not actual or Path(actual).resolve() != expected:
            raise SystemExit(
                f"refuse initialization: manifest {key} does not match authoritative plan"
            )
    for key, expected in {
        "ARTICLE_AUTOPUBLISH": "1",
        "ARTICLE_PUBLISH_PAIR": args.pair,
    }.items():
        if persisted_env.get(key) != expected:
            raise SystemExit(
                f"refuse initialization: manifest {key} does not match authoritative plan"
            )

    env = os.environ.copy()
    env.update(persisted_env)
    completed = subprocess.run(argv, env=env, check=False)
    if completed.returncode != 0:
        return completed.returncode

    updated = json.loads(state_path.read_text())
    pair = updated.get("pairs", {}).get(args.pair, {})
    if (
        pair.get("status") != "intent"
        or pair.get("target_kind") != TARGET_KINDS[args.pair]
        or not pair.get("target")
    ):
        raise SystemExit(
            f"managed staging returned success without a durable {args.pair} intent"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
