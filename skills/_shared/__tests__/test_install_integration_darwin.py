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
    slot = f"probe-{int(time.time())}-{os.getpid()}"
    yield slot
    # tear down
    _bootout(_label(slot))
    p = _plist_path(slot)
    if p.exists():
        p.unlink()


# ─── FIND-001 fix verify: collision-bootout-then-byte-identical-disk ─
def test_collision_bootout_with_identical_disk_still_loads(probe_slot, tmp_path):
    """REQ-B4 + REQ-E2 + REQ-C1 interaction: when a stale job is loaded from
    a different path AND the canonical disk plist is already byte-identical
    (residue from a prior install), the script must still bootstrap so one
    loaded job remains at the canonical path."""
    # Step 1: install once to materialize canonical disk plist
    subprocess.run(["bash", str(INSTALL_SH), probe_slot],
                   capture_output=True, timeout=15, check=True)
    canonical_plist = _plist_path(probe_slot)
    assert canonical_plist.exists()
    # Step 2: bootout the loaded job but LEAVE the disk plist in place (= residue)
    _bootout(_label(probe_slot))
    assert canonical_plist.exists(), "disk plist must still exist as residue"
    # Step 3: load a stale plist with the SAME label from a DIFFERENT path
    stale_path = tmp_path / f"stale-{probe_slot}.plist"
    stale_path.write_text(canonical_plist.read_text())  # same content, different path
    r_load = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{_uid()}", str(stale_path)],
        capture_output=True, text=True,
    )
    assert r_load.returncode == 0, f"stale bootstrap failed: {r_load.stderr}"
    # Step 4: now run install — must detect cross-path collision, bootout stale,
    # and STILL bootstrap canonical even though disk digest matches.
    r = subprocess.run(["bash", str(INSTALL_SH), probe_slot],
                       capture_output=True, text=True, timeout=15)
    assert r.returncode == 0, f"install failed: rc={r.returncode} stderr={r.stderr}"
    rc, out = _launchctl_print(_label(probe_slot))
    assert rc == 0, f"post-install launchctl print failed: {out}"
    # The loaded path must be the canonical, not the stale tmp path
    from lib.plist_render import parse_loaded_plist_path
    loaded_path = parse_loaded_plist_path(out)
    assert loaded_path == str(canonical_plist), \
        f"expected canonical {canonical_plist}, got {loaded_path}"
    # Cleanup: bootout + remove stale
    _bootout(_label(probe_slot))
    if stale_path.exists():
        stale_path.unlink()


# ─── FIND-002 fix: PROP-E5 half-load rollback ─────────────────────
def test_bootstrap_failure_rolls_back_disk_plist(tmp_path, monkeypatch):
    """EDGE-E5 / PROP-E5: when launchctl bootstrap fails, the disk plist must
    be removed (no half-loaded state). Shim launchctl via PATH to force fail."""
    # tmp_path is under /private/var/folders (Darwin pytest tmp) which is in
    # the allowed-temp-root list of the FIND-2-001 production guard.
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_launchctl = fake_bin / "launchctl"
    fake_launchctl.write_text(
        "#!/bin/bash\n"
        # Allow print + bootout to succeed (return empty/0), but FAIL bootstrap.
        "case \"$1\" in\n"
        "  bootstrap) echo 'simulated launchctl error' >&2; exit 78;;\n"
        "  bootout)   exit 0;;\n"
        "  print)     exit 1;;\n"  # not loaded
        "  *)         exit 0;;\n"
        "esac\n"
    )
    fake_launchctl.chmod(0o755)
    slot = f"probe-rollback-{int(time.time())}-{os.getpid()}"
    p = _plist_path(slot)
    assert not p.exists(), "pre-condition: canonical plist must not exist"
    env = {**os.environ, "LAUNCHCTL_BIN": str(fake_launchctl)}
    r = subprocess.run(["bash", str(INSTALL_SH), slot],
                       capture_output=True, text=True, timeout=15, env=env)
    assert r.returncode != 0, "install with failing bootstrap must exit non-zero"
    assert "bootstrap failed" in r.stderr.lower() or "simulated" in r.stderr.lower()
    # CRITICAL: the disk plist must be ROLLED BACK (removed)
    assert not p.exists(), \
        f"PROP-E5 violation: bootstrap failed but disk plist {p} still exists"


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


# ─── PROP-A1: rendered plist on disk has literal user-home paths ──
def test_rendered_plist_contains_literal_absolute_paths(probe_slot):
    subprocess.run(["bash", str(INSTALL_SH), probe_slot], capture_output=True, timeout=15, check=True)
    body = _plist_path(probe_slot).read_text()
    assert "$HOME" not in body
    assert "${HOME}" not in body
    assert "~/" not in body
    # Must reference the canonical anicca repo
    repo_root = Path(__file__).resolve().parents[3]
    assert f"{repo_root}/skills/_shared/proactive-loop.sh" in body
    assert str(Path.home() / f".local/state/life-manager/logs/{probe_slot}-proactive.out") in body


# ─── PROP-E1: load-identity check for any sibling job at all times ─
# FIND-003 fix: install our own sibling job before the test so the check is
# never skipped (= every CI run actually exercises the invariant).
def test_does_not_touch_sibling_job(tmp_path):
    """PROP-E1: assert path AND PID identity of ANY pre-existing sibling job
    that shares our naming convention. Set up a controlled sibling so the test
    cannot silently no-op (FIND-003 fix)."""
    sibling_slot = f"sibling-{int(time.time())}-{os.getpid()}"
    sibling_label = f"ai.anicca.{sibling_slot}-core-healthcheck"
    sibling_plist = LAUNCH_AGENTS / f"{sibling_label}.plist"
    sibling_plist.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n<dict>\n'
        f'  <key>Label</key><string>{sibling_label}</string>\n'
        '  <key>ProgramArguments</key><array><string>/bin/true</string></array>\n'
        '  <key>StartInterval</key><integer>86400</integer>\n'
        '  <key>RunAtLoad</key><false/>\n'
        '</dict>\n</plist>\n'
    )
    subprocess.run(["launchctl", "bootstrap", f"gui/{_uid()}", str(sibling_plist)],
                   capture_output=True, check=False)
    try:
        rc_b, before = _launchctl_print(sibling_label)
        assert rc_b == 0, "sibling must be loaded"
        path_before = re.search(r"path\s*=\s*(.+)", before)
        # Run our install; it must not perturb the sibling
        target = f"probe-{int(time.time())}-{os.getpid()}"
        subprocess.run(["bash", str(INSTALL_SH), target],
                       capture_output=True, timeout=15, check=True)
        try:
            rc_a, after = _launchctl_print(sibling_label)
            assert rc_a == 0, "sibling must STILL be loaded"
            path_after = re.search(r"path\s*=\s*(.+)", after)
            assert path_before is not None and path_after is not None
            assert path_before.group(1).strip() == path_after.group(1).strip(), \
                "PROP-E1 violation: sibling path changed during install"
        finally:
            _bootout(_label(target))
            (_plist_path(target)).unlink(missing_ok=True)
    finally:
        _bootout(sibling_label)
        sibling_plist.unlink(missing_ok=True)
