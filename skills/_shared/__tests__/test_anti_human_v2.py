"""PROP-J8 + J8a (required:true) — anti-human-touch over sprint-2 source files.

Re-runs sprint-1's anti_human_touch_violations over every new sprint-2 source file.
ZERO hits required.
"""
from __future__ import annotations

import os
from pathlib import Path
import pytest

from lib.group_j import anti_human_touch_violations  # FROM sprint-1


_SHARED = Path(__file__).resolve().parent.parent
_LIB = _SHARED / "lib"

SPRINT_2_LIB_FILES = [
    "quota_tracker.py",
    "menu.py",
    "build_log.py",
    "health_check_v2.py",
    "bot2bot.py",
    "proactive_loop.py",
]
SPRINT_2_SHELL_FILES = [
    "proactive-loop.sh",
    "credential-restore.sh",
    "auto-allowlist.sh",
    "auto-rollback.sh",
]


# ─── PROP-J8a-new-files (required:true) ───────────────────────────
@pytest.mark.parametrize("filename", SPRINT_2_LIB_FILES)
def test_sprint_2_lib_files_have_zero_human_touch(filename):
    fpath = _LIB / filename
    if not fpath.exists():
        pytest.skip(f"{filename} not yet implemented (Phase 2b will create)")
    src = fpath.read_text()
    violations = anti_human_touch_violations(src)
    assert violations == [], f"{filename} has human-touch violations: {violations}"


@pytest.mark.parametrize("filename", SPRINT_2_SHELL_FILES)
def test_sprint_2_shell_files_have_zero_human_touch(filename):
    fpath = _SHARED / filename
    if not fpath.exists():
        pytest.skip(f"{filename} not yet implemented (Phase 2b will create)")
    src = fpath.read_text()
    violations = anti_human_touch_violations(src)
    assert violations == [], f"{filename} has human-touch violations: {violations}"


# ─── PROP-J8-blocklist (required:true) ────────────────────────────
def test_known_human_touch_patterns_still_flagged():
    """sprint-1 PROP-J8 invariant re-asserted: the blocklist still catches every
    pattern (= guards against accidental sprint-2 weakening of the static analyzer)."""
    samples = {
        "telegram-api": 'requests.post("https://api.telegram.org/bot/x")',
        "slack-webhook": 'requests.post("https://hooks.slack.com/foo")',
        "twilio": "twilio.send_message(...)",
        "osascript": 'subprocess.run(["osascript", "-e", "display dialog"])',
        "find-generic-password": 'subprocess.run(["security", "find-generic-password"])',
    }
    for label, src in samples.items():
        violations = anti_human_touch_violations(src)
        assert violations, f"sprint-2 must still flag {label}"
