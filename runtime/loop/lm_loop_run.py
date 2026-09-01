#!/usr/bin/env python3
"""Per-loop cleanup boundary followed by exact immutable entrypoint exec."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from runtime.loop.loop_cleanup import cleanup_run_root
from runtime.loop.macos_loop_registry import validate_registry
from runtime.loop.runtime_event import append_runtime_event, build_runtime_event, build_runtime_start_event


def prepare_loop_run(registry: dict, loop_id: str, release_root: Path, *,
                     active_run_ids: set[str], now: float | None = None) -> tuple[list[str], dict]:
    validate_registry(registry)
    entry = registry["loops"].get(loop_id)
    if not isinstance(entry, dict):
        raise ValueError(f"unknown loop id: {loop_id}")
    executable = release_root.resolve() / entry["entrypoint"]
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError(f"entrypoint missing or not executable: {entry['entrypoint']}")
    totals = {"evaluated_runs": 0, "removed_runs": 0, "reclaimed_bytes": 0,
              "preserved_runs": 0, "protected_deletions": 0, "errors": 0}
    seen = set()
    for value in (entry["state_root"], entry["log_root"]):
        root = Path(os.path.expanduser(value)).resolve()
        if root in seen:
            continue
        seen.add(root)
        result = cleanup_run_root(root, entry["cleanup"], active_run_ids, now=now)
        for key in totals:
            totals[key] += result[key]
    return [str(executable)], totals


def reset_loop_scratch(state_root: Path, loop_id: str) -> Path:
    """Private scratch dir per loop, wiped every run so subprocess temp files cannot leak."""
    scratch = state_root / "loop-tmp" / loop_id
    if scratch.is_dir() and not scratch.is_symlink():
        shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True, exist_ok=True, mode=0o700)
    return scratch


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":")); handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.chmod(name, 0o600); os.replace(name, path)
    finally:
        try: os.unlink(name)
        except FileNotFoundError: pass


def _run_entrypoint(command: list[str], env: dict[str, str] | None = None) -> int:
    process = subprocess.Popen(command, start_new_session=True, env=env)
    previous = {}

    def forward(signum, _frame):
        if process.poll() is None:
            try:
                os.killpg(process.pid, signum)
            except ProcessLookupError:
                pass

    for signum in (signal.SIGTERM, signal.SIGINT):
        previous[signum] = signal.signal(signum, forward)
    try:
        return_code = process.wait()
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    return return_code if return_code >= 0 else 128 - return_code


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) != 2:
        print("usage: lm-loop-run <loop-id> <release-root>", file=sys.stderr); return 64
    loop_id, release_value = args
    release_root = Path(release_value).resolve()
    try:
        registry = json.loads((release_root / "config/loop-registry.json").read_text())
        manifest = json.loads((release_root / "RELEASE.json").read_text())
        if not isinstance(manifest.get("sha"), str) or len(manifest["sha"]) != 40:
            raise ValueError("invalid release manifest SHA")
        active = {value for value in os.environ.get("LIFE_MANAGER_ACTIVE_RUN_IDS", "").split(",") if value}
        command, cleanup = prepare_loop_run(
            registry, loop_id, release_root, active_run_ids=active, now=time.time())
        entry = registry["loops"][loop_id]
        receipt = Path(os.path.expanduser(entry["state_root"])) / "cleanup-latest.json"
        _atomic_json(receipt, {"version": 1, "loop_id": loop_id,
                              "release_sha": manifest["sha"], **cleanup})
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"lm-loop-run: {error}", file=sys.stderr); return 78
    run_id = os.environ.get("LIFE_MANAGER_RUN_ID") or f"{time.time_ns():x}-{os.getpid()}"
    event_path = Path(os.path.expanduser(entry["state_root"])) / "events.jsonl"
    try:
        append_runtime_event(event_path, build_runtime_start_event(
            loop_id=loop_id, domain=entry["domain"], run_id=run_id,
            release_sha=manifest["sha"], provider=entry["provider_route"],
            profile_alias=None, effect_class=entry["effect_class"],
        ))
    except (OSError, ValueError) as error:
        print(f"lm-loop-run: start event failed: {error}", file=sys.stderr)
    scratch = reset_loop_scratch(Path(os.path.expanduser(entry["state_root"])), loop_id)
    try:
        return_code = _run_entrypoint(
            command,
            env={
                **os.environ,
                "LIFE_MANAGER_RELEASE_ROOT": str(release_root),
                "TMPDIR": f"{scratch}/",
                "NPM_CONFIG_CACHE": str(scratch / "npm-cache"),
            },
        )
    finally:
        # Scratch is never evidence. Every loop owns and removes its temporary
        # downloads, package caches, and build products when its pass ends.
        shutil.rmtree(scratch, ignore_errors=True)
    try:
        event = build_runtime_event(
            loop_id=loop_id, domain=entry["domain"], run_id=run_id,
            release_sha=manifest["sha"], provider=entry["provider_route"],
            profile_alias=None, effect_class=entry["effect_class"],
            succeeded=return_code == 0,
            blocker=None if return_code == 0 else f"entrypoint_exit_{return_code}",
            evidence_scheme="lm-loop",
        )
        append_runtime_event(event_path, event)
    except (OSError, ValueError) as error:
        print(f"lm-loop-run: terminal event failed: {error}", file=sys.stderr)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
