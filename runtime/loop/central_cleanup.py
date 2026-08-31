#!/usr/bin/env python3
"""Central owner for shared immutable Mr.bot release garbage collection."""

from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.loop.loop_cleanup import gc_releases


def host_cleanup_command(root: Path, home: Path) -> list[str]:
    return [sys.executable, str(root / "skills/self/disk-cleanup/disk_cleanup.py"),
            "--home", str(home), "--state-dir", str(home / ".openclaw/state")]


def loaded_release_roots(agents_dir: Path, releases_root: Path) -> set[Path]:
    protected = set()
    base = releases_root.resolve()
    for plist_path in agents_dir.glob("ai.anicca.*.plist"):
        try:
            with plist_path.open("rb") as handle:
                plist = plistlib.load(handle)
        except Exception:
            continue
        for value in map(str, plist.get("ProgramArguments") or []):
            candidate = Path(os.path.expanduser(value))
            try:
                resolved = candidate.resolve(strict=True)
                relative = resolved.relative_to(base)
            except (OSError, ValueError):
                continue
            if relative.parts:
                release = base / relative.parts[0]
                if release.is_dir(): protected.add(release.resolve())
    return protected


def open_release_roots(releases_root: Path) -> set[Path]:
    """Return release roots referenced by any open file or process cwd."""
    completed = subprocess.run(
        ["lsof", "-Fn"],
        capture_output=True, text=True, timeout=120,
    )
    if completed.returncode not in (0, 1):
        raise OSError(f"release lsof failed: {completed.returncode}")
    base = releases_root.resolve()
    protected: set[Path] = set()
    for line in completed.stdout.splitlines():
        if not line.startswith("n"):
            continue
        try:
            relative = Path(line[1:]).resolve().relative_to(base)
        except (OSError, ValueError):
            continue
        if relative.parts:
            release = base / relative.parts[0]
            if release.is_dir():
                protected.add(release.resolve())
    return protected


def release_gc(releases: Path, current: Path, agents: Path, keep: int) -> dict:
    """Collect releases while pinning every generation referenced by launchd."""
    protected = loaded_release_roots(agents, releases) | open_release_roots(releases)
    protected_file = Path(os.environ.get(
        "MR_BOT_PROTECTED_RELEASES", "~/.local/state/mr-bot/protected-releases.json")).expanduser()
    try:
        values = json.loads(protected_file.read_text())
        if isinstance(values, list):
            protected.update(Path(value).expanduser().resolve() for value in values if isinstance(value, str))
    except (OSError, json.JSONDecodeError):
        pass
    result = gc_releases(releases, current, keep=keep, protected=protected)
    result["protected_release_count"] = len(protected)
    return result


def main() -> int:
    home = Path.home()
    loops_root = Path(os.environ.get("LOOPS_ROOT", "~/loops")).expanduser()
    releases = loops_root / "releases"
    current = loops_root / "current"
    agents = Path(os.environ.get(
        "MR_BOT_LAUNCH_AGENTS_DIR", "~/Library/LaunchAgents")).expanduser()
    if sys.argv[1:] == ["--release-gc-only"]:
        try:
            result = release_gc(releases, current, agents,
                                keep=int(os.environ.get("MR_BOT_RELEASE_KEEP", "5")))
        except (OSError, ValueError) as error:
            print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True)); return 1
        result["ok"] = result["errors"] == 0
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if result["ok"] else 1
    try:
        host_process = subprocess.run(
            host_cleanup_command(ROOT, home), capture_output=True, text=True, timeout=240,
        )
        host_result = json.loads(host_process.stdout.splitlines()[-1]) if host_process.stdout.strip() else {}
        host_ok = host_process.returncode == 0 and isinstance(host_result, dict)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, IndexError) as error:
        host_ok, host_result = False, {"error": str(error)}
    try:
        result = release_gc(releases, current, agents,
                            keep=int(os.environ.get("MR_BOT_RELEASE_KEEP", "5")))
    except (OSError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True)); return 1
    result.update({"ok": result["errors"] == 0 and host_ok,
                   "host_cleanup": host_result,
                   "shared_cache_candidates": 0, "orphan_candidates": 0})
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
