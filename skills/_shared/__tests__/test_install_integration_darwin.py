"""PROP-C1, PROP-E1, PROP-E2, PROP-E5, PROP-E6, PROP-NFR3 — Darwin integration tests.

Spawns install-proactive-plist.sh as a subprocess against a TEST slot label
(`probe-NNN`) so we never touch a production loop. Skipped on non-Darwin.
Phase 2a RED for install-proactive-plist.
"""
from __future__ import annotations
import os
import re
import subprocess
import sys
import time
from pathlib import Path
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="install-proactive-plist is Darwin-only (launchd)",
)

SHARED_DIR = Path(__file__).resolve().parent.parent
INSTALL_SH = SHARED_DIR / "install-proactive-plist.sh"
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"


def _uid() -> int:
    return os.getuid()


def _label(slot: str) -> str:
    return f"ai.anicca.{slot}-proactive"


def _plist_path(slot: str) -> Path:
    return LAUNCH_AGENTS / f"{_label(slot)}.plist"


def _launchctl_print(label: str) -> tuple[int, str]:
    r = subprocess.run(
        ["launchctl", "print", f"gui/{_uid()}/{label}"],
        capture_output=True, text=True,
    )
    return r.returncode, r.stdout + r.stderr


def _bootout(label: str) -> None:
    subprocess.run(["launchctl", "bootout", f"gui/{_uid()}/{label}"],
                   capture_output=True, text=True)


@pytest.fixture
def probe_slot():
    """A unique probe slot per test so we never collide with production loops."""
    slot = f"probe-{int(time.time())}"
    yield slot
    # tear down
    _bootout(_label(slot))
    p = _plist_path(slot)
    if p.exists():
        p.unlink()


# ─── PROP-C1 + PROP-NFR3: install + post-install launchctl print ─────
def test_install_then_launchctl_print_succeeds(probe_slot):
    r = subprocess.run(
        ["bash", str(INSTALL_SH), probe_slot],
        capture_output=True, text=True, timeout=15,
    )
    assert r.returncode == 0, f"install failed: {r.stderr}"
    # NFR-3: stdout = exactly one summary line
    out_lines = [l for l in r.stdout.splitlines() if l.strip()]
    assert len(out_lines) == 1, f"expected 1 stdout line, got {out_lines}"
    assert f"installed {_label(probe_slot)}" in out_lines[0]
    # PROP-C1: launchctl print confirms loaded
    rc, out = _launchctl_print(_label(probe_slot))
    assert rc == 0, f"launchctl print rc={rc}: {out}"
    assert "state = " in out


# ─── PROP-B1: idempotent — 2nd install = no rewrite, same load-ts ─
def test_idempotent_install_no_churn(probe_slot):
    subprocess.run(["bash", str(INSTALL_SH), probe_slot], capture_output=True, timeout=15, check=True)
    p = _plist_path(probe_slot)
    first_mtime = p.stat().st_mtime
    time.sleep(1.1)  # mtime resolution
    r = subprocess.run(["bash", str(INSTALL_SH), probe_slot],
                       capture_output=True, text=True, timeout=15)
    assert r.returncode == 0
    assert p.stat().st_mtime == first_mtime, "2nd identical install must not rewrite plist"


# ─── PROP-E6: Darwin-only (we ARE on Darwin so this just asserts no
#              cross-platform branch leaked through — sanity test) ─
def test_darwin_branch_does_not_short_circuit(probe_slot):
    r = subprocess.run(["bash", str(INSTALL_SH), probe_slot],
                       capture_output=True, text=True, timeout=15)
    assert r.returncode == 0
    assert "Darwin only" not in r.stderr


# ─── REQ-A4: injection guard rejects bad slot WITHOUT side-effect ───
def test_injection_guard_no_side_effect():
    bad = "gig; rm -rf /"
    snapshot_before = list(LAUNCH_AGENTS.glob("ai.anicca.*-proactive.plist"))
    r = subprocess.run(["bash", str(INSTALL_SH), bad],
                       capture_output=True, text=True, timeout=10)
    assert r.returncode != 0
    assert "validation" in r.stderr.lower() or "invalid" in r.stderr.lower()
    snapshot_after = list(LAUNCH_AGENTS.glob("ai.anicca.*-proactive.plist"))
    assert set(snapshot_before) == set(snapshot_after), \
        "injection guard MUST NOT touch LaunchAgents dir"


# ─── PROP-A1: rendered plist on disk has literal /Users/... paths ──
def test_rendered_plist_contains_literal_absolute_paths(probe_slot):
    subprocess.run(["bash", str(INSTALL_SH), probe_slot], capture_output=True, timeout=15, check=True)
    body = _plist_path(probe_slot).read_text()
    assert "$HOME" not in body
    assert "${HOME}" not in body
    assert "~/" not in body
    # Must reference the canonical anicca repo
    assert "/Users/operator/anicca/skills/_shared/proactive-loop.sh" in body
    assert f"/Users/operator/.openclaw/logs/{probe_slot}-proactive.out" in body


# ─── PROP-E1: existing core-healthcheck (if any) must not get touched ─
def test_does_not_touch_core_healthcheck(probe_slot):
    # If a gig-core-healthcheck happens to be loaded, capture its load PID
    # before our install and assert identity after.
    rc, before = _launchctl_print("ai.anicca.gig-core-healthcheck")
    if rc != 0:
        pytest.skip("gig-core-healthcheck not loaded; skipping load-identity check")
    pid_before = re.search(r"pid\s*=\s*(\d+)", before)
    subprocess.run(["bash", str(INSTALL_SH), probe_slot], capture_output=True, timeout=15, check=True)
    rc2, after = _launchctl_print("ai.anicca.gig-core-healthcheck")
    assert rc2 == 0, "core-healthcheck must still be loaded"
    pid_after = re.search(r"pid\s*=\s*(\d+)", after)
    # PID may not be present if it's not currently running, but if both present they must match
    if pid_before and pid_after:
        assert pid_before.group(1) == pid_after.group(1), \
            "PID changed = core-healthcheck was bootout-then-rebootstrapped (forbidden)"
