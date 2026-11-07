#!/usr/bin/env python3
"""Own a headless CloakBrowser context for a Maritime tenant identity.

Linux counterpart of cdp_persistent_context.py (the macOS keepalive). The
tenant sandbox has no launchd and no X server, so this owner:
  * launches the image-owned CloakBrowser binary headless (the same binary
    and dynamic --remote-debugging-port=0 contract the macOS owner uses:
    Chromium writes the real port into DevToolsActivePort in the profile,
    which browser-guard.sh / resolve_cdp_endpoint.py then resolve), and
  * seeds the persistent context from a Playwright storage-state file
    (cookies + localStorage) the first time it sees that exact state, so a
    provisioned web session (publisher_resolution.py's materialized
    browser-auth-state.json) is consumed by the profile instead of expiring
    unused. Seeding is keyed by the state's SHA-256: a re-provisioned state
    re-seeds, an unchanged state never overwrites a live session.

The macOS disk-admission guard protects a physical host disk; inside the
tenant sandbox the platform owns the disk, so the preflight keeps only the
guard's purpose at sandbox scale: refuse to launch on a nearly-full
filesystem.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path


_MIN_FREE_BYTES = 256 * 1024**2
_SEED_MARKER = ".lm-storage-state.sha256"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _command_line(pid: int) -> str:
    try:
        result = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                                capture_output=True, text=True, check=False, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout


def _live_profile_owner(profile: str) -> int | None:
    """Return the live Chromium pid that already holds this profile, if any."""
    try:
        target = os.readlink(Path(profile) / "SingletonLock")
    except OSError:
        return None
    pid_text = target.rpartition("-")[2]
    if not pid_text.isdigit():
        return None
    pid = int(pid_text)
    if not _pid_alive(pid):
        return None
    marker = f"--user-data-dir={os.path.realpath(profile)}"
    return pid if marker in _command_line(pid) else None


def _disk_preflight(profile: str) -> bool:
    probe = Path(profile)
    while not probe.exists():
        if probe.parent == probe:
            return False
        probe = probe.parent
    try:
        return shutil.disk_usage(probe).free >= _MIN_FREE_BYTES
    except OSError:
        return False


def _state_digest(state_path: Path) -> str:
    return hashlib.sha256(state_path.read_bytes()).hexdigest()


def _seed_due(profile: str, digest: str) -> bool:
    try:
        return (Path(profile) / _SEED_MARKER).read_text(encoding="utf-8").strip() != digest
    except OSError:
        return True


def _apply_storage_state(context, state: dict) -> int:
    """Seed cookies and localStorage into a live persistent context.

    Returns the number of cookies applied. Raises on failure so the caller
    never marks a half-seeded state as consumed.
    """
    cookies = state.get("cookies") or []
    if cookies:
        context.add_cookies(cookies)
    for entry in state.get("origins") or []:
        items = entry.get("localStorage") or []
        origin = entry.get("origin") or ""
        if not items or not origin.startswith(("http://", "https://")):
            continue
        page = context.new_page()
        try:
            page.goto(origin, timeout=30_000, wait_until="commit")
            page.evaluate(
                "(items) => { for (const item of items) "
                "localStorage.setItem(item.name, item.value); }",
                items,
            )
        finally:
            page.close()
    return len(cookies)


def _seed_storage_state(context, profile: str, state_path: Path) -> int | None:
    """Seed the context from state_path unless this exact state was applied.

    Returns the applied cookie count, 0 when the state was already consumed,
    and None when no state file exists.
    """
    if not state_path.is_file():
        return None
    digest = _state_digest(state_path)
    if not _seed_due(profile, digest):
        return 0
    state = json.loads(state_path.read_text(encoding="utf-8"))
    applied = _apply_storage_state(context, state)
    (Path(profile) / _SEED_MARKER).write_text(digest + "\n", encoding="utf-8")
    return applied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--port", required=True)
    parser.add_argument("--renderer-limit", default="8")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--storage-state", default=None,
                        help="Playwright storage-state JSON to seed on first use")
    parser.add_argument("--extension", action="append", default=[],
                        help="unpacked extension dir (repeatable)")
    args = parser.parse_args(argv)
    try:
        port = int(args.port)
        renderer_limit = int(args.renderer_limit)
    except (TypeError, ValueError):
        return 1
    if not 0 <= port <= 65_535 or not 1 <= renderer_limit <= 64:
        return 1
    if not _disk_preflight(args.profile):
        return 1
    if args.preflight_only:
        return 0
    owner = _live_profile_owner(args.profile)
    if owner is not None:
        # Same adoption contract as the macOS owner: a second launch on a held
        # profile exits 0 immediately and looks like a launch failure. Adopt
        # the live browser; exit non-zero when it dies so the caller relaunches.
        print(f"adopted live profile owner pid={owner}", flush=True)
        while _pid_alive(owner):
            time.sleep(5)
        return 1
    from cloakbrowser import launch_persistent_context

    context = launch_persistent_context(
        args.profile,
        headless=True,
        humanize=True,
        extension_paths=[os.path.expanduser(path) for path in args.extension] or None,
        args=[
            f"--remote-debugging-port={port}",
            # No --remote-debugging-address: the default loopback bind is what
            # the guard resolver probes (see cdp_persistent_context.py).
            "--remote-allow-origins=*",
            "--disable-dev-shm-usage",
            f"--renderer-process-limit={renderer_limit}",
            "--disk-cache-size=67108864",
            "--media-cache-size=33554432",
        ],
    )
    if args.storage_state:
        try:
            applied = _seed_storage_state(context, args.profile, Path(args.storage_state))
            if applied:
                print(f"seeded storage state: {applied} cookies", flush=True)
        except Exception as error:  # never hand out an unseeded identity as ready
            context.close()
            print(f"storage state seeding failed: {error}", flush=True)
            return 1
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(f"persistent context alive on 127.0.0.1:{port}", flush=True)
    try:
        while not stopping:
            time.sleep(1)
    finally:
        context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
