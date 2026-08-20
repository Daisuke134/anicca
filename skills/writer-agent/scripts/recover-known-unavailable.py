#!/usr/bin/env python3
"""Re-arm only unavailable publication failures with a deterministic live proof."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
NOTE_RUNTIME_ERROR = "note_mcp_venv_missing"
SUBSTACK_BROWSER_ERROR = "substack_editor_redirect_own_eyes_unverified"
SUBSTACK_PROBE_TIMEOUT_SECONDS = 45


def run(command: list[str], *, env: dict[str, str], timeout: int = 180) -> bool:
    try:
        return (
            subprocess.run(
                command,
                env=env,
                check=False,
                timeout=timeout,
            ).returncode
            == 0
        )
    except (OSError, subprocess.TimeoutExpired):
        return False


def managed_env(state: dict[str, Any], state_path: Path) -> dict[str, str] | None:
    run_dir = Path(str(state.get("run_dir", "")))
    ledger = str(state.get("ledger_path", ""))
    if (
        not run_dir.is_dir()
        or state_path != run_dir / "gates" / "publication-state.json"
        or not ledger
    ):
        return None
    return {
        **os.environ,
        "ARTICLE_AUTOPUBLISH": "1",
        "ARTICLE_RUN_DIR": str(run_dir),
        "ARTICLE_PUBLICATION_STATE": str(state_path),
        "ARTICLE_LEDGER": ledger,
        "ARTICLE_GATES_LOG": str(run_dir / "gates" / "article-gates.log"),
    }


def recover_state(state_path: Path) -> None:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        return
    if not isinstance(state, dict):
        return
    env = managed_env(state, state_path)
    if env is None:
        return

    pairs = state.get("pairs", {})
    if not isinstance(pairs, dict):
        return
    guard = os.environ.get(
        "ARTICLE_PUBLICATION_GUARD", str(SCRIPT_DIR / "publication-guard.py")
    )

    note = pairs.get("note/ja", {})
    if (
        isinstance(note, dict)
        and note.get("status") == "unavailable"
        and note.get("error") == NOTE_RUNTIME_ERROR
        and not note.get("receipt")
    ):
        note_dir = os.environ.get(
            "NOTE_MCP_DIR", str(Path.home() / ".openclaw" / "external" / "note-mcp")
        )
        runtime_guard = os.environ.get(
            "ARTICLE_NOTE_RUNTIME_GUARD",
            str(SCRIPT_DIR / "ensure-note-mcp-runtime.sh"),
        )
        if run(["bash", runtime_guard, note_dir], env=env):
            run(
                ["python3", guard, "clear-unavailable", "--pair", "note/ja"],
                env=env,
            )

    identities = state.get("destination_identities", {})
    if not isinstance(identities, dict):
        identities = {}
    for pair in ("substack/ja", "substack/en"):
        entry = pairs.get(pair, {})
        if not isinstance(entry, dict):
            continue
        target = str(entry.get("target", ""))
        if (
            entry.get("status") != "unavailable"
            or entry.get("error") != SUBSTACK_BROWSER_ERROR
            or entry.get("receipt")
            or entry.get("target_kind") != "substack-draft-id"
            or re.fullmatch(r"[1-9][0-9]*", target) is None
        ):
            continue
        account = str(
            identities.get(pair, "aniccabuddha.substack.com")
        ).strip().lower()
        if re.fullmatch(r"[a-z0-9-]+\.substack\.com", account) is None:
            continue
        verifier = os.environ.get(
            "ARTICLE_RENDER_VERIFY", str(SCRIPT_DIR / "render-verify-draft.sh")
        )
        lang = pair.split("/", 1)[1]
        url = f"https://{account}/publish/post/{target}"
        if run(
            [
                verifier,
                "--platform",
                "substack",
                "--url",
                url,
                "--lang",
                lang,
            ],
            env=env,
            timeout=SUBSTACK_PROBE_TIMEOUT_SECONDS,
        ):
            run(
                [
                    "python3",
                    guard,
                    "register-intent",
                    "--pair",
                    pair,
                    "--target-kind",
                    "substack-draft-id",
                    "--target",
                    target,
                ],
                env=env,
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    pattern = (
        f"runs/{args.run_id}/gates/publication-state.json"
        if args.run_id
        else "runs/*/gates/publication-state.json"
    )
    for state_path in sorted(args.state_root.glob(pattern)):
        recover_state(state_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
