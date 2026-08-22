#!/usr/bin/env python3
"""Run the isolated Affiliate EN CloakBrowser owned by launchd."""

from __future__ import annotations

import os
import pwd
import stat
import subprocess
import time
from pathlib import Path


_GUARD_RELATIVE = Path(
    "gig/releases/life-manager/current/skills/earn/gig/scripts/gig_disk_guard.py"
)
_READABLE = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
_REMOVED_ENV = (
    "GIG_IGNORE_DISK_PRESSURE_BLOCK", "GIG_IGNORE_DISK_WRITERS_STOP",
    "DISK_CONTROL_STATE_DIR", "OPENCLAW_STATE_DIR", "LIFE_MANAGER_HOST_STATE_DIR",
)


def _canonical_home() -> Path | None:
    try:
        home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    except (KeyError, OSError):
        return None
    return home if home.is_absolute() and home.is_dir() else None


def _disk_preflight(home: Path | None = None) -> bool:
    home = _canonical_home() if home is None else home
    if home is None or not home.is_absolute() or not home.is_dir():
        return False
    guard = home / _GUARD_RELATIVE
    try:
        if (
            guard.is_symlink()
            or not guard.is_file()
            or not guard.stat().st_mode & _READABLE
        ):
            return False
        child_env = os.environ.copy()
        child_env.update(
            {
                "HOME": str(home),
                "GIG_DISK_HEADROOM_KIB": "524288",
                "GIG_HOST_STATE_DIR": str(home / ".openclaw/state"),
                "GIG_STATE_DIR": str(home / ".local/state/life-manager/affiliate"),
            }
        )
        for key in _REMOVED_ENV:
            child_env.pop(key, None)
        result = subprocess.run(
            ["/usr/bin/python3", "-I", str(guard), "/usr/bin/true"],
            env=child_env,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return getattr(result, "returncode", 1) == 0


def _cdp_port() -> int | None:
    try:
        port = int(os.environ.get("AFFILIATE_CDP_PORT", "9324"))
    except (TypeError, ValueError):
        return None
    return port if 1 <= port <= 65_535 else None


def main() -> int:
    if not _disk_preflight():
        return 1
    port = _cdp_port()
    if port is None:
        return 1
    from cloakbrowser import launch_persistent_context

    profile = Path(
        os.environ.get("AFFILIATE_BROWSER_PROFILE", "~/.cloak/profiles/affiliate/en")
    ).expanduser()
    profile.mkdir(mode=0o700, parents=True, exist_ok=True)
    context = launch_persistent_context(
        str(profile), headless=False,
        args=[f"--remote-debugging-port={port}", "--remote-allow-origins=*"],
    )
    pages = context.pages
    page = pages[0] if pages else context.new_page()
    if page.url == "about:blank":
        page.goto(
            os.environ.get("AFFILIATE_START_URL", "https://elevenlabs.io/app/home"),
            wait_until="domcontentloaded",
            timeout=30_000,
        )
    while True:
        time.sleep(60)
if __name__ == "__main__":
    raise SystemExit(main())
